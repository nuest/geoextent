"""
DEIMS-SDR content provider for geoextent.

DEIMS-SDR (Dynamic Ecological Information Management System - Site and Dataset Registry)
is a metadata registry for long-term ecological research sites and datasets, powered by
eLTER. It does not host data files; datasets reference external repositories (Zenodo,
PANGAEA, B2SHARE, SEANOE, EIDC, etc.).

Supported identifiers:
- Dataset URLs: https://deims.org/dataset/{uuid}
- Site URLs: https://deims.org/{uuid}
- API URLs: https://deims.org/api/datasets/{uuid}, https://deims.org/api/sites/{uuid}

Geospatial metadata is extracted from the DEIMS-SDR REST API:
- Boundaries as WKT (POINT, POLYGON, MULTIPOLYGON)
- Temporal ranges as ISO 8601 date strings
"""

import json
import logging
import os
import re
import shutil

import requests
from osgeo import ogr

from geoextent.lib import helpfunctions as hf
from geoextent.lib.content_providers.providers import ContentProvider

logger = logging.getLogger("geoextent")

_DEIMS_API_BASE = "https://deims.org/api"

# UUID pattern (RFC 4122)
_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)

# URL patterns for DEIMS-SDR
_DATASET_URL_RE = re.compile(
    r"https?://deims\.org/(?:api/)?dataset[s]?/(" + _UUID_RE.pattern + r")",
    re.IGNORECASE,
)
_SITE_URL_RE = re.compile(
    r"https?://deims\.org/(?:api/)?site[s]?/(" + _UUID_RE.pattern + r")",
    re.IGNORECASE,
)
# Bare site URL: https://deims.org/{uuid} (no /dataset/ or /site/ prefix)
_BARE_SITE_URL_RE = re.compile(
    r"https?://deims\.org/(" + _UUID_RE.pattern + r")$",
    re.IGNORECASE,
)


class DEIMSSDR(ContentProvider):
    """Content provider for DEIMS-SDR (Dynamic Ecological Information Management System)."""

    @classmethod
    def provider_info(cls):
        return {
            "name": "DEIMS-SDR",
            "description": "DEIMS-SDR (Dynamic Ecological Information Management System - Site and Dataset Registry) is a metadata registry for long-term ecological research sites and datasets, powered by eLTER. It catalogues environmental research and monitoring facilities globally, with rich geospatial metadata (WKT boundaries, temporal ranges).",
            "website": "https://deims.org/",
            "supported_identifiers": [
                "https://deims.org/dataset/{uuid}",
                "https://deims.org/{uuid}",
                "https://deims.org/api/datasets/{uuid}",
                "https://deims.org/api/sites/{uuid}",
            ],
            "examples": [
                "https://deims.org/dataset/3d87da8b-2b07-41c7-bf05-417832de4fa2",
                "https://deims.org/8eda49e9-1f4e-4f3e-b58e-e0bb25dc32a6",
            ],
            "notes": "Metadata-only provider. DEIMS-SDR does not host data files; it provides geospatial boundaries and temporal ranges via its REST API.",
        }

    @property
    def supports_metadata_extraction(self):
        return True

    def __init__(self):
        super().__init__()
        self.name = "DEIMS-SDR"
        self.reference = None
        self.resource_type = None  # "dataset" or "site"
        self.resource_uuid = None
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "nuest/geoextent"}
        )

    def validate_provider(self, reference):
        """Check if the reference is a DEIMS-SDR URL.

        Args:
            reference (str): Identifier to validate

        Returns:
            bool: True if this is a DEIMS-SDR identifier
        """
        self.reference = reference

        # Dataset URL: https://deims.org/dataset/{uuid} or API variant
        m = _DATASET_URL_RE.search(reference)
        if m:
            self.resource_type = "dataset"
            self.resource_uuid = m.group(1)
            return True

        # Site URL: https://deims.org/sites/{uuid} or API variant
        m = _SITE_URL_RE.search(reference)
        if m:
            self.resource_type = "site"
            self.resource_uuid = m.group(1)
            return True

        # Bare site URL: https://deims.org/{uuid}
        m = _BARE_SITE_URL_RE.search(reference)
        if m:
            self.resource_type = "site"
            self.resource_uuid = m.group(1)
            return True

        return False

    def _fetch_metadata(self):
        """Fetch metadata from DEIMS-SDR API.

        Returns:
            dict: Parsed JSON response from the API
        """
        if self.resource_type == "dataset":
            url = f"{_DEIMS_API_BASE}/datasets/{self.resource_uuid}"
        else:
            url = f"{_DEIMS_API_BASE}/sites/{self.resource_uuid}"

        logger.debug(f"Fetching DEIMS-SDR metadata from: {url}")
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.json()

    def _extract_geometry_from_wkt(self, wkt_string):
        """Parse a WKT string and return OGR geometry.

        Args:
            wkt_string (str): WKT geometry string

        Returns:
            ogr.Geometry or None: Parsed geometry, or None on failure
        """
        if not wkt_string:
            return None
        geom = ogr.CreateGeometryFromWkt(wkt_string)
        if geom is None:
            logger.warning(f"Failed to parse WKT: {wkt_string[:100]}...")
        return geom

    def _extract_geographic(self, data):
        """Extract geographic boundaries from API response.

        Handles both dataset format (array of geographic entries) and
        site format (flat geographic object).

        Args:
            data (dict): Parsed API response

        Returns:
            ogr.Geometry or None: Combined geometry from all boundaries
        """
        geographic = data.get("attributes", {}).get("geographic")
        if geographic is None:
            return None

        # Datasets have an array of geographic entries
        if isinstance(geographic, list):
            entries = geographic
        else:
            # Sites have a flat object
            entries = [geographic]

        combined = None
        for entry in entries:
            wkt = entry.get("boundaries")
            if not wkt:
                # Sites may also have a coordinates field (centroid point)
                wkt = entry.get("coordinates")
            if not wkt:
                continue

            geom = self._extract_geometry_from_wkt(wkt)
            if geom is None:
                continue

            if combined is None:
                combined = geom.Clone()
            else:
                combined = combined.Union(geom)

        return combined

    def _extract_temporal(self, data):
        """Extract temporal extent from API response.

        Args:
            data (dict): Parsed API response

        Returns:
            tuple or None: (start_date, end_date) as ISO strings, or None
        """
        date_range = data.get("attributes", {}).get("general", {}).get("dateRange")
        if date_range is None:
            return None

        start = date_range.get("from")
        end = date_range.get("to")

        if start is None:
            return None

        # If end is null (ongoing), use start as end
        if end is None:
            end = start

        return (start, end)

    def _extract_external_references(self, data):
        """Extract followable external references (DOIs, URLs) from DEIMS metadata.

        Reads onlineDistribution.doi and onlineDistribution.onlineLocation URLs.
        Filters out null values, placeholder text, and non-URL strings.

        Args:
            data (dict): Parsed API response

        Returns:
            list[str]: Deduplicated list of followable references
        """
        refs = []
        seen = set()

        online_dist = data.get("attributes", {}).get("onlineDistribution")
        if online_dist is None:
            return refs

        # Check doi field
        doi_val = online_dist.get("doi")
        if doi_val and isinstance(doi_val, str):
            doi_val = doi_val.strip()
            if hf.doi_regexp.match(doi_val) or hf.https_regexp.match(doi_val):
                if doi_val not in seen:
                    refs.append(doi_val)
                    seen.add(doi_val)

        # Check onlineLocation URLs
        online_locations = online_dist.get("onlineLocation")
        if isinstance(online_locations, list):
            for loc in online_locations:
                if isinstance(loc, dict):
                    url_obj = loc.get("url")
                    if isinstance(url_obj, dict):
                        url_val = url_obj.get("value")
                    else:
                        url_val = url_obj
                    if url_val and isinstance(url_val, str):
                        url_val = url_val.strip()
                        if hf.doi_regexp.match(url_val) or hf.https_regexp.match(
                            url_val
                        ):
                            if url_val not in seen:
                                refs.append(url_val)
                                seen.add(url_val)

        return refs

    def _try_follow_reference(self, reference, folder, download_kwargs):
        """Try to follow an external reference to a supported provider.

        Uses lazy imports to avoid circular dependency (DEIMSSDR -> extent -> DEIMSSDR).

        Args:
            reference (str): DOI or URL to follow
            folder (str): Download target directory
            download_kwargs (dict): Keyword arguments for provider.download()

        Returns:
            dict or None: Follow info dict on success, None on failure
        """
        from geoextent.lib.extent import _get_content_providers
        from geoextent.lib.content_providers.providers import find_provider

        provider = find_provider(reference, _get_content_providers())
        if provider is None:
            logger.info(
                "DEIMS-SDR: external reference %s not matched by any provider, "
                "skipping",
                reference,
            )
            return None

        logger.info(
            "DEIMS-SDR dataset %s references %s -> following to %s",
            self.resource_uuid,
            reference,
            provider.name,
        )

        try:
            provider.download(folder, **download_kwargs)
            # Check that files were actually created
            if os.listdir(folder):
                logger.info(
                    "DEIMS-SDR -> %s: follow successful",
                    provider.name,
                )
                return {
                    "from": "DEIMS-SDR",
                    "to": provider.name,
                    "via": reference,
                }
            else:
                logger.warning(
                    "DEIMS-SDR -> %s: follow produced no files",
                    provider.name,
                )
                return None
        except Exception as e:
            logger.warning(
                "DEIMS-SDR -> %s: follow failed: %s",
                provider.name,
                e,
            )
            # Clean up any partial files
            for f in os.listdir(folder):
                fpath = os.path.join(folder, f)
                try:
                    if os.path.isdir(fpath):
                        shutil.rmtree(fpath)
                    else:
                        os.remove(fpath)
                except OSError:
                    pass
            return None

    def _create_geojson(self, geom, data, temporal, folder):
        """Create a GeoJSON file from extracted geometry and metadata.

        Args:
            geom (ogr.Geometry): The geometry to write
            data (dict): Original API response (for properties)
            temporal (tuple or None): (start, end) dates
            folder (str): Target directory

        Returns:
            str: Path to created GeoJSON file
        """
        geojson_geom = json.loads(geom.ExportToJson())
        title = data.get("title", "")

        properties = {
            "source": "DEIMS-SDR",
            "title": title,
            "resource_type": self.resource_type,
            "resource_id": self.resource_uuid,
            "url": self.reference,
        }

        if temporal:
            properties["start_time"] = temporal[0]
            properties["end_time"] = temporal[1]

        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": geojson_geom,
                    "properties": properties,
                }
            ],
        }

        filename = f"deims_{self.resource_type}_{self.resource_uuid}.geojson"
        filepath = os.path.join(folder, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)

        logger.debug(f"Created GeoJSON file: {filepath}")
        return filepath

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
        follow=True,
    ):
        """Extract metadata from DEIMS-SDR and create GeoJSON.

        DEIMS-SDR is metadata-only: it does not host data files.
        When ``follow=True`` and ``download_data=True``, external DOIs/URLs
        from the dataset metadata are followed to other supported providers
        (e.g., Zenodo, PANGAEA) for actual data extent extraction.

        Args:
            folder (str): Target directory for GeoJSON output
            follow (bool): Follow external DOIs/URLs to other providers
                (default True). Disable with ``--no-follow`` or ``follow=False``.
            (other parameters accepted for API compatibility but not used)

        Returns:
            str: Path to output directory containing GeoJSON file(s)
        """
        logger.info(
            f"Extracting metadata from DEIMS-SDR: {self.resource_type} "
            f"{self.resource_uuid}"
        )

        download_dir = os.path.join(
            folder, f"deims_{self.resource_type}_{self.resource_uuid}"
        )
        os.makedirs(download_dir, exist_ok=True)

        self._follow_info = None

        try:
            data = self._fetch_metadata()

            # Try to follow external references to other providers
            if follow and download_data and self.resource_type == "dataset":
                external_refs = self._extract_external_references(data)
                if external_refs:
                    download_kwargs = {
                        "throttle": throttle,
                        "download_data": download_data,
                        "show_progress": show_progress,
                        "max_size_bytes": max_size_bytes,
                        "max_download_method": max_download_method,
                        "max_download_method_seed": max_download_method_seed,
                        "download_skip_nogeo": download_skip_nogeo,
                        "download_skip_nogeo_exts": download_skip_nogeo_exts,
                        "max_download_workers": max_download_workers,
                    }
                    for ref in external_refs:
                        result = self._try_follow_reference(
                            ref, download_dir, download_kwargs
                        )
                        if result is not None:
                            self._follow_info = result
                            logger.info(
                                "DEIMS-SDR: successfully followed to %s via %s",
                                result["to"],
                                result["via"],
                            )
                            return download_dir

                    logger.info(
                        "DEIMS-SDR: no external references could be followed, "
                        "using own metadata"
                    )
                else:
                    logger.debug("DEIMS-SDR: no external references found in metadata")
            elif not follow:
                logger.info(
                    "DEIMS-SDR: follow disabled (--no-follow), using own metadata"
                )

            # Fall through: create GeoJSON from DEIMS metadata
            geom = self._extract_geographic(data)
            if geom is None:
                logger.warning(
                    f"No geographic data found for DEIMS-SDR "
                    f"{self.resource_type} {self.resource_uuid}"
                )
                return download_dir

            temporal = self._extract_temporal(data)
            self._create_geojson(geom, data, temporal, download_dir)
            return download_dir

        except requests.RequestException as e:
            logger.error(f"Error fetching DEIMS-SDR metadata: {e}")
            raise
