import logging
import re
import tempfile
from datetime import datetime
from requests import HTTPError
from .providers import DoiProvider
from .. import helpfunctions as hf


class Pangaea(DoiProvider):
    @property
    def supports_metadata_extraction(self):
        return True

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
        from pangaeapy.pandataset import PanDataSet

        try:
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

        except Exception as e:
            self.log.error(f"Error fetching Pangaea metadata: {e}")
            raise Exception(f"Failed to fetch Pangaea dataset {self.dataset_id}: {e}")

    def _get_web_metadata(self):
        """Get metadata by extracting Schema.org structured data from Pangaea web page"""
        import requests

        if not self.dataset_id:
            raise Exception("No dataset ID available for web metadata extraction")

        url = f"https://doi.pangaea.de/10.1594/PANGAEA.{self.dataset_id}"
        self.log.debug(f"Fetching web metadata from {url}")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            html_content = response.text

            # Extract Schema.org metadata (guaranteed to be present per Pangaea documentation)
            schema_metadata = self._extract_schema_org_metadata(html_content)
            if not schema_metadata:
                raise Exception("No Schema.org metadata found in Pangaea page")

            return schema_metadata

        except requests.RequestException as e:
            raise Exception(f"Failed to fetch web page: {e}")
        except Exception as e:
            raise Exception(f"Failed to parse web metadata: {e}")

    def _extract_schema_org_metadata(self, html_content):
        """Extract metadata from Schema.org JSON-LD structured data"""
        import json
        import re
        from datetime import datetime

        try:
            # Find JSON-LD script tag with Schema.org data
            json_ld_pattern = (
                r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
            )
            matches = re.findall(
                json_ld_pattern, html_content, re.DOTALL | re.IGNORECASE
            )

            for match in matches:
                try:
                    json_data = json.loads(match.strip())

                    # Check if this is a Dataset type
                    if json_data.get("@type") == "Dataset":
                        metadata = {
                            "title": json_data.get("name"),
                            "year": None,
                            "coverage": {},
                            "temporal_coverage": {},
                            "parameters": [],
                        }

                        # Extract year from datePublished
                        date_published = json_data.get("datePublished")
                        if date_published:
                            try:
                                year = datetime.fromisoformat(
                                    date_published.replace("Z", "+00:00")
                                ).year
                                metadata["year"] = year
                            except:
                                # Try simple year extraction
                                year_match = re.search(r"(\d{4})", date_published)
                                if year_match:
                                    metadata["year"] = int(year_match.group(1))

                        # Extract spatial coverage
                        spatial_coverage = json_data.get("spatialCoverage")
                        if spatial_coverage:
                            geo = spatial_coverage.get("geo", {})
                            if (
                                isinstance(geo, dict)
                                and geo.get("@type") == "GeoCoordinates"
                            ):
                                lat = geo.get("latitude")
                                lon = geo.get("longitude")
                                if lat is not None and lon is not None:
                                    # For point data, use the same coordinates for bounding box
                                    metadata["coverage"] = {
                                        "min_lat": float(lat),
                                        "max_lat": float(lat),
                                        "min_lon": float(lon),
                                        "max_lon": float(lon),
                                    }
                            elif (
                                isinstance(geo, dict) and geo.get("@type") == "GeoShape"
                            ):
                                # Handle bounding box data from GeoShape
                                box = geo.get("box")
                                if box:
                                    # Parse box coordinates: "south west north east"
                                    try:
                                        coords = box.split()
                                        if len(coords) == 4:
                                            south, west, north, east = map(
                                                float, coords
                                            )
                                            metadata["coverage"] = {
                                                "min_lat": south,
                                                "max_lat": north,
                                                "min_lon": west,
                                                "max_lon": east,
                                            }
                                    except (ValueError, IndexError) as e:
                                        self.log.warning(
                                            f"Could not parse GeoShape box: {e}"
                                        )

                                polygon = geo.get("polygon")
                                if polygon:
                                    # Parse polygon coordinates if available in future
                                    pass

                        # Extract distribution/download URLs
                        distribution = json_data.get("distribution")
                        if distribution:
                            download_urls = []
                            if isinstance(distribution, list):
                                for dist in distribution:
                                    if isinstance(dist, dict):
                                        content_url = dist.get("contentUrl")
                                        if content_url:
                                            download_urls.append(content_url)
                            elif isinstance(distribution, dict):
                                content_url = distribution.get("contentUrl")
                                if content_url:
                                    download_urls.append(content_url)

                            if download_urls:
                                metadata["download_urls"] = download_urls

                        # Extract temporal coverage
                        temporal_coverage = json_data.get("temporalCoverage")
                        if temporal_coverage:
                            if "/" in temporal_coverage:
                                # ISO 8601 interval format: start/end
                                start_str, end_str = temporal_coverage.split("/", 1)
                                try:
                                    start_date = datetime.fromisoformat(
                                        start_str.replace("Z", "+00:00")
                                    )
                                    end_date = datetime.fromisoformat(
                                        end_str.replace("Z", "+00:00")
                                    )
                                    metadata["temporal_coverage"] = {
                                        "start_time": start_date.strftime("%Y-%m-%d"),
                                        "end_time": end_date.strftime("%Y-%m-%d"),
                                    }
                                except Exception as e:
                                    self.log.warning(
                                        f"Could not parse temporal coverage: {e}"
                                    )
                            else:
                                # Single date
                                try:
                                    date = datetime.fromisoformat(
                                        temporal_coverage.replace("Z", "+00:00")
                                    )
                                    date_str = date.strftime("%Y-%m-%d")
                                    metadata["temporal_coverage"] = {
                                        "start_time": date_str,
                                        "end_time": date_str,
                                    }
                                except Exception as e:
                                    self.log.warning(
                                        f"Could not parse single temporal coverage: {e}"
                                    )

                        self.log.debug("Successfully extracted Schema.org metadata")
                        return metadata

                except json.JSONDecodeError:
                    continue

        except Exception as e:
            self.log.warning(f"Schema.org metadata extraction failed: {e}")

        return None

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
                    col
                    for col in data.columns
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
                                    "start_time": valid_times.min().strftime(
                                        "%Y-%m-%d"
                                    ),
                                    "end_time": valid_times.max().strftime("%Y-%m-%d"),
                                }
                        except Exception as parse_error:
                            self.log.warning(
                                f"Could not parse temporal data: {parse_error}"
                            )

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

    def download(
        self,
        target_folder,
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
        Extract geospatial metadata from Pangaea dataset.

        Parameters:
        - target_folder: Directory to store files
        - throttle: Rate limiting for API calls
        - download_data: If True, downloads actual data files for local GDAL extraction.
                        If False, uses metadata-based extraction (default behavior).
        """
        self.throttle = throttle

        # Warning for download skip nogeo not being supported
        if download_skip_nogeo:
            self.log.warning(
                "PANGAEA provider does not support selective file filtering. "
                "The --download-skip-nogeo option will be ignored. Files will be downloaded based on dataset metadata."
            )

        try:
            if download_data:
                self._download_data_files(
                    target_folder,
                    max_size_bytes,
                    max_download_method,
                    max_download_method_seed,
                )
            else:
                self._download_metadata_only(target_folder)

            self.log.info(
                f"Pangaea {'data' if download_data else 'metadata'} extracted for dataset {self.dataset_id}"
            )

        except Exception as e:
            self.log.error(f"Error processing Pangaea dataset: {e}")
            raise

    def _download_metadata_only(self, target_folder):
        """Extract metadata without downloading actual data files"""
        from tqdm import tqdm

        # Log download summary before starting
        self.log.info(
            f"Starting metadata extraction from Pangaea dataset {self.dataset_id}"
        )

        with tqdm(
            desc=f"Extracting Pangaea metadata for {self.dataset_id}", unit="step"
        ) as pbar:
            # Try web scraping first as fallback when pangaeapy fails or for no-download mode
            try:
                pbar.set_postfix_str("Fetching web metadata")
                metadata = self._get_web_metadata()
                pbar.update(1)
            except Exception as web_error:
                self.log.warning(
                    f"Web metadata extraction failed: {web_error}, trying pangaeapy"
                )
                try:
                    pbar.set_postfix_str("Fetching API metadata")
                    metadata = self._get_metadata()
                    pbar.update(1)
                except Exception as pangaeapy_error:
                    self.log.error(
                        f"Both web and pangaeapy metadata extraction failed: {pangaeapy_error}"
                    )
                    raise Exception(
                        f"Failed to extract metadata: web error: {web_error}, pangaeapy error: {pangaeapy_error}"
                    )

            # Create a GeoJSON file with the extracted spatial metadata for processing
            import json
            import os

            pbar.set_postfix_str("Processing metadata")
            processed_metadata = self._process_metadata_for_geoextent(metadata)
            pbar.update(1)

            # Create GeoJSON if geographic coverage is available
            if "geographic_coverage" in processed_metadata:
                geojson_file = os.path.join(
                    target_folder, f"pangaea_{self.dataset_id}.geojson"
                )
                pbar.set_postfix_str("Creating GeoJSON file")
                geojson_data = self._create_geojson_from_metadata(processed_metadata)

                with open(geojson_file, "w") as f:
                    json.dump(geojson_data, f, indent=2)
                self.log.info(
                    f"Created GeoJSON metadata file for Pangaea dataset {self.dataset_id}"
                )
            else:
                # Fallback: create JSON metadata file for debugging
                metadata_file = os.path.join(
                    target_folder, f"pangaea_{self.dataset_id}_metadata.json"
                )
                pbar.set_postfix_str("Creating metadata file")
                with open(metadata_file, "w") as f:
                    json.dump(processed_metadata, f, indent=2)
                self.log.info(
                    f"Created metadata file for Pangaea dataset {self.dataset_id}"
                )
            pbar.update(1)

    def _download_data_files(
        self,
        target_folder,
        max_size_bytes=None,
        max_download_method="ordered",
        max_download_method_seed=None,
    ):
        """Download actual data files from Pangaea for local GDAL-based extraction"""
        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        from pangaeapy.pandataset import PanDataSet
        from tqdm import tqdm
        import os

        try:
            if self.dataset_id:
                self.log.debug(
                    f"Downloading Pangaea data files for dataset {self.dataset_id}"
                )

                # Log download summary before starting
                self.log.info(
                    f"Starting data file download from Pangaea dataset {self.dataset_id}"
                )

                # Show progress while fetching dataset metadata
                # Estimate total steps: API connection (1) + data processing/fallback (1)
                with tqdm(
                    desc=f"Fetching Pangaea dataset {self.dataset_id}",
                    unit="step",
                    total=2,
                ) as pbar:
                    pbar.set_postfix_str("Connecting to Pangaea API")
                    # Create dataset using the numeric ID
                    dataset = PanDataSet(int(self.dataset_id))
                    pbar.update(1)

                    # Check if dataset has downloadable data
                    has_data = hasattr(dataset, "data") and dataset.data is not None
                    if has_data:
                        data_size = (
                            len(dataset.data) if hasattr(dataset.data, "__len__") else 1
                        )

                        # If we have data but it's empty (0 records), treat as no data
                        if data_size == 0:
                            has_data = False

                    if has_data and data_size > 0:
                        pbar.set_postfix_str("Processing data")

                        # Save data as CSV for GDAL processing
                        csv_file = os.path.join(
                            target_folder, f"pangaea_{self.dataset_id}.csv"
                        )
                        pbar.set_postfix_str(f"Saving CSV ({data_size} records)")
                        dataset.data.to_csv(csv_file, index=False)
                        self.log.debug(f"Saved dataset data to {csv_file}")
                        pbar.update(1)

                        self.log.info(
                            f"Downloaded Pangaea dataset {self.dataset_id} with {data_size} records"
                        )

                    else:
                        self.log.warning(
                            f"No tabular data available for download from dataset {self.dataset_id}"
                        )
                        # Fallback to actual file download using distribution URLs
                        pbar.set_postfix_str("Trying direct file download fallback")
                        fallback_success = self._download_files_fallback(
                            target_folder,
                            pbar,
                            max_size_bytes,
                            max_download_method,
                            max_download_method_seed,
                        )
                        if not fallback_success:
                            pbar.set_postfix_str("Falling back to metadata extraction")
                            self._download_metadata_only(target_folder)
                        pbar.update(1)

        except Exception as e:
            self.log.error(f"Error downloading Pangaea data files: {e}")
            # Try fallback to actual file download before giving up
            try:
                self.log.info("Attempting direct file download as fallback")
                if self._download_files_fallback(
                    target_folder,
                    None,
                    max_size_bytes,
                    max_download_method,
                    max_download_method_seed,
                ):
                    return
            except Exception as fallback_error:
                self.log.warning(
                    f"File download fallback also failed: {fallback_error}"
                )

            # Final fallback to metadata-only extraction
            self._download_metadata_only(target_folder)

    def _download_files_fallback(
        self,
        target_folder,
        pbar=None,
        max_size_bytes=None,
        max_download_method="ordered",
        max_download_method_seed=None,
    ):
        """
        Fallback method to download actual data files using distribution URLs from schema.org metadata
        when pangaeapy fails (e.g., for non-tabular data like GeoJSON, GeoTIFF archives)

        Returns:
            bool: True if download was successful, False otherwise
        """
        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        try:
            # Get schema.org metadata to find distribution URLs
            metadata = self._get_web_metadata()
            download_urls = metadata.get("download_urls", [])

            if not download_urls:
                self.log.warning("No download URLs found in schema.org metadata")
                return False

            self.log.info(
                f"Found {len(download_urls)} download URLs in schema.org metadata"
            )

            import requests
            import os
            import zipfile

            # First, collect file information including sizes
            files_info = []
            for i, url in enumerate(download_urls):
                try:
                    # Get file info without downloading
                    head_response = requests.head(url, timeout=30)
                    head_response.raise_for_status()

                    filename = self._get_filename_from_response(head_response, url)
                    file_size = None

                    # Try to get Content-Length header
                    content_length = head_response.headers.get("Content-Length")
                    if content_length and content_length.isdigit():
                        file_size = int(content_length)

                    files_info.append(
                        {"url": url, "name": filename, "size": file_size, "index": i}
                    )

                    self.log.debug(
                        f"File {filename}: {file_size} bytes"
                        if file_size
                        else f"File {filename}: size unknown"
                    )

                except Exception as e:
                    self.log.warning(f"Could not get file info from {url}: {e}")
                    # Add file without size info
                    files_info.append(
                        {
                            "url": url,
                            "name": f"unknown_file_{i}",
                            "size": None,
                            "index": i,
                        }
                    )

            # Apply size filtering if specified
            if max_size_bytes is not None:
                from .. import helpfunctions as hf

                selected_files, total_size, skipped_files = hf.filter_files_by_size(
                    files_info,
                    max_size_bytes,
                    max_download_method,
                    max_download_method_seed,
                )

                if not selected_files:
                    self.log.warning("No files can be downloaded within the size limit")
                    return False

                self.log.info(
                    f"Size limit applied: downloading {len(selected_files)} of {len(files_info)} files"
                )
                files_to_download = selected_files
            else:
                files_to_download = files_info

            success = False
            for file_info in files_to_download:
                try:
                    url = file_info["url"]
                    filename = file_info["name"]
                    file_index = file_info["index"]

                    if pbar:
                        try:
                            pbar.set_postfix_str(
                                f"Downloading file {file_index+1}/{len(download_urls)}"
                            )
                        except Exception as pbar_error:
                            # Ignore progress bar errors to avoid breaking the download
                            self.log.debug(f"Progress bar update error: {pbar_error}")

                    self.log.debug(f"Downloading from URL: {url}")
                    response = requests.get(url, stream=True, timeout=300)
                    response.raise_for_status()

                    filepath = os.path.join(target_folder, filename)

                    # Download the file with size monitoring
                    downloaded_size = 0
                    size_exceeded = False

                    with open(filepath, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                # If we have a size limit and this file size is unknown, monitor download size
                                if (
                                    max_size_bytes is not None
                                    and file_info.get("size") is None
                                ):
                                    downloaded_size += len(chunk)
                                    if downloaded_size > max_size_bytes:
                                        self.log.warning(
                                            f"File {filename} exceeds size limit during download ({downloaded_size} > {max_size_bytes} bytes). Stopping download."
                                        )
                                        size_exceeded = True
                                        break

                                f.write(chunk)

                    # If size was exceeded, remove the partial file and skip this file
                    if size_exceeded:
                        if os.path.exists(filepath):
                            os.remove(filepath)
                        continue

                    file_size = os.path.getsize(filepath)
                    self.log.info(f"Downloaded {filename} ({file_size} bytes)")

                    # If it's a ZIP archive, extract it
                    if filepath.lower().endswith(".zip"):
                        try:
                            if pbar:
                                try:
                                    pbar.set_postfix_str(f"Extracting {filename}")
                                except Exception as pbar_error:
                                    # Ignore progress bar errors
                                    self.log.debug(
                                        f"Progress bar update error: {pbar_error}"
                                    )

                            with zipfile.ZipFile(filepath, "r") as zip_ref:
                                # Get list of files before extracting
                                extracted_files = zip_ref.namelist()
                                zip_ref.extractall(target_folder)

                            # Log extracted files
                            self.log.info(
                                f"Extracted {len(extracted_files)} files from {filename}"
                            )

                            # Optionally remove the zip file to save space
                            os.remove(filepath)

                        except zipfile.BadZipFile:
                            self.log.warning(
                                f"File {filename} appears to be corrupted or not a valid ZIP"
                            )
                        except Exception as extract_error:
                            self.log.warning(
                                f"Failed to extract {filename}: {extract_error}"
                            )

                    success = True

                except requests.RequestException as e:
                    self.log.warning(f"Failed to download from {url}: {e}")
                    continue
                except Exception as e:
                    self.log.warning(f"Error processing download from {url}: {e}")
                    continue

            return success

        except Exception as e:
            self.log.error(f"File download fallback failed: {e}")
            return False

    def _get_filename_from_response(self, response, url):
        """Extract filename from HTTP response or URL"""
        import os
        from urllib.parse import urlparse

        # Try to get filename from Content-Disposition header
        content_disposition = response.headers.get("content-disposition", "")
        if "filename=" in content_disposition:
            filename = content_disposition.split("filename=")[1].strip("\"'")
            return filename

        # Fallback to URL path
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if filename and filename != "/":
            return filename

        # Final fallback using dataset ID
        return f"pangaea_{self.dataset_id}_data"

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
                "crs": "4326",
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

    def _create_geojson_from_metadata(self, metadata):
        """Create a GeoJSON representation from Pangaea metadata for geoextent processing"""
        geojson_data = {"type": "FeatureCollection", "features": []}

        # Extract geographic coverage
        if "geographic_coverage" in metadata:
            bbox = metadata["geographic_coverage"]["bbox"]
            min_lon, min_lat, max_lon, max_lat = bbox

            # Create a polygon feature representing the bounding box
            feature = {
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
                "properties": {
                    "source": "Pangaea",
                    "dataset_id": metadata.get("dataset_id", ""),
                    "title": metadata.get("title", ""),
                    "year": metadata.get("year", ""),
                },
            }

            # Add temporal information if available
            if "temporal_coverage" in metadata:
                feature["properties"]["start_time"] = metadata["temporal_coverage"].get(
                    "start"
                )
                feature["properties"]["end_time"] = metadata["temporal_coverage"].get(
                    "end"
                )

            geojson_data["features"].append(feature)

        return geojson_data
