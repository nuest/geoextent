"""
Abstract base class for CKAN-based data repository providers.

CKAN (Comprehensive Knowledge Archive Network) is an open-source data management
system used by many research data repositories. This class provides common
functionality for interacting with CKAN APIs.

See: https://docs.ckan.org/en/latest/api/
"""

import logging
import re
from abc import abstractmethod
from requests import HTTPError
from .providers import DoiProvider
from .. import helpfunctions as hf


class CKANProvider(DoiProvider):
    """
    Abstract base class for CKAN-based repository providers.

    CKAN repositories share a common API structure, making it possible to
    create a reusable base class for common operations like metadata retrieval,
    file listing, and downloads.

    Child classes must implement:
    - validate_provider(reference): Validate and extract dataset identifier
    - Configure self.host with API endpoint
    - Set self.name for logging purposes
    """

    @property
    def supports_metadata_extraction(self):
        return True

    def __init__(self):
        super().__init__()
        self.log = logging.getLogger("geoextent")
        self.host = None  # Child classes must set this
        self.reference = None
        self.dataset_id = None
        self.name = "CKAN"  # Child classes should override
        self.throttle = False
        self.metadata = None

    @abstractmethod
    def validate_provider(self, reference):
        """
        Validate if the reference is supported by this provider.

        Must set:
        - self.reference
        - self.dataset_id

        Returns:
            bool: True if this provider can handle the reference
        """
        pass

    def _get_metadata(self):
        """
        Get dataset metadata from CKAN API.

        Uses the CKAN package_show action to retrieve complete dataset metadata
        including resources (files), spatial extent, temporal extent, etc.

        Returns:
            dict: Complete dataset metadata from CKAN API

        Raises:
            HTTPError: If the dataset doesn't exist or API request fails
        """
        if not self.dataset_id:
            raise ValueError("No dataset ID available for metadata extraction")

        # CKAN API standard endpoint
        api_url = f"{self.host['api']}action/package_show"

        try:
            response = self._request(
                api_url,
                params={"id": self.dataset_id},
                throttle=self.throttle,
            )
            response.raise_for_status()

            api_response = response.json()

            # CKAN API returns data in a standard wrapper
            if not api_response.get("success"):
                error_msg = api_response.get("error", {}).get(
                    "message", "Unknown error"
                )
                raise HTTPError(f"CKAN API error: {error_msg}")

            self.metadata = api_response.get("result")

            if not self.metadata:
                raise ValueError(f"No metadata returned for dataset {self.dataset_id}")

            self.log.debug(
                f"Retrieved metadata for {self.name} dataset {self.dataset_id}"
            )
            return self.metadata

        except Exception as e:
            error_msg = (
                f"The {self.name} dataset {self.dataset_id} could not be retrieved. "
                f"Error: {str(e)}"
            )
            self.log.warning(error_msg)
            raise HTTPError(error_msg)

    def _get_file_information(self):
        """
        Extract file information from CKAN dataset metadata.

        Returns:
            list: List of file dictionaries with keys:
                - name: Filename
                - url: Download URL
                - size: File size in bytes
                - format: File format/extension
                - description: File description (if available)
        """
        if not self.metadata:
            self._get_metadata()

        resources = self.metadata.get("resources", [])

        if not resources:
            self.log.warning(
                f"No resources found in {self.name} dataset {self.dataset_id}"
            )
            return []

        files = []
        for resource in resources:
            # Check if resource is accessible
            # Some CKAN instances mark restricted resources
            if resource.get("restricted", {}).get("allowed", True) is False:
                self.log.debug(
                    f"Skipping restricted resource: {resource.get('name', 'unnamed')}"
                )
                continue

            # Extract file information
            file_info = {
                "name": resource.get("name") or resource.get("id"),
                "url": resource.get("url"),
                "size": resource.get("size", 0),
                "format": resource.get("format", "").lower(),
                "description": resource.get("description", ""),
                "id": resource.get("id"),
            }

            # Only include if we have a valid download URL
            if file_info["url"]:
                files.append(file_info)
            else:
                self.log.debug(f"Skipping resource without URL: {file_info['name']}")

        self.log.info(f"Found {len(files)} downloadable files in {self.name} dataset")
        return files

    def _extract_spatial_metadata(self):
        """
        Extract spatial extent metadata from CKAN dataset.

        CKAN datasets may include spatial information in various formats.
        This method attempts to extract bounding box coordinates if available.

        Returns:
            dict or None: Spatial metadata with bbox in [W, S, E, N] format, or None
        """
        if not self.metadata:
            self._get_metadata()

        # Try to find spatial extent in common CKAN metadata fields
        spatial_data = None

        # Check for spatial coverage in extras
        extras = self.metadata.get("extras", [])
        for extra in extras:
            key = extra.get("key", "")
            value = extra.get("value", "")

            if key in ["spatial", "spatial-reference-system", "bbox"]:
                spatial_data = value
                break

        # Also check direct spatial field (some CKAN instances)
        if not spatial_data and "spatial" in self.metadata:
            spatial_data = self.metadata.get("spatial")

        # Try to parse spatial data if found
        if spatial_data:
            try:
                # Handle JSON string
                if isinstance(spatial_data, str):
                    import json

                    spatial_data = json.loads(spatial_data)

                # Extract coordinates (various formats)
                if isinstance(spatial_data, dict):
                    # GeoJSON format
                    if "coordinates" in spatial_data:
                        # This would need proper GeoJSON parsing
                        pass
                    # Bounding box format
                    elif all(
                        k in spatial_data for k in ["west", "south", "east", "north"]
                    ):
                        return {
                            "bbox": [
                                float(spatial_data["west"]),
                                float(spatial_data["south"]),
                                float(spatial_data["east"]),
                                float(spatial_data["north"]),
                            ],
                            "crs": "4326",
                        }
            except Exception as e:
                self.log.debug(f"Could not parse spatial metadata: {e}")

        return None

    def _extract_temporal_metadata(self):
        """
        Extract temporal extent metadata from CKAN dataset.

        Returns:
            list or None: Temporal extent as [start_date, end_date], or None
        """
        if not self.metadata:
            self._get_metadata()

        # Check for temporal coverage in extras
        extras = self.metadata.get("extras", [])
        start_date = None
        end_date = None

        for extra in extras:
            key = extra.get("key", "")
            value = extra.get("value", "")

            if key in ["temporal_start", "temporal-extent-begin"]:
                start_date = value
            elif key in ["temporal_end", "temporal-extent-end"]:
                end_date = value

        if start_date or end_date:
            return [start_date, end_date]

        return None

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
        """
        Download files from CKAN dataset.

        Parameters:
        - folder: Directory to store downloaded files
        - throttle: Rate limiting for API calls
        - download_data: If True, downloads actual data files. If False, metadata only.
        - show_progress: Show download progress bars
        - max_size_bytes: Maximum total download size in bytes
        - max_download_method: Method for file selection when size limited ("ordered", "random")
        - max_download_method_seed: Random seed for reproducible sampling
        - download_skip_nogeo: Skip files that don't appear geospatial
        - download_skip_nogeo_exts: Additional file extensions to consider geospatial
        - max_download_workers: Number of parallel download workers
        """
        from tqdm import tqdm

        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        self.throttle = throttle

        if not download_data:
            # Metadata-only mode: extract spatial and temporal metadata and create a GeoJSON file for processing
            try:
                metadata = self._get_metadata()
                self.log.info(
                    f"{self.name} metadata extracted for dataset {self.dataset_id}"
                )

                # Try to extract spatial and temporal metadata
                spatial = self._extract_spatial_metadata()
                temporal = self._extract_temporal_metadata()

                if spatial and "bbox" in spatial:
                    # Create a GeoJSON file with the bbox and temporal extent for geoextent to process
                    self._create_geojson_from_metadata(
                        folder, spatial, temporal, metadata
                    )
                else:
                    self.log.warning(
                        f"{self.name} dataset {self.dataset_id} has no extractable spatial metadata. "
                        "Consider using download_data=True to download actual data files."
                    )
                return
            except Exception as e:
                self.log.error(f"Failed to extract {self.name} metadata: {e}")
                raise

        self.log.debug(f"Downloading {self.name} dataset: {self.dataset_id}")

        try:
            # Get file information
            file_info = self._get_file_information()

            if not file_info:
                self.log.warning(
                    f"No files found in {self.name} dataset {self.dataset_id}"
                )
                return

            # Apply geospatial filtering if requested
            if download_skip_nogeo:
                filtered_files = self._filter_geospatial_files(
                    file_info,
                    skip_non_geospatial=download_skip_nogeo,
                    max_size_mb=None,
                    additional_extensions=download_skip_nogeo_exts,
                )
            else:
                filtered_files = file_info

            # Apply size filtering if specified
            if max_size_bytes is not None:
                selected_files, total_size, skipped_files = hf.filter_files_by_size(
                    filtered_files,
                    max_size_bytes,
                    max_download_method,
                    max_download_method_seed,
                )
                if not selected_files:
                    self.log.warning("No files can be downloaded within the size limit")
                    return
                final_files = selected_files
            else:
                final_files = filtered_files
                total_size = sum(f.get("size", 0) for f in final_files)

            if not final_files:
                self.log.warning(f"No files selected for download after filtering")
                return

            # Log download summary
            self.log.info(
                f"Starting download of {len(final_files)} files from {self.name} "
                f"dataset {self.dataset_id} ({total_size:,} bytes total)"
            )

            # Use parallel download batch method from parent class
            self._download_files_batch(
                final_files,
                folder,
                show_progress=show_progress,
                max_workers=max_download_workers,
            )

            self.log.info(
                f"Downloaded {len(final_files)} files from {self.name} "
                f"dataset {self.dataset_id} ({total_size:,} bytes total)"
            )

        except Exception as e:
            self.log.error(f"Error downloading from {self.name}: {e}")
            raise

    def _create_geojson_from_metadata(self, target_folder, spatial, temporal, metadata):
        """
        Create a GeoJSON file from metadata for geoextent processing.

        This allows metadata-only extraction to work by creating a file that
        geoextent can process to extract the spatial and temporal extent.

        Args:
            target_folder: Directory to create the GeoJSON file in
            spatial: Spatial metadata dict with 'bbox' and 'crs' keys
            temporal: Temporal metadata list with [start_date, end_date] or None
            metadata: Full dataset metadata
        """
        import json
        import os

        bbox = spatial["bbox"]
        # bbox is [W, S, E, N]
        min_lon, min_lat, max_lon, max_lat = bbox

        # Build properties
        properties = {
            "source": self.name,
            "dataset_id": self.dataset_id,
            "title": metadata.get("title", ""),
            "description": (
                metadata.get("notes", "")[:200] if metadata.get("notes") else ""
            ),
        }

        # Add temporal extent to properties if available
        if temporal and isinstance(temporal, list):
            if len(temporal) >= 2:
                start_date, end_date = temporal[0], temporal[1]
                if start_date:
                    properties["start_time"] = start_date
                if end_date:
                    properties["end_time"] = end_date
            elif len(temporal) == 1:
                # Single date
                properties["start_time"] = temporal[0]
                properties["end_time"] = temporal[0]

        # Create a polygon feature representing the bounding box
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

        # Create the GeoJSON file
        geojson_file = os.path.join(
            target_folder, f"{self.name.lower()}_{self.dataset_id}.geojson"
        )

        with open(geojson_file, "w") as f:
            json.dump(geojson_data, f, indent=2)

        temporal_info = f" with temporal extent {temporal}" if temporal else ""
        self.log.info(
            f"Created GeoJSON metadata file for {self.name} dataset {self.dataset_id}{temporal_info}"
        )
