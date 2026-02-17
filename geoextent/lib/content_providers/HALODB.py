"""
HALO DB (DLR) content provider for geoextent.

HALO-DB is the web platform of a data retrieval and long-term archiving system
for the HALO research aircraft (High Altitude and LOng Range), operated by DLR
(German Aerospace Center).

Supported identifiers:
- Dataset URLs: https://halo-db.pa.op.dlr.de/dataset/{id}

Metadata extraction approach:
- Primary: GeoJSON search endpoint returns flight track geometry (LineString)
  and flight metadata (departure/arrival times, airports, mission)
- Fallback: HTML parsing of dataset page for temporal extent (mission dates)

HALO DB does not assign DOIs; datasets are identified by numeric ID and URL
only.  Primary data files require authentication for download, so this provider
always operates in metadata-only mode.
"""

import json
import logging
import os
import re

import requests
from bs4 import BeautifulSoup

from geoextent.lib.content_providers.providers import ContentProvider

logger = logging.getLogger("geoextent")

_BASE_URL = "https://halo-db.pa.op.dlr.de"
_DATASET_URL_RE = re.compile(
    r"https?://halo-db\.pa\.op\.dlr\.de/dataset/(\d+)",
    re.IGNORECASE,
)


class HALODB(ContentProvider):
    """Content provider for HALO DB (DLR aircraft research database).

    HALO DB does not assign DOIs to datasets; identification is by numeric ID
    and URL only.  The GeoJSON search endpoint provides structured metadata
    including flight track geometry for some datasets.
    """

    @classmethod
    def provider_info(cls):
        return {
            "name": "HALO DB",
            "description": (
                "HALO-DB is the web platform of a data retrieval and long-term "
                "archiving system for data based on observations of the HALO "
                "research aircraft (High Altitude and LOng Range), operated by "
                "DLR (German Aerospace Center). Contains ~9,800 datasets from "
                "115+ scientific missions covering atmospheric science, "
                "geophysics, and earth observation."
            ),
            "website": "https://halo-db.pa.op.dlr.de/",
            "supported_identifiers": [
                "https://halo-db.pa.op.dlr.de/dataset/{id}",
            ],
            "examples": [
                "https://halo-db.pa.op.dlr.de/dataset/745",
                "https://halo-db.pa.op.dlr.de/dataset/364",
            ],
            "notes": (
                "Metadata-only provider. HALO DB does not assign DOIs; "
                "datasets are identified by numeric ID and URL. Flight track "
                "geometry is extracted from the GeoJSON search API when "
                "available. Primary data files require authentication for "
                "download."
            ),
        }

    @property
    def supports_metadata_extraction(self):
        return True

    def __init__(self):
        super().__init__()
        self.name = "HALO DB"
        self.reference = None
        self.dataset_id = None
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "nuest/geoextent"})

    def validate_provider(self, reference):
        """Check if the reference is a HALO DB dataset URL.

        Args:
            reference (str): URL to validate

        Returns:
            bool: True if this is a HALO DB dataset URL
        """
        self.reference = reference

        m = _DATASET_URL_RE.search(reference)
        if m:
            self.dataset_id = m.group(1)
            return True

        return False

    def _search_dataset_geojson(self):
        """Search for this dataset in the GeoJSON search endpoint.

        The endpoint returns a paginated FeatureCollection.  Each feature that
        represents a dataset (as opposed to the first "coverage" feature) has a
        ``properties.link`` field with the full dataset URL.

        Returns:
            dict or None: GeoJSON feature for this dataset, or None
        """
        search_url = (
            f"{_BASE_URL}/search" f"?texts={self.dataset_id}" f"&format=geojson"
        )
        logger.debug("Searching HALO DB GeoJSON: %s", search_url)

        response = self.session.get(search_url, timeout=60)
        response.raise_for_status()
        data = response.json()

        # Find the feature matching our dataset
        dataset_url = f"{_BASE_URL}/dataset/{self.dataset_id}"
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            if props.get("link") == dataset_url:
                return feature

        return None

    def _parse_html_temporal(self):
        """Parse temporal extent from the HTML dataset page.

        Looks for the "Time period" section containing begin/end dates.

        Returns:
            tuple or None: (start_date, end_date) strings, or None
        """
        url = f"{_BASE_URL}/dataset/{self.dataset_id}"
        logger.debug("Fetching HALO DB dataset page: %s", url)

        response = self.session.get(url, timeout=60)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        begin_date = None
        end_date = None

        # Look for "Time period" heading in containertab sections
        for p in soup.find_all("p", style=lambda s: s and "font-weight:bold" in s):
            if "Time period" in p.get_text():
                container = p.parent
                if container is None:
                    continue

                ltab_divs = container.find_all("div", class_="ltab")
                rtab_divs = container.find_all("div", class_="rtab")

                for i, ltab in enumerate(ltab_divs):
                    if i >= len(rtab_divs):
                        break
                    label = ltab.get_text(strip=True)
                    # Remove asterisk markers (inherited-from-mission indicator)
                    date_text = rtab_divs[i].get_text(strip=True).rstrip("*").strip()
                    if "Begin" in label and date_text:
                        begin_date = date_text[:10]
                    elif "End" in label and date_text:
                        end_date = date_text[:10]

        if begin_date or end_date:
            return (begin_date or end_date, end_date or begin_date)
        return None

    def _extract_temporal_from_feature(self, feature):
        """Extract temporal extent from a GeoJSON feature's properties.

        Uses ``time_dep`` and ``time_arr`` (departure/arrival times) from the
        GeoJSON properties.

        Args:
            feature (dict): GeoJSON feature

        Returns:
            tuple or None: (start_date, end_date) strings, or None
        """
        props = feature.get("properties", {})
        time_dep = props.get("time_dep")
        time_arr = props.get("time_arr")

        if time_dep and time_arr:
            return (time_dep[:10], time_arr[:10])

        if time_dep:
            return (time_dep[:10], time_dep[:10])

        return None

    def _create_geojson(self, feature, temporal, folder):
        """Create a GeoJSON file from extracted metadata.

        Args:
            feature (dict or None): GeoJSON feature with geometry
            temporal (tuple or None): (start, end) dates
            folder (str): Target directory

        Returns:
            str or None: Path to created GeoJSON file, or None if no data
        """
        properties = {
            "source": "HALO DB",
            "dataset_id": self.dataset_id,
            "url": f"{_BASE_URL}/dataset/{self.dataset_id}",
        }

        if feature:
            props = feature.get("properties", {})
            for key in ("mission", "aircraft", "flight", "airport_dep", "airport_arr"):
                if props.get(key):
                    properties[key] = props[key]

        if temporal:
            properties["start_time"] = temporal[0]
            properties["end_time"] = temporal[1]

        geometry = feature.get("geometry") if feature else None

        if geometry is None and temporal is None:
            logger.warning(
                "HALO DB dataset %s: no geometry or temporal data found",
                self.dataset_id,
            )
            return None

        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": properties,
                }
            ],
        }

        filename = f"halodb_{self.dataset_id}.geojson"
        filepath = os.path.join(folder, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)

        logger.debug("Created GeoJSON file: %s", filepath)
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
    ):
        """Extract metadata from HALO DB and create GeoJSON.

        HALO DB primary data requires authentication, so this provider
        always operates in metadata-only mode regardless of ``download_data``.

        Args:
            folder (str): Target directory for GeoJSON output
            (other parameters accepted for API compatibility)

        Returns:
            str: Path to output directory
        """
        logger.info("Extracting metadata from HALO DB dataset %s", self.dataset_id)

        download_dir = os.path.join(folder, f"halodb_{self.dataset_id}")
        os.makedirs(download_dir, exist_ok=True)

        feature = None
        temporal = None

        # Step 1: Try GeoJSON search for structured metadata
        try:
            feature = self._search_dataset_geojson()
            if feature:
                temporal = self._extract_temporal_from_feature(feature)
                has_geometry = feature.get("geometry") is not None
                logger.info(
                    "HALO DB GeoJSON: found dataset %s (geometry=%s, temporal=%s)",
                    self.dataset_id,
                    "yes" if has_geometry else "no",
                    "yes" if temporal else "no",
                )
        except Exception as e:
            logger.warning(
                "HALO DB GeoJSON search failed for dataset %s: %s",
                self.dataset_id,
                e,
            )

        # Step 2: Fall back to HTML parsing for temporal extent if needed
        if temporal is None:
            try:
                temporal = self._parse_html_temporal()
                if temporal:
                    logger.info(
                        "HALO DB HTML: extracted temporal extent %s to %s",
                        temporal[0],
                        temporal[1],
                    )
            except Exception as e:
                logger.warning(
                    "HALO DB HTML parsing failed for dataset %s: %s",
                    self.dataset_id,
                    e,
                )

        # Step 3: Create GeoJSON from extracted metadata
        result = self._create_geojson(feature, temporal, download_dir)
        if result is None:
            logger.warning(
                "HALO DB dataset %s has no extractable spatial or temporal metadata",
                self.dataset_id,
            )

        return download_dir
