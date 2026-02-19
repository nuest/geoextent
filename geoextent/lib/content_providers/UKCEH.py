"""
UKCEH (UK Centre for Ecology & Hydrology) content provider for geoextent.

UKCEH operates the Environmental Information Data Centre (EIDC) at
catalogue.ceh.ac.uk. It publishes environmental science datasets with
DOI prefix 10.5285 and provides a JSON metadata API with structured
bounding boxes and temporal extents.

Two data download patterns exist:
- Apache datastore directory listings (individual files)
- data-package ZIPs (all-or-nothing)

Supported identifiers:
- DOIs: 10.5285/{uuid}
- URLs: https://catalogue.ceh.ac.uk/documents/{uuid}
"""

import json
import logging
import os
import re

from bs4 import BeautifulSoup

from .providers import DoiProvider
from .. import helpfunctions as hf

logger = logging.getLogger("geoextent")

# UUID pattern: 8-4-4-4-12 hex characters
_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)


class UKCEH(DoiProvider):
    """Content provider for UKCEH Environmental Information Data Centre (EIDC).

    Extracts spatial extent from ``boundingBoxes``, temporal extent from
    ``temporalExtents``, and file listings from the Apache datastore or
    data-package ZIP endpoints.
    """

    doi_prefixes = ("10.5285/",)

    CATALOGUE_BASE = "https://catalogue.ceh.ac.uk/documents/"

    @classmethod
    def provider_info(cls):
        return {
            "name": "UKCEH",
            "description": (
                "UKCEH (UK Centre for Ecology & Hydrology) operates the "
                "Environmental Information Data Centre (EIDC). It publishes "
                "environmental science datasets including water chemistry, "
                "land cover, biomass, and atmospheric data with DOI prefix 10.5285."
            ),
            "website": "https://catalogue.ceh.ac.uk/",
            "supported_identifiers": [
                "https://catalogue.ceh.ac.uk/documents/{uuid}",
                "https://doi.org/10.5285/{uuid}",
                "10.5285/{uuid}",
            ],
            "doi_prefix": "10.5285",
            "examples": [
                "10.5285/dd35316a-cecc-4f6d-9a21-74a0f6599e9e",
                "https://doi.org/10.5285/6a8b07f9-552e-408c-8351-595ee6a7fc5f",
            ],
        }

    def __init__(self):
        super().__init__()
        self.host = {
            "hostname": [
                "https://catalogue.ceh.ac.uk/documents/",
            ],
            "api": "https://catalogue.ceh.ac.uk/documents/",
        }
        self.record_id = None
        self.record = None
        self.name = "UKCEH"

    @property
    def supports_metadata_extraction(self):
        return True

    def validate_provider(self, reference):
        """Validate if the reference is a UKCEH dataset identifier.

        Matches:
        - DOI: 10.5285/{uuid}
        - URL: https://catalogue.ceh.ac.uk/documents/{uuid}
        """
        self.reference = reference

        # Try DOI prefix first — extract UUID from suffix
        doi_match = re.search(r"10\.5285/", reference)
        if doi_match:
            uuid_match = _UUID_RE.search(reference)
            if uuid_match:
                self.record_id = uuid_match.group(0).lower()
                return True
            # DOI prefix matches but no UUID — resolve and try again
            url = self.get_url
            uuid_match = _UUID_RE.search(url)
            if uuid_match:
                self.record_id = uuid_match.group(0).lower()
                return True
            return False

        # Try catalogue URL
        url = self.get_url
        for prefix in self.host["hostname"]:
            if url.startswith(prefix):
                uuid_match = _UUID_RE.search(url)
                if uuid_match:
                    self.record_id = uuid_match.group(0).lower()
                    return True

        return False

    def _get_metadata(self):
        """Fetch metadata from the UKCEH catalogue JSON API.

        Returns:
            dict: API response JSON
        """
        if self.record is not None:
            return self.record

        url = f"{self.host['api']}{self.record_id}?format=json"
        logger.debug("Fetching UKCEH metadata from: %s", url)
        resp = self._request(url, headers={"accept": "application/json"})
        resp.raise_for_status()
        self.record = resp.json()
        logger.debug(
            "Retrieved UKCEH metadata for record %s: %s",
            self.record_id,
            self.record.get("title", ""),
        )
        return self.record

    def _extract_spatial(self, metadata):
        """Parse boundingBoxes into a merged bounding box.

        Returns:
            dict or None: ``{"bbox": [W, S, E, N], "crs": "4326"}`` or None
        """
        bboxes = metadata.get("boundingBoxes", [])
        if not bboxes:
            return None

        min_lon = float("inf")
        min_lat = float("inf")
        max_lon = float("-inf")
        max_lat = float("-inf")

        for entry in bboxes:
            try:
                min_lon = min(min_lon, float(entry["westBoundLongitude"]))
                min_lat = min(min_lat, float(entry["southBoundLatitude"]))
                max_lon = max(max_lon, float(entry["eastBoundLongitude"]))
                max_lat = max(max_lat, float(entry["northBoundLatitude"]))
            except (KeyError, TypeError, ValueError):
                continue

        if min_lon == float("inf"):
            return None

        return {"bbox": [min_lon, min_lat, max_lon, max_lat], "crs": "4326"}

    def _extract_temporal(self, metadata):
        """Parse temporalExtents into [start_date, end_date].

        Merges all entries into overall [min_begin, max_end].

        Returns:
            list or None: ``[start_date, end_date]`` as YYYY-MM-DD strings
        """
        extents = metadata.get("temporalExtents", [])
        if not extents:
            return None

        all_begins = []
        all_ends = []

        for entry in extents:
            begin = entry.get("begin")
            end = entry.get("end")
            if begin:
                all_begins.append(begin[:10])
            if end:
                all_ends.append(end[:10])

        if not all_begins and not all_ends:
            return None

        # Use available dates for both if one direction is missing
        start = min(all_begins) if all_begins else min(all_ends)
        stop = max(all_ends) if all_ends else max(all_begins)
        return [start, stop]

    def _get_download_urls(self, metadata):
        """Parse onlineResources for download sources.

        Returns:
            dict: ``{"datastore_url": ... or None, "data_package_url": ... or None}``
        """
        resources = metadata.get("onlineResources", [])
        result = {"datastore_url": None, "data_package_url": None}

        for res in resources:
            func = res.get("function", "")
            url = res.get("url", "")

            if func == "fileAccess" and "datastore" in url:
                # Ensure trailing slash for directory listing
                result["datastore_url"] = url if url.endswith("/") else url + "/"
            elif func == "download" and "data-package" in url:
                # Derive ZIP URL from base URL
                result["data_package_url"] = url.rstrip("/") + ".zip"

        return result

    def _parse_datastore_listing(self, url):
        """Fetch and parse Apache autoindex HTML directory listing.

        Args:
            url: Datastore directory URL

        Returns:
            list or None: ``[{"name": ..., "url": ..., "size": int_bytes}, ...]``
                or None on failure
        """
        try:
            resp = self._request(url)
            resp.raise_for_status()
        except Exception:
            logger.debug("Failed to fetch datastore listing from %s", url)
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        files = []
        # Apache autoindex uses <pre> with <a> links
        pre = soup.find("pre")
        if not pre:
            # Some listings use <table> format
            for row in soup.find_all("tr"):
                link = row.find("a")
                if not link:
                    continue
                href = link.get("href", "")
                if href in ("", "/", "../") or "Parent Directory" in link.get_text():
                    continue
                # Skip directory links (ending with /)
                if href.endswith("/"):
                    continue

                name = href.split("/")[-1]
                file_url = url + name if not url.endswith("/") else url + name

                # Try to extract size from table cells
                size_bytes = 0
                cells = row.find_all("td")
                for cell in cells:
                    size_text = cell.get_text().strip()
                    parsed = self._parse_human_size(size_text)
                    if parsed > 0:
                        size_bytes = parsed
                        break

                files.append({"name": name, "url": file_url, "size": size_bytes})
        else:
            # Parse <pre> format: each line is "icon <a href>name</a> date size"
            text = pre.get_text()
            links = pre.find_all("a")

            for link in links:
                href = link.get("href", "")
                if href in ("", "/", "../") or "Parent Directory" in link.get_text():
                    continue
                if href.endswith("/"):
                    continue

                name = link.get_text().strip()
                file_url = url + href

                # Extract size from the text after the link
                # Apache format: "name                  date       size"
                size_bytes = 0
                # Find the line containing this filename
                for line in text.split("\n"):
                    if name in line:
                        # Size is typically the last token
                        tokens = line.strip().split()
                        if tokens:
                            parsed = self._parse_human_size(tokens[-1])
                            if parsed > 0:
                                size_bytes = parsed
                        break

                files.append({"name": name, "url": file_url, "size": size_bytes})

        if not files:
            return None

        logger.debug("Parsed %d files from datastore listing at %s", len(files), url)
        return files

    @staticmethod
    def _parse_human_size(size_str):
        """Parse Apache human-readable size strings like '56M', '6.4M', '419K'.

        Returns:
            int: Size in bytes, or 0 if unparseable
        """
        if not size_str:
            return 0

        size_str = size_str.strip()
        match = re.match(r"^(\d+(?:\.\d+)?)\s*([KMGTP]?)$", size_str, re.IGNORECASE)
        if not match:
            return 0

        value = float(match.group(1))
        unit = match.group(2).upper()

        multipliers = {
            "": 1,
            "K": 1024,
            "M": 1024 * 1024,
            "G": 1024 * 1024 * 1024,
            "T": 1024 * 1024 * 1024 * 1024,
            "P": 1024 * 1024 * 1024 * 1024 * 1024,
        }

        return int(value * multipliers.get(unit, 1))

    def _create_metadata_geojson(self, folder, metadata):
        """Write GeoJSON from UKCEH metadata.

        Creates one Feature per boundingBoxes entry so that both bbox merge
        and convex hull merge work correctly on the individual shapes.

        Returns:
            str or None: Path to created GeoJSON file, or None if no data
        """
        bboxes = metadata.get("boundingBoxes", [])
        temporal = self._extract_temporal(metadata)
        title = metadata.get("title", "")

        if not bboxes and temporal is None:
            logger.debug(
                "UKCEH record %s: no spatial or temporal metadata", self.record_id
            )
            return None

        properties = {
            "source": "UKCEH",
            "dataset_id": self.record_id,
            "title": title,
        }
        if temporal:
            properties["start_time"] = temporal[0]
            properties["end_time"] = temporal[1]

        features = []
        for entry in bboxes:
            try:
                west = float(entry["westBoundLongitude"])
                south = float(entry["southBoundLatitude"])
                east = float(entry["eastBoundLongitude"])
                north = float(entry["northBoundLatitude"])
            except (KeyError, TypeError, ValueError):
                continue

            # Point geometry when all corners collapse
            if west == east and south == north:
                geometry = {
                    "type": "Point",
                    "coordinates": [west, south],
                }
            else:
                geometry = {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [west, south],
                            [east, south],
                            [east, north],
                            [west, north],
                            [west, south],
                        ]
                    ],
                }

            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": dict(properties),
                }
            )

        # If no spatial features but we have temporal, create a null-geometry feature
        if not features and temporal:
            features.append(
                {
                    "type": "Feature",
                    "geometry": None,
                    "properties": properties,
                }
            )

        if not features:
            return None

        geojson_data = {
            "type": "FeatureCollection",
            "features": features,
        }

        geojson_file = os.path.join(folder, f"ukceh_{self.record_id}.geojson")
        with open(geojson_file, "w") as f:
            json.dump(geojson_data, f, indent=2)

        parts = []
        if bboxes:
            parts.append(f"{len(bboxes)} bounding box(es)")
        if temporal:
            parts.append(f"time={temporal[0]} to {temporal[1]}")
        logger.info(
            "Created GeoJSON metadata file for UKCEH record %s (%s)",
            self.record_id,
            ", ".join(parts),
        )
        return geojson_file

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
        """Download data from UKCEH.

        Strategy:
        1. Always fetch metadata
        2. If metadata-only: write GeoJSON from metadata
        3. If data download: try datastore listing first (selective files),
           fall back to data-package ZIP, then metadata GeoJSON
        """
        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        logger.info("Processing UKCEH record: %s", self.reference)

        # Always fetch metadata
        metadata = self._get_metadata()

        if not download_data:
            result = self._create_metadata_geojson(folder, metadata)
            if result is None:
                logger.warning(
                    "UKCEH record %s has no extractable spatial or temporal "
                    "metadata. Consider using download_data=True.",
                    self.record_id,
                )
            return

        # Check access limitation
        access = metadata.get("accessLimitation", {})
        access_code = access.get("code", "")
        if access_code and access_code != "Available":
            logger.warning(
                "UKCEH record %s has restricted access (%s). "
                "Falling back to metadata-only extraction.",
                self.record_id,
                access_code,
            )
            self._create_metadata_geojson(folder, metadata)
            return

        # Get download URLs
        urls = self._get_download_urls(metadata)

        # Try datastore listing first (enables selective file download)
        file_list = None
        if urls["datastore_url"]:
            file_list = self._parse_datastore_listing(urls["datastore_url"])

        if file_list:
            # Apply geospatial file filtering
            filtered_files = self._filter_geospatial_files(
                file_list,
                skip_non_geospatial=download_skip_nogeo,
                additional_extensions=download_skip_nogeo_exts,
            )

            if not filtered_files:
                logger.warning(
                    "No files selected after filtering. "
                    "Falling back to metadata-only extraction."
                )
                self._create_metadata_geojson(folder, metadata)
                return

            # Apply size filtering
            if max_size_bytes is not None:
                filtered_files, filtered_total_size, skipped_files = (
                    hf.filter_files_by_size(
                        filtered_files,
                        max_size_bytes,
                        max_download_method,
                        max_download_method_seed,
                        provider_name=(
                            self.name
                            if getattr(self, "_download_size_soft_limit", False)
                            else None
                        ),
                    )
                )
                if not filtered_files:
                    logger.warning("No files can be downloaded within the size limit")
                    return

            total_size = sum(f.get("size", 0) for f in filtered_files)
            logger.info(
                "Starting download of %d files from UKCEH datastore (%s bytes total)",
                len(filtered_files),
                f"{total_size:,}",
            )

            self._download_files_batch(
                filtered_files,
                folder,
                show_progress=show_progress,
                max_workers=max_download_workers,
            )

            logger.info(
                "Downloaded %d files from UKCEH record %s",
                len(filtered_files),
                self.record_id,
            )
            return

        # Fall back to data-package ZIP
        if urls["data_package_url"]:
            zip_url = urls["data_package_url"]
            logger.info("Datastore not available, trying data-package ZIP: %s", zip_url)

            # Check size via HEAD if we have a limit
            if max_size_bytes is not None:
                try:
                    head_resp = self.session.head(zip_url, allow_redirects=True)
                    content_length = int(head_resp.headers.get("content-length", 0))
                    if content_length > 0:
                        if content_length > max_size_bytes:
                            if getattr(self, "_download_size_soft_limit", False):
                                from ..exceptions import DownloadSizeExceeded

                                raise DownloadSizeExceeded(
                                    provider=self.name,
                                    estimated_size=content_length,
                                    max_size=max_size_bytes,
                                )
                            logger.warning(
                                "Data-package ZIP (%s bytes) exceeds size limit "
                                "(%s bytes). Falling back to metadata.",
                                f"{content_length:,}",
                                f"{max_size_bytes:,}",
                            )
                            self._create_metadata_geojson(folder, metadata)
                            return
                except Exception:
                    logger.debug("HEAD request failed for %s", zip_url)

            # Download the ZIP
            zip_path = os.path.join(folder, f"ukceh_{self.record_id}.zip")
            try:
                self._download_file_optimized(
                    zip_url, zip_path, show_progress=show_progress
                )
                logger.info(
                    "Downloaded data-package ZIP for UKCEH record %s", self.record_id
                )
                return
            except Exception:
                logger.warning(
                    "Failed to download data-package ZIP from %s. "
                    "Falling back to metadata-only extraction.",
                    zip_url,
                )

        # Neither download method worked — metadata fallback
        logger.info(
            "No data download available for UKCEH record %s. "
            "Using metadata-only extraction.",
            self.record_id,
        )
        self._create_metadata_geojson(folder, metadata)
