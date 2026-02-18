import json
import logging
import os
import re
import time
from urllib.parse import urlparse

from .providers import DoiProvider
from .. import helpfunctions as hf
from ..exceptions import DownloadSizeExceeded

logger = logging.getLogger("geoextent")

# Soft limit for DwC-A downloads (1 GB).  The CLI will prompt interactively
# when the archive exceeds this; API callers can pass a higher ``max_size_bytes``.
DEFAULT_DWCA_SIZE_LIMIT = 1 * 1024 * 1024 * 1024


class GBIF(DoiProvider):
    """Content provider for GBIF (Global Biodiversity Information Facility).

    GBIF is the world's largest biodiversity data network with 2.5B+
    occurrence records.  Datasets are registered with DOIs under several
    prefixes (10.15468, 10.15470, 10.15472, 10.25607, 10.71819, 10.82144).

    Two extraction modes:
    - **metadata-only** (default): structured bounding boxes and temporal
      coverage from the GBIF Registry API.
    - **data download** (``download_data=True``): fetches the Darwin Core
      Archive (DwC-A) ZIP from the dataset's IPT endpoint and processes
      the contained occurrence/event files with ``fromDirectory()``.
    """

    doi_prefixes = (
        "10.15468/",
        "10.15470/",
        "10.15472/",
        "10.25607/",
        "10.71819/",
        "10.82144/",
    )

    API_BASE = "https://api.gbif.org/v1"

    # UUID pattern for GBIF dataset keys
    _UUID_RE = re.compile(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        re.IGNORECASE,
    )

    @classmethod
    def provider_info(cls):
        return {
            "name": "GBIF",
            "description": "Global Biodiversity Information Facility — the world's largest open biodiversity data network with 2.5B+ occurrence records. Supports metadata-only extraction from the Registry API and optional Darwin Core Archive (DwC-A) data download from institutional IPT servers.",
            "website": "https://www.gbif.org/",
            "supported_identifiers": [
                "https://www.gbif.org/dataset/{uuid}",
                "https://doi.org/10.15468/{id}",
                "10.15468/{id}",
                "10.15472/{id}",
            ],
            "doi_prefix": "10.15468",
            "examples": [
                "10.15468/6bleia",
                "https://www.gbif.org/dataset/378651d7-9b0f-4713-8255-4b1c46842c39",
            ],
            "notes": "Metadata-only by default. Use download_data=True (--download-data) to fetch the DwC-A ZIP from the IPT endpoint. Downloads >1 GB prompt for confirmation in the CLI.",
        }

    def __init__(self):
        super().__init__()
        self.host = {
            "hostname": [
                "gbif.org",
                "www.gbif.org",
                "api.gbif.org",
            ]
        }
        self.dataset_key = None
        self.metadata = None
        self.name = "GBIF"

    @property
    def supports_metadata_extraction(self):
        return True

    def validate_provider(self, reference):
        """Validate if the reference is a GBIF dataset identifier.

        Matches:
        - DOI prefixes: 10.15468/, 10.15470/, 10.15472/, 10.25607/, 10.71819/, 10.82144/
        - URLs on gbif.org / api.gbif.org containing a dataset UUID
        - Bare dataset UUIDs (when preceded by gbif.org hostname)
        """
        self.reference = reference

        # Check DOI prefixes
        for prefix in self.doi_prefixes:
            if prefix in reference:
                return True

        # Check hostname
        try:
            parsed = urlparse(reference)
            hostname = parsed.hostname or ""
        except Exception:
            hostname = ""

        if hostname in ("gbif.org", "www.gbif.org", "api.gbif.org"):
            # Try to extract UUID from URL path
            uuid_match = self._UUID_RE.search(parsed.path)
            if uuid_match:
                self.dataset_key = uuid_match.group(0)
            return True

        return False

    def _get_metadata(self):
        """Fetch full dataset metadata from the GBIF Registry API.

        If we only have a DOI (no dataset_key yet), first resolves via
        ``/v1/dataset/doi/{doi}`` which returns a search result.
        """
        if self.metadata:
            return self.metadata

        # Resolve DOI → dataset key if needed
        if not self.dataset_key:
            self._resolve_doi()

        if not self.dataset_key:
            raise ValueError(
                f"Could not resolve GBIF dataset key from: {self.reference}"
            )

        url = f"{self.API_BASE}/dataset/{self.dataset_key}"
        logger.debug("Fetching GBIF dataset metadata from: %s", url)
        response = self._request(url)
        response.raise_for_status()
        self.metadata = response.json()
        logger.debug(
            "Retrieved GBIF metadata for: %s",
            self.metadata.get("title", self.dataset_key),
        )
        return self.metadata

    def _resolve_doi(self):
        """Resolve a DOI to a GBIF dataset key via the search endpoint."""
        # Extract the DOI from the reference
        doi_match = re.search(r"(10\.\d{4,}/[^\s]+)", self.reference)
        if not doi_match:
            return

        doi = doi_match.group(1)
        url = f"{self.API_BASE}/dataset/doi/{doi}"
        logger.debug("Resolving GBIF DOI %s via: %s", doi, url)
        response = self._request(url)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        if results:
            self.dataset_key = results[0].get("key")
            logger.debug("Resolved DOI %s → dataset key %s", doi, self.dataset_key)

    def _extract_spatial_metadata(self):
        """Merge all geographicCoverages into a single bounding envelope.

        Returns:
            dict or None: ``{"bbox": [W, S, E, N], "crs": "4326"}``
        """
        if not self.metadata:
            self._get_metadata()

        coverages = self.metadata.get("geographicCoverages", [])
        if not coverages:
            return None

        min_lon = float("inf")
        min_lat = float("inf")
        max_lon = float("-inf")
        max_lat = float("-inf")

        for cov in coverages:
            bb = cov.get("boundingBox", {})
            try:
                min_lon = min(min_lon, float(bb["minLongitude"]))
                min_lat = min(min_lat, float(bb["minLatitude"]))
                max_lon = max(max_lon, float(bb["maxLongitude"]))
                max_lat = max(max_lat, float(bb["maxLatitude"]))
            except (KeyError, TypeError, ValueError):
                continue

        if min_lon == float("inf"):
            return None

        return {"bbox": [min_lon, min_lat, max_lon, max_lat], "crs": "4326"}

    def _extract_temporal_metadata(self):
        """Parse temporalCoverages into ``[start_date, end_date]``.

        Handles three GBIF temporalCoverage types:
        - ``"range"``: ``{"start": "...", "end": "..."}`` with ISO dates
        - ``"single"``: ``{"date": "..."}``
        - ``"verbatim"``: free-text; extract 4-digit years via regex

        Returns:
            list or None: ``[start_date, end_date]`` as YYYY-MM-DD or YYYY strings
        """
        if not self.metadata:
            self._get_metadata()

        coverages = self.metadata.get("temporalCoverages", [])
        if not coverages:
            return None

        all_dates = []

        for cov in coverages:
            cov_type = (
                cov.get("type", "").lower() if isinstance(cov.get("type"), str) else ""
            )

            if cov_type == "range" or ("start" in cov and "end" in cov):
                start = self._parse_iso_date(cov.get("start"))
                end = self._parse_iso_date(cov.get("end"))
                if start:
                    all_dates.append(start)
                if end:
                    all_dates.append(end)
            elif cov_type == "single_date" or "date" in cov:
                date = self._parse_iso_date(cov.get("date"))
                if date:
                    all_dates.append(date)
            elif cov_type == "verbatim_date" or "period" in cov:
                text = cov.get("period", "")
                years = re.findall(r"\b((?:19|20)\d{2})\b", text)
                all_dates.extend(years)

        if not all_dates:
            return None

        return [min(all_dates), max(all_dates)]

    @staticmethod
    def _parse_iso_date(date_str):
        """Extract a date from an ISO 8601 string, returning YYYY-MM-DD."""
        if not date_str:
            return None
        # Handle both "2020-01-15" and "2020-01-15T00:00:00.000+0000"
        match = re.match(r"(\d{4}-\d{2}-\d{2})", str(date_str))
        if match:
            return match.group(1)
        # Fall back to year only
        match = re.match(r"(\d{4})", str(date_str))
        if match:
            return match.group(1)
        return None

    def _get_dwca_endpoint(self):
        """Find the DWC_ARCHIVE endpoint URL from dataset metadata.

        Returns:
            str or None: URL of the DwC-A ZIP
        """
        if not self.metadata:
            self._get_metadata()

        for ep in self.metadata.get("endpoints", []):
            if ep.get("type") == "DWC_ARCHIVE":
                return ep.get("url")
        return None

    def _check_dwca_size(self, url):
        """Issue a HEAD request to estimate the DwC-A download size.

        Returns:
            int or None: Content-Length in bytes, or None if unavailable
        """
        try:
            response = self.session.head(url, allow_redirects=True, timeout=30)
            length = response.headers.get("Content-Length")
            if length:
                return int(length)
        except Exception as e:
            logger.debug("HEAD request for DwC-A size failed: %s", e)
        return None

    def _create_geojson_from_metadata(self, target_folder, spatial, temporal):
        """Create a GeoJSON file from GBIF metadata for geoextent processing."""
        bbox = spatial["bbox"]
        min_lon, min_lat, max_lon, max_lat = bbox

        properties = {
            "source": self.name,
            "dataset_key": self.dataset_key,
            "title": self.metadata.get("title", "") if self.metadata else "",
        }

        if temporal and isinstance(temporal, list) and len(temporal) >= 2:
            if temporal[0]:
                properties["start_time"] = temporal[0]
            if temporal[1]:
                properties["end_time"] = temporal[1]

        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [min_lon, min_lat],
                                [max_lon, min_lat],
                                [max_lon, max_lat],
                                [min_lon, max_lat],
                                [min_lon, min_lat],
                            ]
                        ],
                    },
                    "properties": properties,
                }
            ],
        }

        safe_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", self.dataset_key or "unknown")
        geojson_file = os.path.join(target_folder, f"gbif_{safe_id}.geojson")
        with open(geojson_file, "w") as f:
            json.dump(geojson_data, f, indent=2)

        temporal_info = f" with temporal extent {temporal}" if temporal else ""
        logger.info(
            "Created GeoJSON metadata file for GBIF dataset %s%s",
            self.dataset_key,
            temporal_info,
        )

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
        """Download data from GBIF.

        Args:
            folder: Target directory for downloads
            throttle: Whether to throttle requests (1 s delay for IPT)
            download_data: If False, metadata-only; if True, fetch DwC-A ZIP
            show_progress: Whether to show progress bars
            max_size_bytes: Maximum download size in bytes (None = use DEFAULT_DWCA_SIZE_LIMIT)
            max_download_method: Method for size-limited downloads
            max_download_method_seed: Seed for random sampling
            download_skip_nogeo: Skip if no geospatial files found
            download_skip_nogeo_exts: Additional geospatial extensions
            max_download_workers: Number of parallel download workers

        Returns:
            str: Path to downloaded data directory
        """
        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        logger.info("Processing GBIF dataset: %s", self.reference)

        # Always fetch metadata (needed for both modes)
        self._get_metadata()
        spatial = self._extract_spatial_metadata()
        temporal = self._extract_temporal_metadata()

        if not download_data:
            # Metadata-only extraction
            if spatial and "bbox" in spatial:
                self._create_geojson_from_metadata(folder, spatial, temporal)
            else:
                logger.warning(
                    "GBIF dataset %s has no extractable spatial metadata. "
                    "Consider using download_data=True to download the DwC-A.",
                    self.dataset_key,
                )
            return folder

        # Data download mode — fetch the DwC-A ZIP
        dwca_url = self._get_dwca_endpoint()
        if not dwca_url:
            logger.warning(
                "GBIF dataset %s has no DWC_ARCHIVE endpoint. "
                "Falling back to metadata-only extraction.",
                self.dataset_key,
            )
            if spatial and "bbox" in spatial:
                self._create_geojson_from_metadata(folder, spatial, temporal)
            return folder

        # Check size against limit
        effective_limit = (
            max_size_bytes if max_size_bytes is not None else DEFAULT_DWCA_SIZE_LIMIT
        )
        estimated_size = self._check_dwca_size(dwca_url)

        if estimated_size is not None and estimated_size > effective_limit:
            raise DownloadSizeExceeded(estimated_size, effective_limit, self.name)

        # Download the DwC-A ZIP
        zip_filename = f"gbif_{self.dataset_key}.zip"
        zip_path = os.path.join(folder, zip_filename)

        try:
            if throttle:
                time.sleep(1)

            logger.info(
                "Downloading DwC-A from %s (%s)",
                dwca_url,
                f"{estimated_size:,} bytes" if estimated_size else "unknown size",
            )
            self._download_file_optimized(
                dwca_url, zip_path, show_progress=show_progress
            )
        except Exception as e:
            logger.warning(
                "DwC-A download failed for GBIF dataset %s: %s. "
                "Falling back to metadata-only extraction.",
                self.dataset_key,
                e,
            )
            if os.path.exists(zip_path):
                os.remove(zip_path)
            if spatial and "bbox" in spatial:
                self._create_geojson_from_metadata(folder, spatial, temporal)
            return folder

        return folder
