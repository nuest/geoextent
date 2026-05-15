"""Text handler that uses NER + a gazetteer to extract spatial extent.

Detects place-name and date entities in plain-text files (or in-memory
strings), forward-geocodes places via the configured gazetteer, and returns
an envelope of the resolved point set together with provenance.

The handler is opt-in: it only claims a file when the dispatch is given
``text_method`` configuration. Without that opt-in flag, ``.txt``/``.md``
files fall through unsupported, preserving current behavior.
"""

import importlib.util
import logging
import os
import unicodedata
from datetime import datetime
from typing import Optional

from . import gazetteer as gaz
from . import helpfunctions as hf
from . import period_gazetteer as period_gaz
from .text_extraction import get_extractor
from .text_extraction.dates import parse_date_entity
from .text_extraction.mime import is_text_file

logger = logging.getLogger("geoextent")


def get_handler_name():
    return "handle_text"


def get_handler_display_name():
    return "Text (NER)"


def _is_active(text_method):
    return bool(text_method)


# Cache the spaCy availability probe; importlib.util.find_spec is cheap but
# we want a single import attempt per process.
_SPACY_AVAILABLE = None


def _spacy_available() -> bool:
    """Return True when spaCy is importable in this process.

    Used as a safety gate on :func:`check_file_supported` so that the
    default ``--text-method ner`` does not hijack text files in user
    directories when the optional ``[nlp]`` extra is not installed.
    """
    global _SPACY_AVAILABLE
    if _SPACY_AVAILABLE is None:
        _SPACY_AVAILABLE = importlib.util.find_spec("spacy") is not None
    return _SPACY_AVAILABLE


def check_file_supported(filepath, *, text_method=None, **_kwargs):
    """Return True iff text extraction is enabled and the file looks like text.

    With ``--text-method ner`` (the default), this handler claims any
    ``text/*`` file. When the ``[nlp]`` extra is not installed, the handler
    silently declines so that pre-existing workflows that happen to include
    ``README.md`` or similar plain-text files continue to work.
    """
    if not _is_active(text_method):
        return False
    if not os.path.isfile(filepath):
        return False
    if not is_text_file(filepath):
        return False
    if not _spacy_available():
        logger.debug(
            "Skipping %s: --text-method=%r but spaCy is not installed "
            "(install with: pip install 'geoextent[nlp]')",
            filepath,
            text_method,
        )
        return False
    return True


def _read_text(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _extract_places(
    text: str,
    *,
    text_method: str,
    ner_model: Optional[str],
    ner_labels,
    ner_score_threshold,
    ner_auto_download: bool,
    period_gazetteer=None,
    period_resolution: bool = True,
):
    config = {}
    if ner_model:
        config["model"] = ner_model
    if ner_labels:
        config["place_labels"] = ner_labels
    if ner_score_threshold is not None:
        config["score_threshold"] = ner_score_threshold
    config["auto_download"] = ner_auto_download
    config["period_gazetteer"] = period_gazetteer
    config["period_resolution"] = period_resolution
    extractor = get_extractor(text_method, **config)
    return extractor, extractor.extract(text)


def _resolve_places(mentions, ner_gazetteer, ner_ambiguity, gaz_cache):
    names = [m.name for m in mentions]
    resolved = gaz.forward_geocode_names(
        names,
        service_name=ner_gazetteer or "nominatim",
        ambiguity=ner_ambiguity or "drop",
        cache=gaz_cache,
    )
    # Pair with mentions in order
    out = []
    for mention, (_, hit, all_hits) in zip(mentions, resolved):
        out.append((mention, hit, all_hits))
    return out


def _bbox_from_points(points):
    """Return [minlon, minlat, maxlon, maxlat] from a list of (lon, lat)."""
    if not points:
        return None
    lons = [p[0] for p in points]
    lats = [p[1] for p in points]
    return [min(lons), min(lats), max(lons), max(lats)]


def _geojson_coord_iter(geom):
    """Yield (lon, lat) tuples from a GeoJSON Point/LineString/Polygon/Multi.

    Tolerant of nested coordinate arrays; ignores Z values.
    """
    if not isinstance(geom, dict):
        return
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if coords is None:
        return
    if gtype == "Point":
        yield (coords[0], coords[1])
    elif gtype in ("LineString", "MultiPoint"):
        for pt in coords:
            yield (pt[0], pt[1])
    elif gtype in ("Polygon", "MultiLineString"):
        for ring in coords:
            for pt in ring:
                yield (pt[0], pt[1])
    elif gtype == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                for pt in ring:
                    yield (pt[0], pt[1])


def _hit_points_for_envelope(hits, *, place_geometry: str = "auto"):
    """Return the list of (lon, lat) corner points that define the bbox.

    With ``place_geometry="boundary"`` or the default ``"auto"`` a polygon
    boundary on a hit contributes its four envelope corners; without one
    the hit's centroid point is used. ``"point"`` always uses lat/lon.
    """
    points = []
    for hit in hits:
        if hit is None:
            continue
        boundary = hit.get("boundary") if place_geometry != "point" else None
        if boundary is not None:
            coords = list(_geojson_coord_iter(boundary))
            if coords:
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                points.append((min(lons), min(lats)))
                points.append((max(lons), max(lats)))
                continue
        points.append((float(hit["lon"]), float(hit["lat"])))
    return points


def _convex_hull_from_coords(coords):
    """Return a convex-hull coordinate list from a flat list of (lon, lat).

    Used by both the points-only and the mixed-geometry hull paths. Single
    point returns the point itself; two collinear points return the line
    segment; ≥3 non-collinear points return the closed polygon ring of the
    hull (first vertex repeated at the end).
    """
    if not coords:
        return None
    if len(coords) == 1:
        return [list(coords[0])]
    try:
        from osgeo import ogr

        multi = ogr.Geometry(ogr.wkbMultiPoint)
        for lon, lat in coords:
            pt = ogr.Geometry(ogr.wkbPoint)
            pt.AddPoint_2D(float(lon), float(lat))
            multi.AddGeometry(pt)
        hull = multi.ConvexHull()
        if hull is None:
            return None
        out = []
        gtype = hull.GetGeometryType()
        if gtype == ogr.wkbPolygon:
            ring = hull.GetGeometryRef(0)
            for i in range(ring.GetPointCount()):
                x, y, *_ = ring.GetPoint(i)
                out.append([x, y])
        else:  # line / point
            for i in range(hull.GetPointCount()):
                x, y, *_ = hull.GetPoint(i)
                out.append([x, y])
        return out
    except Exception as e:
        logger.debug("convex hull computation failed: %s", e)
        bbox = _bbox_from_points(coords)
        if bbox is None:
            return None
        return [
            [bbox[0], bbox[1]],
            [bbox[0], bbox[3]],
            [bbox[2], bbox[3]],
            [bbox[2], bbox[1]],
            [bbox[0], bbox[1]],
        ]


def _convex_hull_from_points(points):
    """Backward-compatible alias used by the points-only path."""
    return _convex_hull_from_coords(points)


def _convex_hull_from_hits(hits, *, place_geometry: str = "auto"):
    """Convex hull over a heterogeneous set of gazetteer hits.

    For each hit, contributes either the polygon vertices (when the hit
    carries a ``boundary`` geometry and ``place_geometry`` is not
    ``"point"``) or its centroid lat/lon. This makes the hull useful for
    mixed extents like a city polygon plus a couple of remote field
    stations, and for the single-polygon case it acts as a polygon
    simplification: the result is the convex hull of the polygon vertices.
    """
    coords = []
    for hit in hits:
        if hit is None:
            continue
        boundary = hit.get("boundary") if place_geometry != "point" else None
        if boundary is not None:
            for c in _geojson_coord_iter(boundary):
                coords.append((float(c[0]), float(c[1])))
        else:
            coords.append((float(hit["lon"]), float(hit["lat"])))
    return _convex_hull_from_coords(coords)


def _build_place_provenance(resolved, gazetteer_name, *, place_geometry: str = "auto"):
    out = []
    for mention, hit, all_hits in resolved:
        record = {
            "name": mention.name,
            "label": mention.label,
            "char_start": mention.char_start,
            "char_end": mention.char_end,
            "score": mention.score,
            "gazetteer": gazetteer_name,
            "matched": hit is not None,
            "candidate_count": len(all_hits),
        }
        if hit is not None:
            record["lat"] = hit["lat"]
            record["lon"] = hit["lon"]
            record["match_name"] = hit["name"]
            record["gazetteer_id"] = hit["id"]
            record["gazetteer_url"] = hit.get("url")
            # Areal hits (administrative boundaries, parks, etc.) carry a
            # GeoJSON Polygon/MultiPolygon. Point-only gazetteers leave
            # this as None so consumers can tell the difference.
            # ``--place-geometry point`` is an explicit request for point
            # treatment — drop the boundary so the response doesn't carry
            # a redundant polygon next to the centroid.
            if hit.get("boundary") is not None and place_geometry != "point":
                record["boundary"] = hit["boundary"]
        out.append(record)
    return out


def extract_from_text(
    text: str,
    *,
    text_method: str = "ner",
    ner_model: Optional[str] = None,
    ner_labels=None,
    ner_score_threshold: Optional[float] = None,
    ner_gazetteer: str = "nominatim",
    ner_ambiguity: str = "drop",
    ner_auto_download: bool = True,
    gazetteer_cache=None,
    period_gazetteer: str = "bundled",
    period_ambiguity: str = "drop",
    period_resolution: bool = True,
    period_cache=None,
    include_source_text: bool = True,
    place_geometry: str = "auto",
):
    """Run NER + place/period gazetteer resolution on a string.

    Result keys:
      ``bbox``: ``[minlon, minlat, maxlon, maxlat]`` in WGS84 (or absent).
      ``crs``: ``"4326"``.
      ``place_names``: place provenance list (see _build_place_provenance).
      ``date_entities``: temporal provenance list, one record per DATE/TIME
        or named period mention, each carrying signed ISO ``start``/``end``.
      ``tbox``: ``[min_start, max_end]`` signed ISO envelope when at least
        one temporal mention resolved.
      ``extraction_method``, ``ner_model``, ``ner_gazetteer``,
      ``period_gazetteer``: config echo.
    """
    # Normalise to NFC so character offsets are stable regardless of how the
    # caller composed accented characters (München can arrive as either U+00FC
    # or U+0075 U+0308). All downstream char_start/char_end values index into
    # this normalised string. Stripping a leading BOM is already done at
    # file-read time (_read_text), but we repeat it here for inline strings.
    text = unicodedata.normalize("NFC", text or "")
    if text.startswith("﻿"):
        text = text[1:]

    period_gaz_obj = (
        period_gaz.get_period_gazetteer(period_gazetteer) if period_resolution else None
    )

    extractor, extraction = _extract_places(
        text,
        text_method=text_method,
        ner_model=ner_model,
        ner_labels=ner_labels,
        ner_score_threshold=ner_score_threshold,
        ner_auto_download=ner_auto_download,
        period_gazetteer=period_gaz_obj,
        period_resolution=period_resolution,
    )
    if gazetteer_cache is None:
        gazetteer_cache = {}
    resolved = _resolve_places(
        extraction.places, ner_gazetteer, ner_ambiguity, gazetteer_cache
    )

    hits = [hit for _, hit, _ in resolved if hit is not None]
    points = _hit_points_for_envelope(hits, place_geometry=place_geometry or "auto")
    bbox = _bbox_from_points(points)

    date_records, tbox_envelope = _resolve_temporal_mentions(
        extraction,
        period_gazetteer=period_gaz_obj,
        period_ambiguity=period_ambiguity,
        period_cache=period_cache,
    )

    result = {
        "crs": str(hf.WGS84_EPSG_ID),
        "place_names": _build_place_provenance(
            resolved, ner_gazetteer, place_geometry=place_geometry or "auto"
        ),
        "date_entities": date_records,
        "extraction_method": text_method,
        "ner_model": extractor.model_name,
        "ner_gazetteer": ner_gazetteer,
        "period_gazetteer": period_gaz_obj.name if period_gaz_obj else None,
    }
    if include_source_text:
        # Standoff annotation contract — see geoextent/lib/annotate.py and
        # docs/source/howto/highlighting.rst. char_start/char_end on every
        # mention index into source_text using the unit documented here.
        result["source_text"] = text
        result["source_offset_unit"] = "python_codepoint"
        result["source_normalisation"] = "nfc"
    if bbox is not None:
        result["bbox"] = bbox
    if tbox_envelope is not None:
        result["tbox"] = tbox_envelope
    return result


def get_bounding_box(
    filepath,
    *,
    text_method=None,
    ner_model=None,
    ner_labels=None,
    ner_score_threshold=None,
    ner_gazetteer=None,
    ner_ambiguity=None,
    ner_auto_download=True,
    gazetteer_cache=None,
    period_gazetteer=None,
    period_ambiguity=None,
    period_resolution: bool = True,
    period_cache=None,
    include_source_text: bool = True,
    place_geometry: str = "auto",
    **_kwargs,
):
    if not _is_active(text_method):
        return None
    text = _read_text(filepath)
    res = extract_from_text(
        text,
        text_method=text_method,
        ner_model=ner_model,
        ner_labels=ner_labels,
        ner_score_threshold=ner_score_threshold,
        ner_gazetteer=ner_gazetteer or "nominatim",
        ner_ambiguity=ner_ambiguity or "drop",
        ner_auto_download=ner_auto_download,
        gazetteer_cache=gazetteer_cache,
        period_gazetteer=period_gazetteer or "bundled",
        period_ambiguity=period_ambiguity or "drop",
        period_resolution=period_resolution,
        period_cache=period_cache,
        include_source_text=include_source_text,
        place_geometry=place_geometry or "auto",
    )
    if "bbox" not in res:
        return None
    out = {"bbox": res["bbox"], "crs": res["crs"]}
    # Forward provenance via a private side-channel attribute on the dict.
    out["place_names"] = res["place_names"]
    out["date_entities"] = res.get("date_entities", [])
    out["ner_model"] = res["ner_model"]
    out["ner_gazetteer"] = res["ner_gazetteer"]
    out["extraction_method"] = res["extraction_method"]
    for key in ("source_text", "source_offset_unit", "source_normalisation"):
        if key in res:
            out[key] = res[key]
    return out


def get_convex_hull(
    filepath,
    *,
    text_method=None,
    ner_model=None,
    ner_labels=None,
    ner_score_threshold=None,
    ner_gazetteer=None,
    ner_ambiguity=None,
    ner_auto_download=True,
    gazetteer_cache=None,
    period_gazetteer=None,
    period_ambiguity=None,
    period_resolution: bool = True,
    period_cache=None,
    include_source_text: bool = True,
    place_geometry: str = "auto",
    **_kwargs,
):
    if not _is_active(text_method):
        return None
    text = _read_text(filepath)
    res = extract_from_text(
        text,
        text_method=text_method,
        ner_model=ner_model,
        ner_labels=ner_labels,
        ner_score_threshold=ner_score_threshold,
        ner_gazetteer=ner_gazetteer or "nominatim",
        ner_ambiguity=ner_ambiguity or "drop",
        ner_auto_download=ner_auto_download,
        gazetteer_cache=gazetteer_cache,
        period_gazetteer=period_gazetteer or "bundled",
        period_ambiguity=period_ambiguity or "drop",
        period_resolution=period_resolution,
        period_cache=period_cache,
        include_source_text=include_source_text,
        place_geometry=place_geometry or "auto",
    )
    if "bbox" not in res:
        return None
    matched_hits = []
    for rec in res["place_names"]:
        if not rec.get("matched"):
            continue
        hit = {"lat": rec["lat"], "lon": rec["lon"]}
        if rec.get("boundary") is not None:
            hit["boundary"] = rec["boundary"]
        matched_hits.append(hit)
    hull = _convex_hull_from_hits(matched_hits, place_geometry=place_geometry or "auto")
    out = {"bbox": res["bbox"], "crs": res["crs"]}
    if hull is not None:
        out["convex_hull_coords"] = hull
    # Drop boundary polygons from provenance once consumed by the hull —
    # see geoextent/lib/extent.py:from_text for the rationale (geojson.io
    # URL-fragment limit, admin polygons can be hundreds of KB).
    place_names = res["place_names"]
    if hull is not None:
        for rec in place_names:
            rec.pop("boundary", None)
    out["place_names"] = place_names
    out["date_entities"] = res.get("date_entities", [])
    out["ner_model"] = res["ner_model"]
    out["ner_gazetteer"] = res["ner_gazetteer"]
    out["extraction_method"] = res["extraction_method"]
    for key in ("source_text", "source_offset_unit", "source_normalisation"):
        if key in res:
            out[key] = res[key]
    return out


def _resolve_temporal_mentions(
    extraction,
    *,
    period_gazetteer,
    period_ambiguity: str,
    period_cache=None,
):
    """Resolve DATE and PERIOD mentions to ``(start, end)`` envelopes.

    Returns ``(records, envelope)`` where ``records`` is the per-mention
    provenance list emitted under ``date_entities`` and ``envelope`` is
    ``[min_start, max_end]`` as a list of signed ISO date strings (or
    ``None`` if no mention resolved).
    """
    records = []
    starts = []
    ends = []

    # Calendar date / time mentions from spaCy DATE/TIME entities.
    for d in extraction.dates:
        text = (d.get("text") if isinstance(d, dict) else d.text).strip()
        if not text:
            continue
        parsed = parse_date_entity(text)
        rec = {
            "text": text,
            "kind": "date",
            "label": d.label if hasattr(d, "label") else "DATE",
            "char_start": getattr(d, "char_start", None),
            "char_end": getattr(d, "char_end", None),
            "gazetteer": "dateutil",
            "matched": parsed is not None,
            "candidate_count": 1 if parsed else 0,
        }
        if parsed is not None:
            rec["start"], rec["end"] = parsed
            starts.append(rec["start"])
            ends.append(rec["end"])
        records.append(rec)

    # Named time-period mentions resolved via the period gazetteer.
    names = [m.text for m in extraction.periods]
    resolved = period_gaz.forward_geocode_periods(
        names,
        gazetteer=period_gazetteer,
        ambiguity=period_ambiguity,
        cache=period_cache,
    )
    for mention, (_, hit, all_hits) in zip(extraction.periods, resolved):
        rec = {
            "text": mention.text,
            "kind": "period",
            "char_start": mention.char_start,
            "char_end": mention.char_end,
            "gazetteer": period_gazetteer.name if period_gazetteer else None,
            "matched": hit is not None,
            "candidate_count": len(all_hits),
        }
        if hit is not None:
            rec["start"] = hit["start"]
            rec["end"] = hit["end"]
            rec["match_name"] = hit["name"]
            rec["gazetteer_id"] = hit["id"]
            rec["gazetteer_url"] = hit.get("url")
            starts.append(rec["start"])
            ends.append(rec["end"])
        records.append(rec)

    envelope = None
    if starts and ends:
        envelope = [hf.signed_iso_min(starts), hf.signed_iso_max(ends)]
    return records, envelope


def get_temporal_extent(
    filepath,
    time_format=None,
    *,
    text_method=None,
    ner_model=None,
    ner_labels=None,
    ner_auto_download=True,
    ner_gazetteer=None,
    ner_ambiguity=None,
    gazetteer_cache=None,
    period_gazetteer=None,
    period_ambiguity=None,
    period_resolution: bool = True,
    period_cache=None,
    **_kwargs,
):
    if not _is_active(text_method):
        return None
    text = _read_text(filepath)
    gazetteer = (
        period_gaz.get_period_gazetteer(period_gazetteer or "bundled")
        if period_resolution
        else None
    )
    _extractor, extraction = _extract_places(
        text,
        text_method=text_method,
        ner_model=ner_model,
        ner_labels=ner_labels,
        ner_score_threshold=None,
        ner_auto_download=ner_auto_download,
        period_gazetteer=gazetteer,
        period_resolution=period_resolution,
    )
    _records, envelope = _resolve_temporal_mentions(
        extraction,
        period_gazetteer=gazetteer,
        period_ambiguity=period_ambiguity or "drop",
        period_cache=period_cache,
    )
    return envelope
