"""Pure parsers for the journal landing-page metadata encodings.

Every function in this module is side-effect-free and HTTP-free: feed it a
string, get a structured result. The :mod:`journals` provider package
combines these into a priority-ordered resolver that picks the richest
geometry available.

Internal bbox shape is GIS-order ``[minlon, minlat, maxlon, maxlat]``; the
swap to EPSG:4326 native ``[minlat, minlon, ...]`` happens at the public API
boundary in :mod:`geoextent.lib.extent`.
"""

from __future__ import annotations

import html as _html
import json
import logging
import re
import xml.etree.ElementTree as _ET

logger = logging.getLogger("geoextent")


# ---------------------------------------------------------------------------
# WKT
# ---------------------------------------------------------------------------

_WKT_TYPE_RE = re.compile(r"^\s*(POINT|LINESTRING|POLYGON|MULTIPOLYGON)\b", re.I)


def parse_wkt(value: str) -> dict | None:
    """Parse a WKT scalar (POINT / LINESTRING / POLYGON / MULTIPOLYGON) into a
    GeoJSON geometry dict, or return ``None`` on failure.

    Coordinate order follows WKT convention: ``lon lat`` pairs.
    """
    if not value or not isinstance(value, str):
        return None
    m = _WKT_TYPE_RE.search(value)
    if not m:
        return None
    geom_type = m.group(1).upper()
    body = value[m.end() :]
    try:
        if geom_type == "POINT":
            inner = re.search(r"\(([^()]+)\)", body).group(1)
            lon, lat = (float(x) for x in inner.split()[:2])
            return {"type": "Point", "coordinates": [lon, lat]}
        if geom_type == "LINESTRING":
            inner = re.search(r"\(([^()]+)\)", body).group(1)
            coords = [
                [float(x) for x in pair.strip().split()[:2]]
                for pair in inner.split(",")
                if pair.strip()
            ]
            return {"type": "LineString", "coordinates": coords}
        if geom_type == "POLYGON":
            rings = _split_polygon_rings(body)
            if not rings:
                return None
            return {"type": "Polygon", "coordinates": rings}
        if geom_type == "MULTIPOLYGON":
            # MULTIPOLYGON(((...)),((...)))
            polys = []
            for poly_body in re.findall(r"\(\(([^()]*(?:\([^()]*\)[^()]*)*)\)\)", body):
                rings = _split_polygon_rings("((" + poly_body + "))")
                if rings:
                    polys.append(rings)
            if not polys:
                return None
            return {"type": "MultiPolygon", "coordinates": polys}
    except (ValueError, AttributeError, IndexError):
        logger.debug("Failed to parse WKT: %s", value[:120])
        return None
    return None


def _split_polygon_rings(body: str) -> list[list[list[float]]]:
    """Pull ring coordinates out of a POLYGON body ``((r1),(r2),...)``."""
    ring_matches = re.findall(r"\(([^()]+)\)", body)
    rings: list[list[list[float]]] = []
    for ring_text in ring_matches:
        pairs = [p.strip() for p in ring_text.split(",") if p.strip()]
        ring: list[list[float]] = []
        for pair in pairs:
            parts = pair.split()
            if len(parts) >= 2:
                ring.append([float(parts[0]), float(parts[1])])
        if ring:
            rings.append(ring)
    return rings


# ---------------------------------------------------------------------------
# DCMI Box (DCSV)
# ---------------------------------------------------------------------------

_DCBOX_KEYS = {
    "northlimit": "n",
    "southlimit": "s",
    "eastlimit": "e",
    "westlimit": "w",
}


def parse_dc_box(value: str) -> list[float] | None:
    """Parse a DCMI Box ``DC.box`` content value into
    ``[minlon, minlat, maxlon, maxlat]``, or ``None`` if any limit is missing.

    Accepts arbitrary key order and tolerates extra fields (``name=``,
    ``projection=``).
    """
    if not value or not isinstance(value, str):
        return None
    bag: dict[str, float] = {}
    for part in value.split(";"):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        key = k.strip().lower()
        if key in _DCBOX_KEYS:
            try:
                bag[_DCBOX_KEYS[key]] = float(v.strip())
            except ValueError:
                return None
    if {"n", "s", "e", "w"}.issubset(bag):
        return [bag["w"], bag["s"], bag["e"], bag["n"]]
    return None


# ---------------------------------------------------------------------------
# DC.temporal / DC.PeriodOfTime — ISO 8601 interval
# ---------------------------------------------------------------------------

_ISO_DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


def parse_dc_iso_interval(value: str) -> tuple[str | None, str | None] | None:
    """Parse an ISO 8601 interval like ``2020-01-01/2024-12-31`` (or open ends
    ``../2024-12-31`` / ``2020-01-01/..``) into a ``(start, end)`` tuple.

    Returns ``None`` if the value does not look like an interval at all; an
    open end is returned as ``None``. Single-date strings are interpreted as
    ``(date, date)``.
    """
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if "/" in value:
        start, end = value.split("/", 1)
        start = start.strip()
        end = end.strip()
        s = start if _ISO_DATE_RE.match(start) else None
        e = end if _ISO_DATE_RE.match(end) else None
        if s is None and e is None:
            return None
        return (s, e)
    if _ISO_DATE_RE.match(value):
        return (value, value)
    return None


# ---------------------------------------------------------------------------
# ISO 19139 EX_GeographicBoundingBox (HTML-entity-escaped XML)
# ---------------------------------------------------------------------------

# The ISO 19139 snippet is emitted inside a ``<meta>`` content attribute as
# HTML-entity-escaped XML *without* a namespace declaration on the root —
# e.g. ``<gmd:EX_GeographicBoundingBox><gmd:westBoundLongitude>…``. Different
# publishers may use different prefixes (``gmd:``, ``ns0:``, …) bound to the
# same namespace URI, so we strip prefixes before parsing and look up by
# local element name only. This matches the spec semantics: ISO 19139
# elements are identified by their namespace + local name, never by the
# literal prefix.
_XML_TAG_PREFIX_RE = re.compile(r"(<\/?)[A-Za-z_][\w.-]*:")
_ISO19139_LIMIT_LOCALNAMES = {
    "west": "westBoundLongitude",
    "east": "eastBoundLongitude",
    "south": "southBoundLatitude",
    "north": "northBoundLatitude",
}


def parse_iso19139_bbox(value: str) -> list[float] | None:
    """Pull the four limits out of an inlined, HTML-escaped ISO 19139
    ``EX_GeographicBoundingBox`` snippet.

    Uses a real XML parser (:mod:`xml.etree.ElementTree`) and matches by
    *local* element name, so the result is independent of which prefix
    (``gmd:`` / ``ns0:`` / …) the publisher chose. Returns
    ``[minlon, minlat, maxlon, maxlat]`` or ``None`` when the snippet is
    missing any limit / fails to parse.
    """
    if not value or not isinstance(value, str):
        return None
    text = _html.unescape(value)
    # Strip namespace prefixes from element tags so the snippet parses
    # without a containing namespace declaration. Attributes are left alone:
    # the EX_GeographicBoundingBox shape doesn't use prefixed attributes.
    stripped = _XML_TAG_PREFIX_RE.sub(r"\1", text)
    try:
        # Wrap in a synthetic root so a snippet containing a single
        # ``EX_GeographicBoundingBox`` (or anything wider) parses cleanly.
        root = _ET.fromstring(
            f"<__iso19139_wrapper__>{stripped}</__iso19139_wrapper__>"
        )
    except _ET.ParseError:
        logger.debug("ISO 19139 snippet failed to parse as XML")
        return None

    limits: dict[str, float] = {}
    for key, localname in _ISO19139_LIMIT_LOCALNAMES.items():
        # Each limit element wraps a ``Decimal`` (or in some profiles a bare
        # text node); accept either by reading the deepest non-empty text.
        elem = root.find(f".//{localname}")
        if elem is None:
            return None
        text_value = _deep_text(elem)
        if text_value is None:
            return None
        try:
            limits[key] = float(text_value)
        except ValueError:
            return None
    return [limits["west"], limits["south"], limits["east"], limits["north"]]


def _deep_text(elem) -> str | None:
    """Return the first non-empty text content found in ``elem`` or any
    descendant. ISO 19139 wraps decimals in ``gco:Decimal`` but other
    profiles may put the value directly inside the limit element.
    """
    if elem.text and elem.text.strip():
        return elem.text.strip()
    for child in elem.iter():
        if child is elem:
            continue
        if child.text and child.text.strip():
            return child.text.strip()
    return None


# ---------------------------------------------------------------------------
# ICBM / geo.position — simple lat/lon points
# ---------------------------------------------------------------------------


def parse_icbm(value: str) -> tuple[float, float] | None:
    """Parse an ICBM ``"lat, lon"`` value into ``(lon, lat)``.

    Returns ``None`` on parse failure.
    """
    if not value or not isinstance(value, str):
        return None
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 2:
        return None
    try:
        lat = float(parts[0])
        lon = float(parts[1])
    except ValueError:
        return None
    return (lon, lat)


def parse_geo_position(value: str) -> tuple[float, float] | None:
    """Parse a ``geo.position`` ``"lat;lon"`` value into ``(lon, lat)``.

    Returns ``None`` on parse failure.
    """
    if not value or not isinstance(value, str):
        return None
    parts = [p.strip() for p in value.split(";")]
    if len(parts) != 2:
        return None
    try:
        lat = float(parts[0])
        lon = float(parts[1])
    except ValueError:
        return None
    return (lon, lat)


# ---------------------------------------------------------------------------
# GeoJSON bbox helpers
# ---------------------------------------------------------------------------

_NOT_AVAILABLE = {"not available", "n/a", "none", "null", ""}


def geometry_bbox(obj) -> list[float] | None:
    """Compute the containing bbox of any GeoJSON-like input.

    Accepts a geometry dict, a Feature, a FeatureCollection, or an OJS-style
    wrapper that adds ``administrativeUnits`` / ``temporalProperties`` to a
    FeatureCollection (those extras are ignored). Returns
    ``[minlon, minlat, maxlon, maxlat]``, or ``None`` if no usable coordinates
    are found.
    """
    if obj is None:
        return None
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
        except (ValueError, TypeError):
            return None
    if not isinstance(obj, dict):
        return None

    coords: list[tuple[float, float]] = []
    _collect_coords(obj, coords)
    if not coords:
        return None
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return [min(xs), min(ys), max(xs), max(ys)]


def _collect_coords(obj, out: list[tuple[float, float]]) -> None:
    """Walk any GeoJSON-shaped object, appending ``(lon, lat)`` pairs."""
    if not isinstance(obj, dict):
        return
    obj_type = obj.get("type")

    if obj_type == "FeatureCollection":
        for feat in obj.get("features") or []:
            _collect_coords(feat, out)
        return
    if obj_type == "Feature":
        _collect_coords(obj.get("geometry"), out)
        return
    if obj_type == "GeometryCollection":
        for g in obj.get("geometries") or []:
            _collect_coords(g, out)
        return

    if obj_type in {
        "Point",
        "LineString",
        "Polygon",
        "MultiPoint",
        "MultiLineString",
        "MultiPolygon",
    }:
        _walk_coordinates(obj.get("coordinates"), out)
        return


def _walk_coordinates(coords, out: list[tuple[float, float]]) -> None:
    """Append every ``(lon, lat)`` leaf from a (possibly nested) coordinates
    array."""
    if coords is None:
        return
    if isinstance(coords, (list, tuple)):
        if len(coords) >= 2 and all(isinstance(v, (int, float)) for v in coords[:2]):
            try:
                out.append((float(coords[0]), float(coords[1])))
            except (TypeError, ValueError):
                pass
            return
        for inner in coords:
            _walk_coordinates(inner, out)


def admin_unit_bbox(ojs_geojson) -> list[float] | None:
    """Extract a bbox from the OJS ``administrativeUnits[].bbox`` field, if any
    unit has a real bbox (skips the ``"not available"`` sentinel).

    Accepts either the parsed dict or a JSON string. The OJS plugin attaches
    ``administrativeUnits`` next to ``features`` in its ``DC.SpatialCoverage``
    wrapper.
    """
    if isinstance(ojs_geojson, str):
        try:
            ojs_geojson = json.loads(ojs_geojson)
        except (ValueError, TypeError):
            return None
    if not isinstance(ojs_geojson, dict):
        return None
    units = ojs_geojson.get("administrativeUnits") or []
    for unit in units:
        bbox = unit.get("bbox") if isinstance(unit, dict) else None
        if isinstance(bbox, list) and len(bbox) == 4:
            try:
                return [float(v) for v in bbox]
            except (TypeError, ValueError):
                continue
        if isinstance(bbox, str) and bbox.strip().lower() not in _NOT_AVAILABLE:
            # Sometimes bbox is a string like "w,s,e,n"
            parts = [p.strip() for p in bbox.split(",")]
            if len(parts) == 4:
                try:
                    return [float(v) for v in parts]
                except ValueError:
                    continue
    return None
