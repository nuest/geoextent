import re
import os
import logging
import json
from xml.etree import ElementTree as ET
from urllib.parse import urlencode
from .providers import DoiProvider
from .. import helpfunctions as hf

logger = logging.getLogger("geoextent")


class BGR(DoiProvider):
    """Content provider for BGR Geoportal (Federal Institute for Geosciences and Natural Resources)

    Supports BGR identifiers, URLs, and DOIs. Uses CSW (Catalog Service for the Web) API
    to extract metadata following GeoDCAT-AP and INSPIRE standards.

    **Identifier Types:**

    BGR uses two distinct UUID types:

    1. **Catalog Record UUID** (metadata record ID): Identifies the metadata record in the CSW catalog
       - Example: b73b55f1-14ec-4b7c-aa59-49b997ce7bbd
       - Used in CSW GetRecordById requests
       - Appears in the URL path (#/datasets/portal/{catalog_uuid})
       - This is the primary identifier for accessing metadata

    2. **Dataset UUID** (file identifier): Identifies the actual geospatial dataset
       - Example: 6f4e0e16-9218-4b5d-9f3f-ac6269293e37
       - Found in the gmd:fileIdentifier element of ISO 19115 metadata
       - Sometimes displayed on dataset landing pages
       - May be used to link datasets across systems

    This provider accepts either UUID type. If a dataset UUID is provided, it will search
    the CSW catalog to find the corresponding catalog record UUID.

    **Supported Identifier Formats:**
    - DOI: 10.25928/HK1000 or https://doi.org/10.25928/HK1000
    - Full portal URL: https://geoportal.bgr.de/mapapps/resources/apps/geoportal/index.html?lang=en#/datasets/portal/{catalog_uuid}
    - CSW GetRecordById URL: https://geoportal.bgr.de/smartfindersdi-csw/api?...&Id={catalog_uuid}
    - Resource URL: https://resource.bgr.de/{uuid}
    - Bare UUID: {uuid} (either catalog record UUID or dataset UUID)
    """

    def __init__(self):
        super().__init__()
        self.host = {
            "hostname": [
                "https://geoportal.bgr.de",
                "http://geoportal.bgr.de",
                "geoportal.bgr.de",
                "https://resource.bgr.de",
                "http://resource.bgr.de",
                "resource.bgr.de",
            ]
        }
        self.csw_base_url = "https://geoportal.bgr.de/smartfindersdi-csw/api"
        self.catalog_record_uuid = None  # UUID for the metadata record (CSW record ID)
        self.dataset_uuid = None  # UUID for the actual dataset (file identifier)
        self.name = "BGR"
        # Namespaces for parsing XML responses
        self.namespaces = {
            "csw": "http://www.opengis.net/cat/csw/2.0.2",
            "gmd": "http://www.isotc211.org/2005/gmd",
            "gco": "http://www.isotc211.org/2005/gco",
            "gml": "http://www.opengis.net/gml",
            "srv": "http://www.isotc211.org/2005/srv",
        }

    @property
    def dataset_id(self):
        """Backward compatibility property - returns catalog record UUID"""
        return self.catalog_record_uuid

    @dataset_id.setter
    def dataset_id(self, value):
        """Backward compatibility property setter"""
        self.catalog_record_uuid = value

    def validate_provider(self, reference):
        """Validate if the reference is a supported BGR Geoportal identifier

        Accepts BGR DOIs, catalog record UUIDs, dataset UUIDs, and various URL formats.
        BGR DOIs follow the pattern 10.25928/* and redirect to the portal URL.

        Args:
            reference (str): DOI, URL, catalog record UUID, or dataset UUID

        Returns:
            bool: True if valid BGR reference, False otherwise
        """
        self.reference = reference

        # UUID pattern for validation
        uuid_pattern = r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"

        # Check for BGR DOI pattern: 10.25928/*
        # Examples: 10.25928/HK1000, 10.25928/MEDKAM.1, 10.25928/b2.21_sfkq-r406
        doi_pattern = r"(?:https?://(?:dx\.)?doi\.org/)?10\.25928/[\w.\-_]+"
        doi_match = re.match(doi_pattern, reference, re.IGNORECASE)
        if doi_match:
            # Extract the DOI if it's a full URL
            if reference.startswith("http"):
                self.doi = reference.split("doi.org/")[-1]
            else:
                self.doi = reference

            logger.debug(f"Detected BGR DOI: {self.doi}")

            # Resolve DOI to get the portal URL with catalog UUID
            try:
                resolved_url = self._resolve_doi_to_url(self.doi)
                logger.debug(f"Resolved DOI to: {resolved_url}")

                # Extract catalog UUID from the resolved URL
                hash_match = re.search(
                    r"#/datasets/portal/(" + uuid_pattern + r")",
                    resolved_url,
                    re.IGNORECASE,
                )
                if hash_match:
                    self.catalog_record_uuid = hash_match.group(1)
                    logger.debug(
                        f"Extracted catalog UUID from DOI resolution: {self.catalog_record_uuid}"
                    )
                    return True
                else:
                    logger.warning(
                        f"Could not extract UUID from resolved DOI URL: {resolved_url}"
                    )
                    return False
            except Exception as e:
                logger.error(f"Failed to resolve BGR DOI {self.doi}: {e}")
                return False

        # Check for BGR hostname in URL
        if any(host in reference for host in self.host["hostname"]):
            # Pattern 1: Full portal URL with hash fragment
            # Example: https://geoportal.bgr.de/mapapps/resources/apps/geoportal/index.html?lang=en#/datasets/portal/{uuid}
            hash_match = re.search(
                r"#/datasets/portal/(" + uuid_pattern + r")", reference, re.IGNORECASE
            )
            if hash_match:
                self.catalog_record_uuid = hash_match.group(1)
                logger.debug(
                    f"Extracted catalog UUID from full portal URL: {self.catalog_record_uuid}"
                )
                return True

            # Pattern 2: CSW GetRecordById URL: ...?Id=DATASET_ID (note capital I)
            id_match = re.search(r"[?&]Id=([^&]+)", reference)
            if id_match:
                potential_id = id_match.group(1)
                if re.match(r"^" + uuid_pattern + r"$", potential_id, re.IGNORECASE):
                    self.catalog_record_uuid = potential_id
                    logger.debug(
                        f"Extracted catalog UUID from CSW URL: {self.catalog_record_uuid}"
                    )
                    return True

            # Pattern 3: geoportal.bgr.de/...?id=DATASET_ID (lowercase i)
            id_match = re.search(r"[?&]id=([^&]+)", reference)
            if id_match:
                potential_id = id_match.group(1)
                if re.match(r"^" + uuid_pattern + r"$", potential_id, re.IGNORECASE):
                    self.catalog_record_uuid = potential_id
                    logger.debug(
                        f"Extracted catalog UUID from URL parameter: {self.catalog_record_uuid}"
                    )
                    return True

            # Pattern 4: resource.bgr.de/DATASET_ID or similar path-based URLs
            # Extract last path component as potential dataset ID
            parts = reference.rstrip("/").split("/")
            if len(parts) > 0:
                potential_id = parts[-1]
                # Remove any query string or fragment
                potential_id = re.split(r"[?#]", potential_id)[0]
                # Check if it's a valid UUID
                if re.match(r"^" + uuid_pattern + r"$", potential_id, re.IGNORECASE):
                    self.catalog_record_uuid = potential_id
                    logger.debug(
                        f"Extracted UUID from URL path: {self.catalog_record_uuid}"
                    )
                    return True

        # If it's not a URL but could be a direct UUID
        # Try as catalog record UUID first, then as dataset UUID if that fails
        if re.match(r"^" + uuid_pattern + r"$", reference, re.IGNORECASE):
            self.catalog_record_uuid = reference
            logger.debug(
                f"Accepted bare UUID as catalog record UUID: {self.catalog_record_uuid}"
            )
            return True

        return False

    def _resolve_doi_to_url(self, doi):
        """Resolve a BGR DOI to its landing page URL

        BGR DOIs (10.25928/*) redirect to the BGR geoportal landing page.
        This method follows the redirect to get the final URL containing the catalog UUID.

        Args:
            doi (str): BGR DOI (e.g., "10.25928/HK1000")

        Returns:
            str: Resolved landing page URL

        Raises:
            Exception: If DOI resolution fails
        """
        # Construct the DOI URL if not already a full URL
        if not doi.startswith("http"):
            doi_url = f"https://doi.org/{doi}"
        else:
            doi_url = doi

        logger.debug(f"Resolving BGR DOI: {doi_url}")

        try:
            # Follow redirects to get the final landing page URL
            # Use HEAD request first to avoid downloading content
            response = self.session.head(doi_url, allow_redirects=True, timeout=30)

            if response.status_code in [200, 302, 303]:
                resolved_url = response.url
                logger.debug(f"DOI resolved to: {resolved_url}")
                return resolved_url
            else:
                raise Exception(
                    f"DOI resolution returned status {response.status_code}"
                )

        except Exception as e:
            logger.error(f"Error resolving BGR DOI {doi}: {e}")
            raise Exception(f"Failed to resolve BGR DOI {doi}: {e}")

    def _get_record_by_id(self, dataset_id):
        """Fetch a CSW record by ID

        Args:
            dataset_id (str): Dataset identifier

        Returns:
            ET.Element: XML element tree root of the CSW response
        """
        params = {
            "service": "CSW",
            "version": "2.0.2",
            "request": "GetRecordById",
            "id": dataset_id,
            "outputSchema": "http://www.isotc211.org/2005/gmd",
            "elementSetName": "full",
        }

        url = f"{self.csw_base_url}?{urlencode(params)}"
        logger.debug(f"Fetching BGR record from: {url}")

        try:
            response = self._request(url, throttle=False)
            response.raise_for_status()

            # Parse XML response
            root = ET.fromstring(response.content)
            return root

        except Exception as e:
            logger.error(f"Error fetching BGR record {dataset_id}: {e}")
            raise Exception(f"Failed to fetch BGR dataset {dataset_id}: {e}")

    def _search_records(self, query_text=None):
        """Search for records using CSW GetRecords

        Args:
            query_text (str, optional): Text to search for

        Returns:
            ET.Element: XML element tree root of the CSW response
        """
        # Build GetRecords request
        # For simplicity, we'll search with a basic constraint
        params = {
            "service": "CSW",
            "version": "2.0.2",
            "request": "GetRecords",
            "resultType": "results",
            "outputSchema": "http://www.isotc211.org/2005/gmd",
            "elementSetName": "full",
            "maxRecords": "10",
        }

        if query_text:
            params["constraintLanguage"] = "CQL_TEXT"
            params["constraint"] = f"AnyText LIKE '%{query_text}%'"

        url = f"{self.csw_base_url}?{urlencode(params)}"
        logger.debug(f"Searching BGR records: {url}")

        try:
            response = self._request(url, throttle=False)
            response.raise_for_status()

            root = ET.fromstring(response.content)
            return root

        except Exception as e:
            logger.error(f"Error searching BGR records: {e}")
            raise Exception(f"Failed to search BGR records: {e}")

    def _extract_metadata_from_iso(self, root):
        """Extract metadata from ISO 19115/19139 XML

        Args:
            root (ET.Element): XML element tree root

        Returns:
            dict: Extracted metadata including dataset UUID (file identifier)
        """
        metadata = {
            "title": None,
            "abstract": None,
            "bbox": None,
            "temporal_extent": None,
            "distribution_urls": [],
            "dataset_uuid": None,  # File identifier from ISO metadata
        }

        try:
            # Find MD_Metadata element
            md_metadata = root.find(".//gmd:MD_Metadata", self.namespaces)
            if md_metadata is None:
                logger.warning("No MD_Metadata found in response")
                return metadata

            # Extract file identifier (dataset UUID)
            file_id_elem = md_metadata.find(
                ".//gmd:fileIdentifier/gco:CharacterString", self.namespaces
            )
            if file_id_elem is not None and file_id_elem.text:
                self.dataset_uuid = file_id_elem.text
                metadata["dataset_uuid"] = file_id_elem.text
                logger.debug(
                    f"Extracted dataset UUID (file identifier): {self.dataset_uuid}"
                )

            # Extract title
            title_elem = md_metadata.find(
                ".//gmd:identificationInfo//gmd:citation//gmd:title/gco:CharacterString",
                self.namespaces,
            )
            if title_elem is not None and title_elem.text:
                metadata["title"] = title_elem.text

            # Extract abstract
            abstract_elem = md_metadata.find(
                ".//gmd:identificationInfo//gmd:abstract/gco:CharacterString",
                self.namespaces,
            )
            if abstract_elem is not None and abstract_elem.text:
                metadata["abstract"] = abstract_elem.text

            # Extract bounding box from EX_GeographicBoundingBox
            bbox_elem = md_metadata.find(
                ".//gmd:identificationInfo//gmd:extent//gmd:EX_GeographicBoundingBox",
                self.namespaces,
            )
            if bbox_elem is not None:
                west = bbox_elem.find(
                    ".//gmd:westBoundLongitude/gco:Decimal", self.namespaces
                )
                east = bbox_elem.find(
                    ".//gmd:eastBoundLongitude/gco:Decimal", self.namespaces
                )
                south = bbox_elem.find(
                    ".//gmd:southBoundLatitude/gco:Decimal", self.namespaces
                )
                north = bbox_elem.find(
                    ".//gmd:northBoundLatitude/gco:Decimal", self.namespaces
                )

                if all(elem is not None for elem in [west, east, south, north]):
                    try:
                        metadata["bbox"] = [
                            float(west.text),  # minx (west longitude)
                            float(south.text),  # miny (south latitude)
                            float(east.text),  # maxx (east longitude)
                            float(north.text),  # maxy (north latitude)
                        ]
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not parse bounding box coordinates: {e}")

            # Extract temporal extent
            temporal_elem = md_metadata.find(
                ".//gmd:identificationInfo//gmd:extent//gmd:EX_TemporalExtent",
                self.namespaces,
            )
            if temporal_elem is not None:
                # Try to find time period
                begin_elem = temporal_elem.find(".//gml:beginPosition", self.namespaces)
                end_elem = temporal_elem.find(".//gml:endPosition", self.namespaces)

                if begin_elem is not None and end_elem is not None:
                    metadata["temporal_extent"] = {
                        "start": begin_elem.text,
                        "end": end_elem.text,
                    }

            # Extract distribution/download URLs
            distribution_elems = md_metadata.findall(
                ".//gmd:distributionInfo//gmd:MD_DigitalTransferOptions//gmd:onLine",
                self.namespaces,
            )
            for dist_elem in distribution_elems:
                url_elem = dist_elem.find(".//gmd:URL", self.namespaces)
                if url_elem is not None and url_elem.text:
                    metadata["distribution_urls"].append(url_elem.text)

        except Exception as e:
            logger.warning(f"Error parsing ISO metadata: {e}")

        return metadata

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
        """Download data from BGR Geoportal

        Args:
            folder (str): Target directory for downloads
            throttle (bool): Whether to throttle requests (default: False)
            download_data (bool): Whether to download actual data files (default: True)
            show_progress (bool): Whether to show progress bars (default: True)
            max_size_bytes (int): Maximum total download size in bytes
            max_download_method (str): Method for selecting files when size limit applies
            max_download_method_seed (int): Random seed for sampling methods
            download_skip_nogeo (bool): Skip non-geospatial files
            download_skip_nogeo_exts (set): Additional geospatial file extensions
            max_download_workers (int): Maximum number of parallel download workers

        Returns:
            str: Path to downloaded data directory
        """
        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        logger.info(f"Downloading from BGR Geoportal: {self.reference}")

        # Warning for download skip nogeo not being supported
        if download_skip_nogeo:
            logger.warning(
                "BGR provider does not fully support selective file filtering. "
                "The --download-skip-nogeo option will be applied when possible."
            )

        if not self.dataset_id:
            raise Exception("No dataset ID available for download")

        # Fetch metadata from CSW
        try:
            xml_root = self._get_record_by_id(self.dataset_id)
            metadata = self._extract_metadata_from_iso(xml_root)

            logger.debug(f"Extracted metadata: {metadata}")

            # Create target directory
            folder_name = f"bgr_{self.dataset_id}"
            download_dir = os.path.join(folder, folder_name)
            os.makedirs(download_dir, exist_ok=True)

            if not download_data:
                # Create GeoJSON from metadata only
                logger.info("Creating metadata-only GeoJSON file")
                self._create_metadata_geojson(metadata, download_dir)
                return download_dir

            # Download data files if available
            if metadata.get("distribution_urls"):
                logger.info(
                    f"Found {len(metadata['distribution_urls'])} distribution URLs"
                )
                self._download_files(
                    metadata["distribution_urls"],
                    download_dir,
                    show_progress,
                    max_size_bytes,
                    max_download_method,
                    max_download_method_seed,
                    download_skip_nogeo,
                    download_skip_nogeo_exts,
                    max_download_workers,
                )
            else:
                logger.warning("No distribution URLs found in metadata")
                # Still create metadata GeoJSON
                self._create_metadata_geojson(metadata, download_dir)

            return download_dir

        except Exception as e:
            logger.error(f"Error downloading BGR dataset: {e}")
            raise

    def _create_metadata_geojson(self, metadata, target_dir):
        """Create a GeoJSON file from metadata

        Args:
            metadata (dict): Extracted metadata
            target_dir (str): Target directory
        """
        if not metadata.get("bbox"):
            logger.warning("No bounding box in metadata, cannot create GeoJSON")
            # Create a basic JSON metadata file instead
            metadata_file = os.path.join(
                target_dir, f"bgr_{self.dataset_id}_metadata.json"
            )
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            logger.info(f"Created metadata JSON file: {metadata_file}")
            return

        minx, miny, maxx, maxy = metadata["bbox"]

        # Create GeoJSON feature
        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [minx, miny],
                                [maxx, miny],
                                [maxx, maxy],
                                [minx, maxy],
                                [minx, miny],
                            ]
                        ],
                    },
                    "properties": {
                        "source": "BGR",
                        "dataset_id": self.dataset_id,
                        "title": metadata.get("title", ""),
                        "abstract": metadata.get("abstract", ""),
                    },
                }
            ],
        }

        # Add temporal extent if available
        if metadata.get("temporal_extent"):
            geojson_data["features"][0]["properties"]["temporal_extent"] = metadata[
                "temporal_extent"
            ]

        # Write GeoJSON file
        geojson_file = os.path.join(target_dir, f"bgr_{self.dataset_id}.geojson")
        with open(geojson_file, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Created GeoJSON metadata file: {geojson_file}")

    def _download_files(
        self,
        distribution_urls,
        target_dir,
        show_progress=True,
        max_size_bytes=None,
        max_download_method="ordered",
        max_download_method_seed=None,
        download_skip_nogeo=False,
        download_skip_nogeo_exts=None,
        max_download_workers=4,
    ):
        """Download files from distribution URLs

        Args:
            distribution_urls (list): List of URLs to download
            target_dir (str): Target directory
            show_progress (bool): Whether to show progress
            max_size_bytes (int): Maximum total download size
            max_download_method (str): Method for selecting files
            max_download_method_seed (int): Random seed
            download_skip_nogeo (bool): Skip non-geospatial files
            download_skip_nogeo_exts (set): Additional geospatial extensions
            max_download_workers (int): Maximum parallel workers
        """
        # Prepare file list for batch download
        file_list = []

        for url in distribution_urls:
            # Try to get file size via HEAD request
            try:
                head_response = self.session.head(url, timeout=30)
                file_size = int(head_response.headers.get("content-length", 0))
            except:
                file_size = 0  # Unknown size

            # Extract filename from URL
            filename = os.path.basename(url.rstrip("/"))
            if not filename or filename == url:
                filename = f"bgr_file_{len(file_list)}"

            file_info = {"url": url, "name": filename, "size": file_size}

            file_list.append(file_info)

        # Filter geospatial files if requested
        if download_skip_nogeo:
            filtered_files = self._filter_geospatial_files(
                file_list,
                skip_non_geospatial=True,
                additional_extensions=download_skip_nogeo_exts,
            )
        else:
            filtered_files = file_list

        # Apply size filtering
        if max_size_bytes is not None:
            selected_files, total_size, skipped_files = hf.filter_files_by_size(
                filtered_files,
                max_size_bytes,
                max_download_method,
                max_download_method_seed,
            )

            if not selected_files:
                logger.warning("No files can be downloaded within the size limit")
                return

            logger.info(
                f"Size limit applied: downloading {len(selected_files)} of {len(filtered_files)} files "
                f"({total_size:,} bytes total)"
            )
            filtered_files = selected_files

        # Use batch download with parallel/sequential selection
        if filtered_files:
            self._download_files_batch(
                filtered_files,
                target_dir,
                show_progress=show_progress,
                max_workers=max_download_workers,
            )
