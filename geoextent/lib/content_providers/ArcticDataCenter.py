import json
import logging
import os
import re
from urllib.parse import quote, urlparse, unquote

from .providers import DoiProvider
from .. import helpfunctions as hf

logger = logging.getLogger("geoextent")


class ArcticDataCenter(DoiProvider):
    """Content provider for NSF Arctic Data Center (arcticdata.io).

    The Arctic Data Center is the primary data and software repository for
    NSF-funded Arctic research. It runs on DataONE/Metacat infrastructure
    and provides a Solr API with structured geospatial and temporal metadata.

    Supports:
    - DOI prefix: 10.18739/
    - Hostnames: arcticdata.io
    - Identifier types: DOIs (doi:10.18739/...) and URN UUIDs (urn:uuid:...)
    """

    doi_prefixes = ("10.18739/",)

    @classmethod
    def provider_info(cls):
        return {
            "name": "Arctic Data Center",
            "description": "NSF Arctic Data Center is the primary repository for NSF-funded Arctic research data. It provides long-term data archiving and supports ISO 19115 metadata with rich geospatial coverage information.",
            "website": "https://arcticdata.io/",
            "supported_identifiers": [
                "https://arcticdata.io/catalog/view/{doi}",
                "https://doi.org/10.18739/{id}",
                "10.18739/{id}",
            ],
            "doi_prefix": "10.18739",
            "examples": [
                "10.18739/A2KW57K57",
            ],
            "notes": "Supports metadata-only extraction via DataONE Solr API (geospatial coverage from ISO 19115 metadata).",
        }

    API_BASE = "https://arcticdata.io/metacat/d1/mn/v2"

    def __init__(self):
        super().__init__()
        self.host = {
            "hostname": [
                "arcticdata.io",
            ]
        }
        self.doi_pattern = re.compile(r"10\.18739/")
        self.urn_pattern = re.compile(
            r"urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            re.IGNORECASE,
        )
        self.dataset_id = None
        self.metadata = None
        self.name = "Arctic Data Center"

    @property
    def supports_metadata_extraction(self):
        return True

    def validate_provider(self, reference):
        """Validate if the reference is a supported Arctic Data Center identifier.

        Args:
            reference (str): DOI, URL, URN UUID, or dataset identifier

        Returns:
            bool: True if valid Arctic Data Center reference, False otherwise
        """
        self.reference = reference

        # Check for ADC DOI prefix
        if self.doi_pattern.search(reference):
            # Extract the full DOI suffix
            doi_match = re.search(r"(10\.18739/[^\s]+)", reference)
            if doi_match:
                self.dataset_id = "doi:" + doi_match.group(1)
            return True

        # Check for URN UUID pattern
        urn_match = self.urn_pattern.search(reference)
        if urn_match:
            self.dataset_id = urn_match.group(0)
            return True

        # Check for arcticdata.io URLs
        try:
            parsed = urlparse(reference)
            hostname = parsed.hostname or ""
        except Exception:
            hostname = ""

        if hostname == "arcticdata.io" or hostname.endswith(".arcticdata.io"):
            # Extract dataset ID from catalog URL
            # Pattern: /catalog/view/doi%3A10.18739%2F...
            # Pattern: /catalog/view/urn%3Auuid%3A...
            path = unquote(parsed.path) if parsed.path else ""

            doi_in_path = re.search(r"(doi:10\.18739/[^\s/]+)", path)
            if doi_in_path:
                self.dataset_id = doi_in_path.group(1)
                return True

            urn_in_path = self.urn_pattern.search(path)
            if urn_in_path:
                self.dataset_id = urn_in_path.group(0)
                return True

            # Accept any URL on arcticdata.io
            return True

        return False

    def _get_metadata(self):
        """Fetch dataset metadata from the DataONE Solr API.

        Returns:
            dict: Metadata document from Solr
        """
        if not self.dataset_id:
            raise ValueError("No dataset ID available for metadata extraction")

        solr_url = (
            f'{self.API_BASE}/query/solr/?q=id:"{self.dataset_id}"'
            f"&fl=id,title,northBoundCoord,southBoundCoord,"
            f"eastBoundCoord,westBoundCoord,beginDate,endDate,"
            f"documents,resourceMap,abstract"
            f"&wt=json"
        )

        logger.debug(f"Fetching Arctic Data Center metadata from: {solr_url}")
        response = self._request(solr_url)
        response.raise_for_status()
        data = response.json()

        docs = data.get("response", {}).get("docs", [])
        if not docs:
            raise ValueError(
                f"No metadata found for Arctic Data Center dataset: {self.dataset_id}"
            )

        self.metadata = docs[0]
        logger.debug(
            f"Retrieved metadata for Arctic Data Center dataset: {self.metadata.get('title', self.dataset_id)}"
        )
        return self.metadata

    def _extract_spatial_metadata(self):
        """Extract spatial extent from Arctic Data Center metadata.

        Returns:
            dict or None: Spatial metadata with bbox in [W, S, E, N] format, or None
        """
        if not self.metadata:
            self._get_metadata()

        try:
            north = float(self.metadata["northBoundCoord"])
            south = float(self.metadata["southBoundCoord"])
            east = float(self.metadata["eastBoundCoord"])
            west = float(self.metadata["westBoundCoord"])
            return {"bbox": [west, south, east, north], "crs": "4326"}
        except (KeyError, TypeError, ValueError) as e:
            logger.debug(f"Could not extract spatial metadata: {e}")
            return None

    def _extract_temporal_metadata(self):
        """Extract temporal extent from Arctic Data Center metadata.

        Returns:
            list or None: Temporal extent as [start_date, end_date], or None
        """
        if not self.metadata:
            self._get_metadata()

        begin = self.metadata.get("beginDate")
        end = self.metadata.get("endDate")

        if not begin and not end:
            return None

        # Parse ISO 8601 dates to YYYY-MM-DD
        def parse_date(date_str):
            if not date_str:
                return None
            # Handle formats like "2020-01-01T00:00:00Z" or "2020-01-01"
            return date_str[:10]

        start_date = parse_date(begin)
        end_date = parse_date(end)

        if start_date or end_date:
            return [start_date or end_date, end_date or start_date]
        return None

    def _get_data_files(self):
        """Fetch data file list from the DataONE Solr API.

        Returns:
            list: List of file dicts with 'name', 'url', 'size', 'id' keys
        """
        if not self.dataset_id:
            raise ValueError("No dataset ID available")

        # Get the resource map ID for this dataset
        if not self.metadata:
            self._get_metadata()

        resource_maps = self.metadata.get("resourceMap", [])
        if not resource_maps:
            logger.warning(f"No resource maps found for dataset {self.dataset_id}")
            return []

        # Query for data files in the first resource map
        resource_map_id = resource_maps[0]
        solr_url = (
            f"{self.API_BASE}/query/solr/"
            f'?q=resourceMap:"{resource_map_id}"+AND+formatType:DATA'
            f"&fl=id,fileName,formatId,size"
            f"&wt=json&rows=1000"
        )

        logger.debug(f"Fetching Arctic Data Center file list from: {solr_url}")
        response = self._request(solr_url)
        response.raise_for_status()
        data = response.json()

        docs = data.get("response", {}).get("docs", [])
        files = []
        for doc in docs:
            file_id = doc.get("id", "")
            encoded_id = quote(file_id, safe="")
            files.append(
                {
                    "name": doc.get("fileName", file_id),
                    "url": f"{self.API_BASE}/object/{encoded_id}",
                    "size": doc.get("size", 0),
                    "id": file_id,
                }
            )

        logger.debug(f"Found {len(files)} data files in Arctic Data Center dataset")
        return files

    def _create_geojson_from_metadata(self, target_folder, spatial, temporal):
        """Create a GeoJSON file from metadata for geoextent processing.

        Args:
            target_folder: Directory to create the GeoJSON file in
            spatial: Spatial metadata dict with 'bbox' and 'crs' keys
            temporal: Temporal metadata list with [start_date, end_date] or None
        """
        bbox = spatial["bbox"]
        min_lon, min_lat, max_lon, max_lat = bbox

        properties = {
            "source": self.name,
            "dataset_id": self.dataset_id,
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

        # Sanitize dataset_id for filename
        safe_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", self.dataset_id)
        geojson_file = os.path.join(target_folder, f"arcticdata_{safe_id}.geojson")
        with open(geojson_file, "w") as f:
            json.dump(geojson_data, f, indent=2)

        temporal_info = f" with temporal extent {temporal}" if temporal else ""
        logger.info(
            f"Created GeoJSON metadata file for {self.name} dataset "
            f"{self.dataset_id}{temporal_info}"
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
        """Download data from Arctic Data Center.

        Args:
            folder (str): Target directory for downloads
            throttle (bool): Whether to throttle requests
            download_data (bool): Whether to download actual data
            show_progress (bool): Whether to show progress bars
            max_size_bytes (int): Maximum download size in bytes
            max_download_method (str): Method for size-limited downloads
            max_download_method_seed (int): Seed for random sampling
            download_skip_nogeo (bool): Skip if no geospatial files found
            download_skip_nogeo_exts (set): Additional geospatial extensions
            max_download_workers (int): Number of parallel download workers

        Returns:
            str: Path to downloaded data directory
        """
        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        logger.info(f"Processing Arctic Data Center dataset: {self.reference}")

        if not download_data:
            # Metadata-only extraction
            try:
                self._get_metadata()
                spatial = self._extract_spatial_metadata()
                temporal = self._extract_temporal_metadata()

                if spatial and "bbox" in spatial:
                    self._create_geojson_from_metadata(folder, spatial, temporal)
                else:
                    logger.warning(
                        f"Arctic Data Center dataset {self.dataset_id} has no "
                        "extractable spatial metadata. Consider using "
                        "download_data=True to download actual data files."
                    )
            except Exception as e:
                logger.error(f"Failed to extract Arctic Data Center metadata: {e}")
                raise
            return folder

        # Full download mode
        try:
            file_list = self._get_data_files()
        except Exception as e:
            logger.error(f"Error fetching Arctic Data Center file list: {e}")
            raise

        if not file_list:
            logger.warning(
                f"No data files found in Arctic Data Center dataset {self.dataset_id}"
            )
            return folder

        # Apply geospatial filtering
        if download_skip_nogeo:
            file_list = self._filter_geospatial_files(
                file_list,
                skip_non_geospatial=True,
                additional_extensions=download_skip_nogeo_exts,
            )

        if not file_list:
            logger.warning("No geospatial files found after filtering")
            return folder

        # Apply size limit
        if max_size_bytes is not None:
            selected_files, total_size, skipped = hf.filter_files_by_size(
                file_list,
                max_size_bytes,
                max_download_method,
                max_download_method_seed,
            )
            if not selected_files:
                logger.warning("No files can be downloaded within the size limit")
                return folder
            file_list = selected_files

        total_size = sum(f.get("size", 0) for f in file_list)
        logger.info(
            f"Downloading {len(file_list)} files from Arctic Data Center "
            f"({total_size:,} bytes total)"
        )

        self._download_files_batch(
            file_list,
            folder,
            show_progress=show_progress,
            max_workers=max_download_workers,
        )

        return folder
