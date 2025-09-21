import logging
import re
import tempfile
from datetime import datetime
from requests import HTTPError
from .providers import DoiProvider
from ..extent import fromDirectory


class Pangaea(DoiProvider):
    def __init__(self):
        super().__init__()
        self.log = logging.getLogger("geoextent")
        self.host = {
            "hostname": [
                "https://doi.pangaea.de/",
                "http://doi.pangaea.de/",
                "https://pangaea.de/",
                "http://pangaea.de/",
            ],
            "api": "https://doi.pangaea.de/",
        }
        self.reference = None
        self.dataset_id = None
        self.name = "Pangaea"
        self.throttle = False
        self.pangaea_doi_pattern = re.compile(r"10\.1594/PANGAEA\.(\d+)")

    def validate_provider(self, reference):
        """Validate if the reference is a Pangaea DOI or URL"""
        self.reference = reference

        # Check for Pangaea DOI pattern
        doi_match = self.pangaea_doi_pattern.search(reference)
        if doi_match:
            self.dataset_id = doi_match.group(1)
            return True

        # Check for Pangaea URL patterns
        url = self.get_url
        if any([url.startswith(p) for p in self.host["hostname"]]):
            # Extract dataset ID from URL
            url_parts = url.rstrip("/").split("/")
            if len(url_parts) > 0:
                potential_id = url_parts[-1]
                if potential_id.isdigit():
                    self.dataset_id = potential_id
                    return True

        return False

    def _get_metadata(self):
        """Get metadata from Pangaea using pangaeapy"""
        try:
            from pangaeapy.pandataset import PanDataSet

            if self.dataset_id:
                self.log.debug(f"Fetching Pangaea dataset {self.dataset_id}")

                # Create dataset using the numeric ID
                dataset = PanDataSet(int(self.dataset_id))

                # Extract metadata
                metadata = {
                    "title": getattr(dataset, "title", None),
                    "authors": getattr(dataset, "authors", None),
                    "year": getattr(dataset, "year", None),
                    "coverage": self._extract_coverage(dataset),
                    "temporal_coverage": self._extract_temporal_coverage(dataset),
                    "parameters": self._extract_parameters(dataset),
                }

                return metadata

        except ImportError:
            raise Exception("pangaeapy library is required for Pangaea support")
        except Exception as e:
            self.log.error(f"Error fetching Pangaea metadata: {e}")
            raise Exception(f"Failed to fetch Pangaea dataset {self.dataset_id}: {e}")

    def _extract_coverage(self, dataset):
        """Extract geographic coverage from Pangaea dataset"""
        coverage = {}

        try:
            # Check for geographic information in dataset
            if hasattr(dataset, "data") and dataset.data is not None:
                data = dataset.data

                # Look for latitude/longitude columns
                lat_cols = [col for col in data.columns if "lat" in col.lower()]
                lon_cols = [col for col in data.columns if "lon" in col.lower()]

                if lat_cols and lon_cols:
                    lat_col = lat_cols[0]
                    lon_col = lon_cols[0]

                    lat_values = data[lat_col].dropna()
                    lon_values = data[lon_col].dropna()

                    if not lat_values.empty and not lon_values.empty:
                        coverage = {
                            "min_lat": float(lat_values.min()),
                            "max_lat": float(lat_values.max()),
                            "min_lon": float(lon_values.min()),
                            "max_lon": float(lon_values.max()),
                        }

            # Alternative: check for geographic metadata in dataset attributes
            if not coverage and hasattr(dataset, "params"):
                params = dataset.params
                for param in params:
                    if "latitude" in param.get("name", "").lower():
                        # Extract coordinate information if available
                        pass
                    elif "longitude" in param.get("name", "").lower():
                        pass

        except Exception as e:
            self.log.warning(f"Could not extract geographic coverage: {e}")

        return coverage

    def _extract_temporal_coverage(self, dataset):
        """Extract temporal coverage from Pangaea dataset"""
        temporal_coverage = {}

        try:
            if hasattr(dataset, "data") and dataset.data is not None:
                data = dataset.data

                # Look for date/time columns
                time_cols = [
                    col for col in data.columns
                    if any(term in col.lower() for term in ["date", "time", "datetime"])
                ]

                if time_cols:
                    time_col = time_cols[0]
                    time_values = data[time_col].dropna()

                    if not time_values.empty:
                        # Try to parse dates
                        try:
                            import pandas as pd
                            parsed_times = pd.to_datetime(time_values, errors="coerce")
                            valid_times = parsed_times.dropna()

                            if not valid_times.empty:
                                temporal_coverage = {
                                    "start_time": valid_times.min().strftime("%Y-%m-%d"),
                                    "end_time": valid_times.max().strftime("%Y-%m-%d"),
                                }
                        except Exception as parse_error:
                            self.log.warning(f"Could not parse temporal data: {parse_error}")

        except Exception as e:
            self.log.warning(f"Could not extract temporal coverage: {e}")

        return temporal_coverage

    def _extract_parameters(self, dataset):
        """Extract parameter information from Pangaea dataset"""
        parameters = []

        try:
            if hasattr(dataset, "params") and dataset.params:
                for param in dataset.params:
                    param_info = {
                        "name": param.get("name", ""),
                        "shortName": param.get("shortName", ""),
                        "unit": param.get("unit", ""),
                    }
                    parameters.append(param_info)
        except Exception as e:
            self.log.warning(f"Could not extract parameters: {e}")

        return parameters

    def download(self, target_folder, throttle=False):
        """
        Extract geospatial metadata from Pangaea dataset without downloading files
        Since Pangaea datasets are typically tabular data with metadata,
        we extract coverage information directly from the metadata
        """
        self.throttle = throttle

        try:
            metadata = self._get_metadata()

            # Create a temporary file with the extracted metadata for processing
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
                import json

                # Convert metadata to a format that can be processed by geoextent
                processed_metadata = self._process_metadata_for_geoextent(metadata)
                json.dump(processed_metadata, temp_file, indent=2)
                temp_file_path = temp_file.name

            self.log.info(f"Pangaea metadata extracted for dataset {self.dataset_id}")

        except Exception as e:
            self.log.error(f"Error processing Pangaea dataset: {e}")
            raise

    def _process_metadata_for_geoextent(self, metadata):
        """Process Pangaea metadata into geoextent-compatible format"""
        processed = {
            "source": "Pangaea",
            "dataset_id": self.dataset_id,
            "title": metadata.get("title", ""),
            "year": metadata.get("year", ""),
        }

        # Add geographic coverage if available
        coverage = metadata.get("coverage", {})
        if coverage:
            processed["geographic_coverage"] = {
                "bbox": [
                    coverage.get("min_lon"),
                    coverage.get("min_lat"),
                    coverage.get("max_lon"),
                    coverage.get("max_lat"),
                ],
                "crs": "4326"
            }

        # Add temporal coverage if available
        temporal = metadata.get("temporal_coverage", {})
        if temporal:
            processed["temporal_coverage"] = {
                "start": temporal.get("start_time"),
                "end": temporal.get("end_time"),
            }

        # Add parameters
        parameters = metadata.get("parameters", [])
        if parameters:
            processed["parameters"] = parameters

        return processed