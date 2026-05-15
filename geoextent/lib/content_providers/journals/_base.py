"""Shared base class for journal landing-page providers.

Concrete subclasses (``OJS``, ``Janeway``, ``Pensoft``) override
:meth:`JournalProvider._is_my_platform` (and, for DOI-prefix-shortcut
publishers like Pensoft, ``validate_provider``). The rest of the pipeline —
HTML fetch, BeautifulSoup parse, JSON-LD walking, meta-tag dictionary,
priority resolution, and writing a GeoJSON (plus a CSV when only dates are
available) into the download folder — lives here.

Output contract (matches the existing remote-provider pattern in
``extent.py``): :meth:`download` writes file(s) into the supplied folder;
``extent.from_directory`` then runs over those files via ``handle_vector`` /
``handle_csv``. Internal bbox shape is ``[minlon, minlat, maxlon, maxlat]``;
the public-API swap to ``[minlat, minlon, ...]`` happens at the API
boundary, not here.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from requests import HTTPError

from .. import providers as _providers
from ... import helpfunctions as hf
from . import _meta

logger = logging.getLogger("geoextent")


# Module-level HTML cache shared across all subclass instances. ``find_provider``
# constructs a fresh instance per provider class on each request, so sniffing
# for OJS then Janeway would otherwise double the HTTP cost on unknown hosts.
# Cleared per-process at startup; bounded by URL distinct count in practice.
_HTML_CACHE: dict[str, str] = {}


_DOI_FROM_URL_RE = re.compile(r"https?://(?:dx\.)?doi\.org/(.+)$", re.I)


class JournalProvider(_providers.DoiProvider):
    """Abstract base for journal-platform metadata extractors."""

    # Subclass override hook
    name: str = "Journal"

    @property
    def supports_metadata_extraction(self) -> bool:
        return True

    def __init__(self):
        super().__init__()
        self.log = logger
        self.reference: str | None = None
        # Resolved URL of the article landing page (set by validate_provider).
        self._article_url: str | None = None
        # Parsed metadata, cached after first call to _extract.
        self._record: dict[str, Any] | None = None
        self.throttle = False

    # ------------------------------------------------------------------
    # Subclass hooks
    # ------------------------------------------------------------------

    def _is_my_platform(self, html: str, url: str) -> bool:
        """Return True if this URL+HTML matches the subclass's platform.

        Override in every subclass.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Provider interface
    # ------------------------------------------------------------------

    def validate_provider(self, reference: str) -> bool:
        """Resolve ``reference`` (DOI or URL) → fetch the landing page → call
        the subclass's :meth:`_is_my_platform` on the response.

        On any HTTP / network error returns ``False`` so the next provider can
        try; provider selection is best-effort by design.
        """
        self.reference = reference
        try:
            url = self.get_url  # DoiProvider property; resolves DOI to final URL
        except Exception:  # pragma: no cover - defensive
            return False
        if (
            not url
            or not isinstance(url, str)
            or not url.startswith(("http://", "https://"))
        ):
            return False
        try:
            html = self._fetch_html(url)
        except (HTTPError, OSError):
            return False
        except Exception:  # pragma: no cover - defensive
            return False
        if self._is_my_platform(html, url):
            self._article_url = url
            return True
        return False

    def download(
        self,
        folder,
        throttle=False,
        download_data=True,
        show_progress=True,
        max_size_bytes=None,
        max_download_method="ordered",
        max_download_method_seed=None,
        download_skip_nogeo=False,
        download_skip_nogeo_exts=None,
        max_download_workers=4,
        progress_callback=None,
    ):
        """Extract geometry + temporal info from the landing page and write
        them as a GeoJSON (when geometry is available) and/or a CSV (date-only
        fallback) into ``folder``.

        The signature matches the broader remote-provider contract enforced by
        ``extent.py``; most arguments are not meaningful for a metadata-only
        provider and are accepted for parity.
        """
        self.throttle = throttle
        if download_skip_nogeo:
            self.log.warning(
                "%s extracts geographic metadata from journal landing pages and "
                "does not download individual files. --download-skip-nogeo is "
                "ignored.",
                self.name,
            )
        if not self._article_url:
            raise ValueError(
                f"{self.name}: validate_provider must succeed before download"
            )

        record = self._extract()
        os.makedirs(folder, exist_ok=True)

        geometry = record.get("geometry")
        tbox = record.get("tbox")
        article_id = record.get("article_id") or "article"
        slug = f"{self.name.lower()}_{article_id}"

        if geometry is not None:
            geojson = self._to_feature_collection(geometry, record)
            geojson_path = os.path.join(folder, f"{slug}.geojson")
            with open(geojson_path, "w", encoding="utf-8") as fh:
                json.dump(geojson, fh, ensure_ascii=False, indent=2)
            self.log.info(
                "%s: wrote geometry to %s (source=%s)",
                self.name,
                geojson_path,
                record.get("source_spatial"),
            )
        elif tbox is not None:
            # No geometry, but we have dates — write a date-only CSV so
            # ``handle_csv`` can still surface a temporal extent.
            csv_path = os.path.join(folder, f"{slug}_dates.csv")
            start, end = tbox
            with open(csv_path, "w", encoding="utf-8") as fh:
                fh.write("date_start,date_end\n")
                fh.write(f"{start or ''},{end or ''}\n")
            self.log.info(
                "%s: wrote date-only CSV to %s (source=%s)",
                self.name,
                csv_path,
                record.get("source_temporal"),
            )
        else:
            self.log.info(
                "%s: no spatial or temporal metadata found at %s",
                self.name,
                self._article_url,
            )

    # ------------------------------------------------------------------
    # Public accessors used by extent.py for DOI enrichment
    # ------------------------------------------------------------------

    @property
    def extracted_doi(self) -> str | None:
        """DOI lifted from the landing-page head, if any. Returns ``None``
        when no download / extraction has populated ``self._record`` yet —
        callers (extent.py enrichment) should query this only *after*
        ``download()`` has run.
        """
        return self._record.get("doi") if self._record else None

    # ------------------------------------------------------------------
    # HTML fetch + parse
    # ------------------------------------------------------------------

    def _fetch_html(self, url: str) -> str:
        cached = _HTML_CACHE.get(url)
        if cached is not None:
            return cached
        resp = self._request(url, throttle=self.throttle)
        text = resp.text
        _HTML_CACHE[url] = text
        return text

    def _parse_jsonld(self, soup: BeautifulSoup) -> list[Any]:
        """Return every JSON-LD block in document order; non-JSON ones are
        skipped silently."""
        blocks: list[Any] = []
        for script in soup.find_all("script", type="application/ld+json"):
            raw = script.string
            if not raw:
                continue
            try:
                blocks.append(json.loads(raw))
            except (json.JSONDecodeError, TypeError) as exc:
                self.log.debug("%s: skipping malformed JSON-LD (%s)", self.name, exc)
                continue
        return blocks

    def _meta_tag_dict(
        self, soup: BeautifulSoup
    ) -> dict[tuple[str, str | None], list[str]]:
        """Return a case-insensitive ``{(name, scheme): [content, ...]}`` map
        of every ``<meta name=…>`` in the document, preserving order and
        duplicates.

        Scheme is stored as ``None`` when absent. Names are lower-cased.
        """
        out: dict[tuple[str, str | None], list[str]] = {}
        for tag in soup.find_all("meta"):
            name = tag.get("name")
            if not name:
                continue
            scheme = tag.get("scheme")
            content = tag.get("content")
            if content is None:
                continue
            key = (name.strip().lower(), scheme.strip() if scheme else None)
            out.setdefault(key, []).append(content)
        return out

    # ------------------------------------------------------------------
    # JSON-LD walkers
    # ------------------------------------------------------------------

    @staticmethod
    def _iter_jsonld_nodes(blocks):
        """Yield every dict node from a list of JSON-LD blocks, descending into
        ``@graph`` arrays."""
        stack = list(blocks)
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                yield node
                graph = node.get("@graph")
                if isinstance(graph, list):
                    stack.extend(graph)
            elif isinstance(node, list):
                stack.extend(node)

    def _geometry_from_jsonld(self, blocks) -> dict | None:
        """Walk JSON-LD nodes looking for spatial info.

        Recognises (in priority order within JSON-LD):

        * ``spatialCoverage`` / ``contentLocation`` containing a ``geo`` block
          (``GeoCoordinates`` for points; ``GeoShape`` for box / polygon /
          line; or a plain GeoJSON geometry dict).
        * Embedded GeoJSON geometry / Feature / FeatureCollection.
        * Bare ``latitude`` + ``longitude`` properties on a Place node.

        Returns a GeoJSON geometry dict, or ``None`` if nothing usable was
        found.
        """
        coords: list[list[float]] = []
        polygons: list[list[list[list[float]]]] = []

        for node in self._iter_jsonld_nodes(blocks):
            for key in ("spatialCoverage", "contentLocation", "location"):
                target = node.get(key)
                if target is None:
                    continue
                for place in target if isinstance(target, list) else [target]:
                    geom = self._place_to_geometry(place)
                    if geom is None:
                        continue
                    if geom["type"] == "Point":
                        coords.append(geom["coordinates"])
                    elif geom["type"] == "Polygon":
                        polygons.append(geom["coordinates"])
                    elif geom["type"] == "MultiPolygon":
                        polygons.extend(geom["coordinates"])
                    elif geom["type"] in {
                        "FeatureCollection",
                        "Feature",
                        "GeometryCollection",
                    }:
                        # Fold an arbitrary GeoJSON into its bbox-equivalent.
                        bbox = _meta.geometry_bbox(geom)
                        if bbox:
                            polygons.append(_bbox_to_polygon_ring(bbox))

        if polygons:
            if len(polygons) == 1:
                return {"type": "Polygon", "coordinates": polygons[0]}
            return {"type": "MultiPolygon", "coordinates": polygons}
        if coords:
            if len(coords) == 1:
                return {"type": "Point", "coordinates": coords[0]}
            return {"type": "MultiPoint", "coordinates": coords}
        return None

    @staticmethod
    def _place_to_geometry(place) -> dict | None:
        """Coerce a schema.org Place / GeoCoordinates / GeoShape (or plain
        GeoJSON geometry dict) into a GeoJSON geometry."""
        if not isinstance(place, dict):
            return None

        # Direct GeoJSON geometry
        if place.get("type") in {
            "Point",
            "Polygon",
            "MultiPolygon",
            "MultiPoint",
            "LineString",
            "MultiLineString",
            "Feature",
            "FeatureCollection",
            "GeometryCollection",
        }:
            # Either a real GeoJSON geometry (has "coordinates") or a wrapper
            # we can compute a bbox from.
            if "coordinates" in place or place.get("type") in {
                "Feature",
                "FeatureCollection",
                "GeometryCollection",
            }:
                return place

        geo = place.get("geo")
        if isinstance(geo, list):
            geo = geo[0] if geo else None
        if isinstance(geo, dict):
            t = (geo.get("@type") or geo.get("type") or "").strip()
            if t == "GeoCoordinates":
                try:
                    lat = float(geo["latitude"])
                    lon = float(geo["longitude"])
                    return {"type": "Point", "coordinates": [lon, lat]}
                except (KeyError, TypeError, ValueError):
                    return None
            if t == "GeoShape":
                # GeoShape.box = "lat1 lon1 lat2 lon2" per schema.org
                box = geo.get("box")
                if box:
                    parts = box.replace(",", " ").split()
                    if len(parts) == 4:
                        try:
                            lat1, lon1, lat2, lon2 = (float(p) for p in parts)
                            w, e = sorted([lon1, lon2])
                            s, n = sorted([lat1, lat2])
                            return _bbox_polygon_geometry([w, s, e, n])
                        except ValueError:
                            return None
                polygon = geo.get("polygon")
                if polygon:
                    # GeoShape.polygon = "lat1 lon1 lat2 lon2 ..."
                    parts = polygon.replace(",", " ").split()
                    if len(parts) >= 6 and len(parts) % 2 == 0:
                        try:
                            ring = []
                            for i in range(0, len(parts), 2):
                                lat = float(parts[i])
                                lon = float(parts[i + 1])
                                ring.append([lon, lat])
                            if ring[0] != ring[-1]:
                                ring.append(ring[0])
                            return {"type": "Polygon", "coordinates": [ring]}
                        except ValueError:
                            return None
            # schema.org may also nest a plain GeoJSON geometry directly
            if t in {"Point", "Polygon", "MultiPolygon", "LineString"}:
                if "coordinates" in geo:
                    return {"type": t, "coordinates": geo["coordinates"]}

        # Bare latitude/longitude on the place itself
        if "latitude" in place and "longitude" in place:
            try:
                lat = float(place["latitude"])
                lon = float(place["longitude"])
                return {"type": "Point", "coordinates": [lon, lat]}
            except (TypeError, ValueError):
                return None

        return None

    def _temporal_from_jsonld(self, blocks) -> tuple[str | None, str | None] | None:
        for node in self._iter_jsonld_nodes(blocks):
            tc = node.get("temporalCoverage")
            if not tc:
                continue
            if isinstance(tc, list):
                tc = tc[0] if tc else None
            if isinstance(tc, str):
                parsed = _meta.parse_dc_iso_interval(tc)
                if parsed:
                    return parsed
        return None

    def _doi_from_head(self, soup, jsonld_blocks, meta_tags) -> str | None:
        """Lift the article DOI out of the head, scanning in priority order:
        JSON-LD identifier blocks, ``citation_doi``, ``prism.doi`` / URL,
        ``DC.Identifier`` when it looks like a DOI.

        Returns the bare DOI (no ``https://doi.org/`` prefix), or ``None``.
        """
        for node in self._iter_jsonld_nodes(jsonld_blocks):
            ident = node.get("identifier")
            for value in _iter_identifiers(ident):
                doi = _extract_doi_string(value)
                if doi:
                    return doi
            doi_field = node.get("doi")
            doi = _extract_doi_string(doi_field) if doi_field else None
            if doi:
                return doi
            url = node.get("url") or node.get("@id")
            doi = _extract_doi_string(url) if url else None
            if doi:
                return doi

        for key in [
            ("citation_doi", None),
            ("prism.doi", None),
            ("dc.identifier.doi", None),
        ]:
            for k_lower, scheme in [key]:
                for (n, sc), values in meta_tags.items():
                    if n == k_lower and (scheme is None or sc == scheme):
                        for v in values:
                            doi = _extract_doi_string(v)
                            if doi:
                                return doi

        # prism.url / DC.Identifier may carry a doi.org URL
        for name in ("prism.url", "dc.identifier", "dc.identifier.uri"):
            for (n, _sc), values in meta_tags.items():
                if n == name:
                    for v in values:
                        doi = _extract_doi_string(v)
                        if doi:
                            return doi
        return None

    # ------------------------------------------------------------------
    # Alternate geo+json link fetch
    # ------------------------------------------------------------------

    def _fetch_alternate_geojson(
        self, base_url: str, soup: BeautifulSoup
    ) -> dict | None:
        link = soup.find(
            "link",
            attrs={"rel": "alternate", "type": re.compile(r"geo\+json", re.I)},
        )
        if not link:
            link = soup.find(
                "link",
                attrs={
                    "rel": "alternate",
                    "type": re.compile(r"application/geo", re.I),
                },
            )
        if not link:
            return None
        href = link.get("href")
        if not href:
            return None
        target = urljoin(base_url, href)
        try:
            resp = self._request(target, throttle=False)
        except (HTTPError, OSError) as exc:
            self.log.debug(
                "%s: alternate geo+json fetch failed (%s): %s",
                self.name,
                target,
                exc,
            )
            return None
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "json" not in ctype:
            self.log.debug(
                "%s: alternate link %s returned non-JSON content-type %r — skipping",
                self.name,
                target,
                ctype,
            )
            return None
        try:
            data = resp.json()
        except ValueError:
            self.log.debug(
                "%s: alternate link %s did not parse as JSON", self.name, target
            )
            return None
        if isinstance(data, dict) and data.get("type") in {
            "Feature",
            "FeatureCollection",
            "GeometryCollection",
            "Point",
            "Polygon",
            "MultiPolygon",
            "LineString",
            "MultiPoint",
            "MultiLineString",
        }:
            return data
        return None

    # ------------------------------------------------------------------
    # Priority resolvers
    # ------------------------------------------------------------------

    _SPATIAL_SOURCES = (
        "jsonld",
        "alternate-link",
        "dc.spatialcoverage:geojson",
        "dc.spatialcoverage:wkt",
        "iso19139",
        "dc.box",
        "ojs.admin-unit",
        "geo.position",
    )

    def _resolve_spatial(
        self,
        soup: BeautifulSoup,
        jsonld_blocks,
        meta_tags,
        base_url: str,
    ) -> dict | None:
        """Apply the spatial source priority list. Returns
        ``{"geometry": …, "bbox": [w,s,e,n], "source": …}`` or ``None``.
        """
        # 1. JSON-LD spatialCoverage / contentLocation
        geom = self._geometry_from_jsonld(jsonld_blocks)
        if geom is not None:
            bbox = _meta.geometry_bbox(geom)
            if bbox:
                return {"geometry": geom, "bbox": bbox, "source": "jsonld"}

        # 2. <link rel="alternate" type="application/geo+json">
        alt = self._fetch_alternate_geojson(base_url, soup)
        if alt is not None:
            bbox = _meta.geometry_bbox(alt)
            if bbox:
                geom = _flatten_to_geometry(alt)
                return {"geometry": geom, "bbox": bbox, "source": "alternate-link"}

        # 3. DC.SpatialCoverage scheme=GeoJSON
        for content in _values(meta_tags, "dc.spatialcoverage", "GeoJSON"):
            try:
                parsed = json.loads(content)
            except (ValueError, TypeError):
                continue
            bbox = _meta.geometry_bbox(parsed)
            if bbox:
                return {
                    "geometry": _flatten_to_geometry(parsed),
                    "bbox": bbox,
                    "source": "dc.spatialcoverage:geojson",
                }

        # 4. DC.SpatialCoverage scheme=WKT
        for content in _values(meta_tags, "dc.spatialcoverage", "WKT"):
            geom = _meta.parse_wkt(content)
            if geom is not None:
                bbox = _meta.geometry_bbox(geom)
                if bbox:
                    return {
                        "geometry": geom,
                        "bbox": bbox,
                        "source": "dc.spatialcoverage:wkt",
                    }

        # 5. ISO 19139 inlined snippet
        for content in _values(meta_tags, "iso 19139", None):
            bbox = _meta.parse_iso19139_bbox(content)
            if bbox:
                return {
                    "geometry": _bbox_polygon_geometry(bbox),
                    "bbox": bbox,
                    "source": "iso19139",
                }

        # 6. DC.box
        for content in _values(meta_tags, "dc.box", None):
            bbox = _meta.parse_dc_box(content)
            if bbox:
                return {
                    "geometry": _bbox_polygon_geometry(bbox),
                    "bbox": bbox,
                    "source": "dc.box",
                }

        # 7. OJS administrativeUnits[].bbox fallback (FeatureCollection wrapper
        # already failed at rule 3 but may carry an admin-unit bbox).
        for content in _values(meta_tags, "dc.spatialcoverage", "GeoJSON"):
            try:
                parsed = json.loads(content)
            except (ValueError, TypeError):
                continue
            bbox = _meta.admin_unit_bbox(parsed)
            if bbox:
                return {
                    "geometry": _bbox_polygon_geometry(bbox),
                    "bbox": bbox,
                    "source": "ojs.admin-unit",
                }

        # 8. ICBM / geo.position (last resort)
        for content in _values(meta_tags, "icbm", None):
            pt = _meta.parse_icbm(content)
            if pt:
                lon, lat = pt
                return {
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "bbox": [lon, lat, lon, lat],
                    "source": "icbm",
                }
        for content in _values(meta_tags, "geo.position", None):
            pt = _meta.parse_geo_position(content)
            if pt:
                lon, lat = pt
                return {
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "bbox": [lon, lat, lon, lat],
                    "source": "geo.position",
                }

        return None

    def _resolve_temporal(
        self,
        jsonld_blocks,
        meta_tags,
    ) -> dict | None:
        # 1. JSON-LD temporalCoverage
        tc = self._temporal_from_jsonld(jsonld_blocks)
        if tc:
            return {"tbox": list(tc), "source": "jsonld:temporalCoverage"}

        # 2/3. DC.temporal, DC.PeriodOfTime
        for name in ("dc.temporal", "dc.periodoftime"):
            for content in _values(meta_tags, name, None):
                parsed = _meta.parse_dc_iso_interval(content)
                if parsed:
                    return {"tbox": list(parsed), "source": name}

        # 4. GeoJSON properties.temporal_periods (Janeway) / OJS temporalProperties
        for content in _values(meta_tags, "dc.spatialcoverage", "GeoJSON"):
            try:
                parsed = json.loads(content)
            except (ValueError, TypeError):
                continue
            tc = _temporal_from_geojson_wrapper(parsed)
            if tc:
                return {"tbox": list(tc), "source": "geojson:temporal_periods"}

        # NOTE: publication-date sources (``DC.Date.issued``,
        # ``citation_date``, ``citation_publication_date``) are deliberately
        # NOT used as a tbox fallback. A publication date is metadata about
        # the journal article, not about the dataset's temporal coverage —
        # surfacing it as the extent would silently misrepresent what the
        # article *studied*. If no real research-period source is present,
        # ``tbox`` stays ``None``.
        return None

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def _extract(self) -> dict[str, Any]:
        """Fetch (cached), parse, and resolve. Populates ``self._record``."""
        if self._record is not None:
            return self._record
        url = self._article_url
        if not url:
            raise RuntimeError("validate_provider must succeed before extraction")
        html = self._fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")
        jsonld = self._parse_jsonld(soup)
        meta_tags = self._meta_tag_dict(soup)

        spatial = self._resolve_spatial(soup, jsonld, meta_tags, url)
        temporal = self._resolve_temporal(jsonld, meta_tags)
        doi = self._doi_from_head(soup, jsonld, meta_tags)

        article_id = self._article_id_from_url(url)
        record: dict[str, Any] = {
            "article_id": article_id,
            "url": url,
            "doi": doi,
            "geometry": spatial["geometry"] if spatial else None,
            "bbox": spatial["bbox"] if spatial else None,
            "source_spatial": spatial["source"] if spatial else None,
            "tbox": temporal["tbox"] if temporal else None,
            "source_temporal": temporal["source"] if temporal else None,
        }
        self._record = record
        return record

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _article_id_from_url(url: str) -> str:
        path = urlparse(url).path.rstrip("/")
        if not path:
            return "article"
        # Take the last numeric path segment, or the last segment overall.
        segments = [s for s in path.split("/") if s]
        for seg in reversed(segments):
            if seg.isdigit():
                return seg
        return segments[-1]

    def _to_feature_collection(self, geometry: dict, record: dict) -> dict:
        props: dict[str, Any] = {
            "provider": self.name,
            "article_url": record.get("url"),
        }
        if record.get("doi"):
            props["doi"] = record["doi"]
        if record.get("source_spatial"):
            props["source_spatial"] = record["source_spatial"]
        tbox = record.get("tbox")
        if tbox:
            start, end = tbox
            if start:
                props["date_start"] = start
            if end:
                props["date_end"] = end
            if record.get("source_temporal"):
                props["source_temporal"] = record["source_temporal"]
        feature = {"type": "Feature", "geometry": geometry, "properties": props}
        return {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
            "features": [feature],
        }


# ---------------------------------------------------------------------------
# Free helpers
# ---------------------------------------------------------------------------


def _values(meta_tags, name: str, scheme: str | None) -> list[str]:
    """Look up meta-tag content values by (case-insensitive) name and
    optional scheme.

    When ``scheme`` is a specific string (e.g. ``"GeoJSON"``, ``"WKT"``),
    only meta tags with that exact scheme attribute match — this is what
    keeps the WKT / GeoJSON branches of ``DC.SpatialCoverage`` apart.

    When ``scheme`` is ``None``, the caller doesn't care about the scheme
    attribute and any matching name is returned, regardless of whether the
    tag carried a scheme. Document order is preserved across schemes.
    OJS / Janeway emit ``DC.temporal``, ``DC.PeriodOfTime``, and
    ``DC.Date.issued`` with ``scheme="ISO8601"`` — a strict ``scheme=None``
    filter would silently skip every one of them.
    """
    name_lc = name.lower()
    out: list[str] = []
    if scheme is not None:
        out.extend(meta_tags.get((name_lc, scheme), []))
        return out
    for (n, _sc), values in meta_tags.items():
        if n == name_lc:
            out.extend(values)
    return out


def _bbox_to_polygon_ring(bbox: list[float]) -> list[list[list[float]]]:
    w, s, e, n = bbox
    return [[[w, s], [e, s], [e, n], [w, n], [w, s]]]


def _bbox_polygon_geometry(bbox: list[float]) -> dict:
    return {"type": "Polygon", "coordinates": _bbox_to_polygon_ring(bbox)}


def _flatten_to_geometry(obj) -> dict:
    """If ``obj`` is a Feature or FeatureCollection, collapse it to a single
    geometry (or GeometryCollection); otherwise pass it through. Used so the
    on-disk GeoJSON we write always has a Feature.geometry, never a
    nested FeatureCollection inside a Feature.
    """
    if not isinstance(obj, dict):
        return obj
    t = obj.get("type")
    if t == "Feature":
        return obj.get("geometry") or {}
    if t == "FeatureCollection":
        geoms = []
        for feat in obj.get("features") or []:
            if isinstance(feat, dict):
                g = feat.get("geometry")
                if g:
                    geoms.append(g)
        if len(geoms) == 1:
            return geoms[0]
        if not geoms:
            return obj
        return {"type": "GeometryCollection", "geometries": geoms}
    return obj


def _temporal_from_geojson_wrapper(parsed) -> tuple[str | None, str | None] | None:
    """Extract a tbox from Janeway's ``properties.temporal_periods`` or OJS's
    ``temporalProperties.timePeriods`` shape, if present."""
    if not isinstance(parsed, dict):
        return None
    # Janeway: Feature with properties.temporal_periods = [[start, end], ...]
    if parsed.get("type") == "Feature":
        props = parsed.get("properties") or {}
        periods = props.get("temporal_periods")
        if isinstance(periods, list) and periods:
            return _periods_envelope(periods)
    # OJS: FeatureCollection-shaped with temporalProperties.timePeriods
    tp = parsed.get("temporalProperties")
    if isinstance(tp, dict):
        periods = tp.get("timePeriods")
        if isinstance(periods, list) and periods:
            return _periods_envelope(periods)
    return None


_OJS_BRACKET_PERIOD_RE = re.compile(
    r"^\{?\s*(\d{4}(?:-\d{2}(?:-\d{2})?)?)\s*\.\.\s*(\d{4}(?:-\d{2}(?:-\d{2})?)?)\s*\}?$"
)


def _periods_envelope(periods) -> tuple[str | None, str | None] | None:
    """Compute the min-start / max-end of a list of period entries.

    Accepts three shapes:

    * ``[start, end]`` tuple or list (Janeway ``properties.temporal_periods``).
    * ``{"start": "...", "end": "..."}`` dict.
    * ``"{start..end}"`` string (OJS ``temporalProperties.timePeriods``;
      curly braces optional). The ``..`` separator is the OJS bracket
      notation for an inclusive interval.
    """
    starts: list[str] = []
    ends: list[str] = []
    for p in periods:
        if isinstance(p, (list, tuple)) and len(p) >= 2:
            s, e = p[0], p[1]
            if isinstance(s, str) and s:
                starts.append(s)
            if isinstance(e, str) and e:
                ends.append(e)
        elif isinstance(p, dict):
            s = p.get("start")
            e = p.get("end")
            if isinstance(s, str) and s:
                starts.append(s)
            if isinstance(e, str) and e:
                ends.append(e)
        elif isinstance(p, str):
            m = _OJS_BRACKET_PERIOD_RE.match(p.strip())
            if m:
                starts.append(m.group(1))
                ends.append(m.group(2))
    if not starts and not ends:
        return None
    return (min(starts) if starts else None, max(ends) if ends else None)


def _iter_identifiers(obj):
    if obj is None:
        return
    if isinstance(obj, list):
        for v in obj:
            yield from _iter_identifiers(v)
        return
    yield obj


def _extract_doi_string(value) -> str | None:
    """Pull a bare DOI out of a string-ish value (dict, plain DOI, URL,
    schema.org PropertyValue with ``name == 'DOI'``)."""
    if value is None:
        return None
    if isinstance(value, dict):
        # schema.org PropertyValue: {"@type":"PropertyValue","name":"DOI","value":"10.…"}
        name = value.get("name") or value.get("propertyID") or ""
        if isinstance(name, str) and name.strip().lower() == "doi":
            inner = value.get("value")
            return _extract_doi_string(inner)
        # Fall through if there's a "value" or "@id" that might itself be a DOI
        for k in ("value", "@id", "url"):
            if k in value:
                got = _extract_doi_string(value[k])
                if got:
                    return got
        return None
    if not isinstance(value, str):
        return None
    s = value.strip()
    # Strip "doi:" prefix
    if s.lower().startswith("doi:"):
        s = s[4:].strip()
    # Strip URL prefix
    m = _DOI_FROM_URL_RE.match(s)
    if m:
        s = m.group(1).strip()
    # Validate against the project's DOI regex
    if hf.doi_regexp.match(s):
        # idutils-style regex; pull the bare DOI out of the match
        match = hf.doi_regexp.match(s)
        return match.group(2) if match.lastindex and match.lastindex >= 2 else s
    return None
