"""
SEANOE (SEA scieNtific Open data Edition) content provider for geoextent.

SEANOE is a marine science data repository operated by Ifremer/SISMER (France).
It uses DOI prefix 10.17882 and provides a REST JSON API at
https://www.seanoe.org/api/find-by-id/{id} that returns rich metadata including
geographic bounding boxes, temporal extents, and file listings.

Supported identifiers:
- DOIs: 10.17882/{id}
- URLs: https://www.seanoe.org/data/{section}/{id}/
"""

import json
import logging
import os
import re

from .providers import DoiProvider
from .. import helpfunctions as hf

logger = logging.getLogger("geoextent")


class SEANOE(DoiProvider):
    """Content provider for SEANOE (SEA scieNtific Open data Edition).

    Extracts spatial extent from ``geoExtendList``, temporal extent from
    ``temporalExtend``, and file listings from the ``files`` array in the
    SEANOE REST API response.
    """

    doi_prefixes = ("10.17882/",)

    API_BASE = "https://www.seanoe.org/api/find-by-id/"

    @classmethod
    def provider_info(cls):
        return {
            "name": "SEANOE",
            "description": (
                "SEANOE (SEA scieNtific Open data Edition) is a marine science "
                "data repository operated by Ifremer/SISMER (France). It publishes "
                "open-access oceanographic, marine biology, and geoscience datasets "
                "with DOI prefix 10.17882."
            ),
            "website": "https://www.seanoe.org/",
            "supported_identifiers": [
                "https://www.seanoe.org/data/{section}/{id}/",
                "https://doi.org/10.17882/{id}",
                "10.17882/{id}",
            ],
            "doi_prefix": "10.17882",
            "examples": [
                "10.17882/105467",
                "https://doi.org/10.17882/105467",
            ],
        }

    def __init__(self):
        super().__init__()
        self.host = {
            "hostname": [
                "https://www.seanoe.org/data/",
                "https://seanoe.org/data/",
            ],
            "api": "https://www.seanoe.org/api/find-by-id/",
        }
        self.record_id = None
        self.record = None
        self.name = "SEANOE"

    @property
    def supports_metadata_extraction(self):
        return True

    def validate_provider(self, reference):
        """Validate if the reference is a SEANOE dataset identifier.

        Matches:
        - DOI: 10.17882/{numeric_id}
        - URL: https://www.seanoe.org/data/{section}/{id}/
        """
        self.reference = reference

        # Try DOI prefix first — extract numeric ID from suffix
        doi_match = re.search(r"10\.17882/(\d+)", reference)
        if doi_match:
            self.record_id = doi_match.group(1)
            return True

        # Try landing page URL
        url = self.get_url
        for prefix in self.host["hostname"]:
            if url.startswith(prefix):
                # URL pattern: .../data/{section}/{id}/
                path = url[len(prefix) :]
                id_match = re.search(r"(\d+)/?$", path)
                if id_match:
                    self.record_id = id_match.group(1)
                    return True

        return False

    def _get_metadata(self):
        """Fetch metadata from the SEANOE REST API.

        Returns:
            dict: API response JSON
        """
        if self.record is not None:
            return self.record

        url = f"{self.host['api']}{self.record_id}"
        logger.debug("Fetching SEANOE metadata from: %s", url)
        resp = self._request(url, headers={"accept": "application/json"})
        resp.raise_for_status()
        self.record = resp.json()
        logger.debug(
            "Retrieved SEANOE metadata for record %s: %s",
            self.record_id,
            self.record.get("publicationDoi", ""),
        )
        return self.record

    def _extract_spatial(self, metadata):
        """Parse geoExtendList into a merged bounding box.

        Returns:
            dict or None: ``{"bbox": [W, S, E, N], "crs": "4326"}`` or None
        """
        geo_list = metadata.get("geoExtendList", [])
        if not geo_list:
            return None

        min_lon = float("inf")
        min_lat = float("inf")
        max_lon = float("-inf")
        max_lat = float("-inf")

        for entry in geo_list:
            try:
                min_lon = min(min_lon, float(entry["west"]))
                min_lat = min(min_lat, float(entry["south"]))
                max_lon = max(max_lon, float(entry["east"]))
                max_lat = max(max_lat, float(entry["north"]))
            except (KeyError, TypeError, ValueError):
                continue

        if min_lon == float("inf"):
            return None

        return {"bbox": [min_lon, min_lat, max_lon, max_lat], "crs": "4326"}

    def _extract_temporal(self, metadata):
        """Parse temporalExtend into [start_date, end_date].

        Returns:
            list or None: ``[start_date, end_date]`` as YYYY-MM-DD strings
        """
        temporal = metadata.get("temporalExtend", {})
        if not temporal:
            return None

        begin = temporal.get("begin")
        end = temporal.get("end")

        if not begin and not end:
            return None

        # Normalize: use available date for both if one is missing
        start = (begin or end)[:10]
        stop = (end or begin)[:10]
        return [start, stop]

    def _get_file_list(self, metadata):
        """Parse files array into standardized file info dicts.

        Only includes files with ``openAccess=True``.

        Returns:
            list: ``[{"name": ..., "url": ..., "size": int}, ...]``
        """
        files = metadata.get("files", [])
        file_list = []

        for f in files:
            if not f.get("openAccess", False):
                continue

            file_url = f.get("fileUrl")
            if not file_url:
                continue

            # Build a descriptive filename from the English label + extension
            label = f.get("label", {})
            en_label = label.get("en", "") if isinstance(label, dict) else ""
            file_name = f.get("fileName", "")

            if en_label and file_name:
                # Use label as base name with the original file extension
                ext = os.path.splitext(file_name)[1]
                name = en_label.replace(" ", "_") + ext
            elif en_label:
                name = en_label.replace(" ", "_")
            else:
                name = file_name

            # Clean up the name
            name = re.sub(r"[^a-zA-Z0-9_.\-]", "_", name)

            size = int(f.get("size", 0))

            file_list.append({"name": name, "url": file_url, "size": size})

        return file_list

    def _create_metadata_geojson(self, folder, metadata):
        """Write GeoJSON from SEANOE metadata.

        Creates one Feature per geoExtendList entry so that both bbox merge
        and convex hull merge work correctly on the individual shapes.

        Returns:
            str or None: Path to created GeoJSON file, or None if no data
        """
        geo_list = metadata.get("geoExtendList", [])
        temporal = self._extract_temporal(metadata)
        title = metadata.get("title", {})
        title_str = title.get("en", "") if isinstance(title, dict) else str(title)

        if not geo_list and temporal is None:
            logger.debug(
                "SEANOE record %s: no spatial or temporal metadata", self.record_id
            )
            return None

        properties = {
            "source": "SEANOE",
            "dataset_id": self.record_id,
            "title": title_str,
        }
        if temporal:
            properties["start_time"] = temporal[0]
            properties["end_time"] = temporal[1]

        features = []
        for entry in geo_list:
            try:
                west = float(entry["west"])
                south = float(entry["south"])
                east = float(entry["east"])
                north = float(entry["north"])
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

        geojson_file = os.path.join(folder, f"seanoe_{self.record_id}.geojson")
        with open(geojson_file, "w") as f:
            json.dump(geojson_data, f, indent=2)

        parts = []
        if geo_list:
            parts.append(f"{len(geo_list)} geographic extent(s)")
        if temporal:
            parts.append(f"time={temporal[0]} to {temporal[1]}")
        logger.info(
            "Created GeoJSON metadata file for SEANOE record %s (%s)",
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
        """Download data from SEANOE.

        Args:
            folder: Target directory for downloads
            throttle: Whether to throttle requests
            download_data: If False, metadata-only; if True, download files
            show_progress: Whether to show progress bars
            max_size_bytes: Maximum download size in bytes
            max_download_method: Method for size-limited downloads
            max_download_method_seed: Seed for random sampling
            download_skip_nogeo: Skip non-geospatial files
            download_skip_nogeo_exts: Additional geospatial extensions
            max_download_workers: Number of parallel download workers
        """
        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        logger.info("Processing SEANOE record: %s", self.reference)

        # Always fetch metadata
        metadata = self._get_metadata()

        if not download_data:
            result = self._create_metadata_geojson(folder, metadata)
            if result is None:
                logger.warning(
                    "SEANOE record %s has no extractable spatial or temporal "
                    "metadata. Consider using download_data=True.",
                    self.record_id,
                )
            return

        # Data download mode
        file_list = self._get_file_list(metadata)

        if not file_list:
            logger.warning(
                "SEANOE record %s has no open-access files. "
                "Falling back to metadata-only extraction.",
                self.record_id,
            )
            self._create_metadata_geojson(folder, metadata)
            return

        # Apply geospatial file filtering
        filtered_files = self._filter_geospatial_files(
            file_list,
            skip_non_geospatial=download_skip_nogeo,
            additional_extensions=download_skip_nogeo_exts,
        )

        if not filtered_files:
            logger.warning(
                "No files selected for download after filtering. "
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

        # Calculate total size
        total_size = sum(f.get("size", 0) for f in filtered_files)

        logger.info(
            "Starting download of %d files from SEANOE record %s (%s bytes total)",
            len(filtered_files),
            self.record_id,
            f"{total_size:,}",
        )

        # Download files
        self._download_files_batch(
            filtered_files,
            folder,
            show_progress=show_progress,
            max_workers=max_download_workers,
        )

        logger.info(
            "Downloaded %d files from SEANOE record %s",
            len(filtered_files),
            self.record_id,
        )
