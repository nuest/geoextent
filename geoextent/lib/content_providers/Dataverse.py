#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Dataverse content provider for geoextent.

This module provides functionality to extract geospatial and temporal extent
information from datasets hosted on Dataverse installations.

Supported Dataverse installations:
- Harvard Dataverse (dataverse.harvard.edu)
- DataverseNL (dataverse.nl)
- Other Dataverse installations following the standard API

Supported identifier formats:
- DOIs: doi:10.7910/DVN/OMV93V, 10.7910/DVN/OMV93V
- DOI URLs: https://doi.org/10.7910/DVN/OMV93V
- Direct dataset URLs: https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/OMV93V
- Persistent ID parameter URLs: https://dataverse.harvard.edu/api/datasets/:persistentId?persistentId=doi:10.7910/DVN/OMV93V

API Documentation:
- Native API: https://guides.dataverse.org/en/latest/api/native-api.html
- Data Access API: https://guides.dataverse.org/en/latest/api/dataaccess.html
"""

import logging
import os
import re
import tempfile
import json
from urllib.parse import urlparse, parse_qs
from requests import HTTPError
from .providers import DoiProvider


class Dataverse(DoiProvider):
    """
    Content provider for Dataverse repositories.

    Handles dataset identification, metadata extraction, and file downloading
    from Dataverse installations using the standard Dataverse API.
    """

    def __init__(self):
        super().__init__()
        self.log = logging.getLogger("geoextent")

        # Known Dataverse installations
        self.known_hosts = [
            "dataverse.harvard.edu",
            "dataverse.nl",
            "demo.dataverse.nl",
            "dataverse.unc.edu",
            "data.library.virginia.edu",
            "dataverse.no",
            "recherche.data.gouv.fr",
        ]

        # URL patterns for validation
        self.url_patterns = {
            "dataset_page": re.compile(
                r"https?://([^/]+)/dataset\.xhtml\?persistentId=(.+)", re.IGNORECASE
            ),
            "api_persistent_id": re.compile(
                r"https?://([^/]+)/api/datasets/:persistentId\?persistentId=(.+)",
                re.IGNORECASE,
            ),
            "api_dataset_id": re.compile(
                r"https?://([^/]+)/api/datasets/(\d+)", re.IGNORECASE
            ),
        }

        # DOI patterns
        self.doi_patterns = {
            "full_doi": re.compile(
                r"^(doi:)?(10\..+)$", re.IGNORECASE
            ),  # Only match DOI format (10.xxxx/xxxx)
            "doi_url": re.compile(r"https?://(?:dx\.)?doi\.org/(.+)", re.IGNORECASE),
        }

        self.reference = None
        self.host = None
        self.persistent_id = None
        self.dataset_id = None
        self.name = "Dataverse"
        self.throttle = False
        self.dataset_metadata = None

    def validate_provider(self, reference):
        """
        Validate if the reference is a valid Dataverse identifier.

        Args:
            reference (str): The dataset reference to validate

        Returns:
            bool: True if valid Dataverse reference, False otherwise
        """
        self.reference = reference
        self.host = None
        self.persistent_id = None
        self.dataset_id = None

        # Check DOI patterns first before URL resolution to avoid circular logic

        # 1. Plain DOI (e.g., doi:10.7910/DVN/OMV93V or 10.7910/DVN/OMV93V)
        match = self.doi_patterns["full_doi"].match(reference)
        if match:
            doi = match.group(2)
            if self._is_dataverse_doi(doi):
                self.persistent_id = f"doi:{doi}"
                # We'll need to discover the host when we access the dataset
                return True

        # 2. DOI URL (e.g., https://doi.org/10.7910/DVN/OMV93V)
        match = self.doi_patterns["doi_url"].match(reference)
        if match:
            doi = match.group(1)
            if self._is_dataverse_doi(doi):
                self.persistent_id = f"doi:{doi}"
                # We'll need to discover the host when we access the dataset
                return True

        # Now try to resolve URLs if it's not a direct DOI
        try:
            url = self.get_url
        except:
            url = reference

        # Check different Dataverse-specific URL patterns

        # 1. Dataset page URL (e.g., https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/OMV93V)
        match = self.url_patterns["dataset_page"].match(url)
        if match:
            host, persistent_id = match.groups()
            if self._is_known_dataverse_host(host):
                self.host = host
                self.persistent_id = self._clean_persistent_id(persistent_id)
                return True

        # 2. API persistent ID URL
        match = self.url_patterns["api_persistent_id"].match(url)
        if match:
            host, persistent_id = match.groups()
            if self._is_known_dataverse_host(host):
                self.host = host
                self.persistent_id = self._clean_persistent_id(persistent_id)
                return True

        # 3. API dataset ID URL
        match = self.url_patterns["api_dataset_id"].match(url)
        if match:
            host, dataset_id = match.groups()
            if self._is_known_dataverse_host(host):
                self.host = host
                self.dataset_id = dataset_id
                return True

        return False

    def _is_known_dataverse_host(self, host):
        """Check if host is a known Dataverse installation."""
        return host.lower() in [h.lower() for h in self.known_hosts]

    def _is_dataverse_doi(self, doi):
        """
        Check if a DOI is likely from a Dataverse installation.

        This is a heuristic check based on common Dataverse DOI patterns.
        """
        # Common Dataverse DOI patterns
        dataverse_patterns = [
            r"10\.7910/DVN/",  # Harvard Dataverse
            r"10\.34894/",  # DataverseNL
            r"10\.18710/",  # DataverseNO
            r"10\.5064/",  # UNC Dataverse
        ]

        return any(
            re.search(pattern, doi, re.IGNORECASE) for pattern in dataverse_patterns
        )

    def _clean_persistent_id(self, persistent_id):
        """Clean and normalize persistent ID."""
        # Remove URL encoding
        import urllib.parse

        persistent_id = urllib.parse.unquote(persistent_id)

        # Ensure it starts with appropriate scheme
        if not persistent_id.startswith(("doi:", "hdl:", "urn:")):
            if persistent_id.startswith("10."):
                persistent_id = f"doi:{persistent_id}"

        return persistent_id

    def _discover_host_from_doi(self, doi):
        """
        Attempt to discover the Dataverse host by following DOI resolution.

        Args:
            doi (str): The DOI to resolve

        Returns:
            str: The discovered host, or None if not found
        """
        try:
            # Follow DOI resolution
            response = self._request(f"https://doi.org/{doi}", allow_redirects=True)
            final_url = response.url

            parsed = urlparse(final_url)
            host = parsed.netloc

            if self._is_known_dataverse_host(host):
                return host

        except Exception as e:
            self.log.debug(f"Failed to discover host from DOI {doi}: {e}")

        return None

    def _get_api_base_url(self):
        """Get the base API URL for the Dataverse installation."""
        if not self.host:
            # Try to discover host from DOI
            if self.persistent_id and self.persistent_id.startswith("doi:"):
                doi = self.persistent_id[4:]  # Remove 'doi:' prefix
                self.host = self._discover_host_from_doi(doi)

            if not self.host:
                # Default to Harvard Dataverse for unknown DOIs
                self.host = "dataverse.harvard.edu"
                self.log.warning(
                    f"Could not determine Dataverse host, defaulting to {self.host}"
                )

        return f"https://{self.host}/api"

    def _get_dataset_metadata(self):
        """
        Retrieve dataset metadata from Dataverse API.

        Returns:
            dict: Dataset metadata from Dataverse API
        """
        if self.dataset_metadata:
            return self.dataset_metadata

        api_base = self._get_api_base_url()

        try:
            if self.persistent_id:
                # Use persistent ID to access dataset
                url = f"{api_base}/datasets/:persistentId"
                params = {"persistentId": self.persistent_id}

                self.log.debug(
                    f"Fetching metadata from {url} with persistentId={self.persistent_id}"
                )
                response = self._request(url, params=params, throttle=self.throttle)

            elif self.dataset_id:
                # Use numeric dataset ID
                url = f"{api_base}/datasets/{self.dataset_id}"

                self.log.debug(f"Fetching metadata from {url}")
                response = self._request(url, throttle=self.throttle)

            else:
                raise ValueError("No dataset identifier available")

            response.raise_for_status()
            data = response.json()

            if data.get("status") != "OK":
                raise HTTPError(
                    f"API returned error: {data.get('message', 'Unknown error')}"
                )

            self.dataset_metadata = data["data"]
            return self.dataset_metadata

        except Exception as e:
            self.log.error(f"Failed to retrieve dataset metadata: {e}")
            raise HTTPError(f"Failed to retrieve Dataverse dataset metadata: {e}")

    def _get_file_list(self):
        """
        Get list of files in the dataset.

        Returns:
            list: List of file metadata dictionaries
        """
        metadata = self._get_dataset_metadata()

        try:
            latest_version = metadata["latestVersion"]
            return latest_version.get("files", [])
        except KeyError as e:
            self.log.error(f"Failed to extract file list from metadata: {e}")
            return []

    def _get_file_download_url(self, file_info):
        """
        Get download URL for a specific file.

        Args:
            file_info (dict): File metadata from Dataverse API

        Returns:
            str: Download URL for the file
        """
        api_base = self._get_api_base_url()

        # Try to get file ID from different possible locations
        file_id = None
        if "dataFile" in file_info and "id" in file_info["dataFile"]:
            file_id = file_info["dataFile"]["id"]
        elif "id" in file_info:
            file_id = file_info["id"]

        if file_id:
            return f"{api_base}/access/datafile/{file_id}"

        # Fallback: try persistent ID if available
        if "dataFile" in file_info and "persistentId" in file_info["dataFile"]:
            persistent_id = file_info["dataFile"]["persistentId"]
            return (
                f"{api_base}/access/datafile/:persistentId?persistentId={persistent_id}"
            )

        raise ValueError(f"Could not determine download URL for file: {file_info}")

    def download(self, folder, throttle=False, download_data=True, show_progress=True):
        """
        Download files from the Dataverse dataset.

        Args:
            folder (str): Target folder for downloads
            throttle (bool): Whether to throttle requests
            download_data (bool): Whether to download actual data files
        """
        from tqdm import tqdm

        self.throttle = throttle

        if not download_data:
            self.log.warning(
                "Dataverse provider requires downloading data files for geospatial extent extraction. "
                "Using download_data=False may result in limited or no spatial extent information. "
                "Consider using download_data=True to download actual data files for better geospatial extraction."
            )
            return

        self.log.debug(
            f"Downloading Dataverse dataset: {self.persistent_id or self.dataset_id}"
        )

        try:
            files = self._get_file_list()

            if not files:
                self.log.warning("No files found in dataset")
                return

            self.log.debug(f"Found {len(files)} files in dataset")

            # Log download summary before starting
            self.log.info(
                f"Starting download of {len(files)} files from Dataverse dataset {self.persistent_id or self.dataset_id}"
            )

            counter = 1
            # Process files with progress bar
            with tqdm(
                total=len(files),
                desc=f"Downloading Dataverse files from {self.persistent_id or self.dataset_id}",
                unit="file",
            ) as pbar:
                for file_info in files:
                    try:
                        download_url = self._get_file_download_url(file_info)

                        # Get filename
                        if (
                            "dataFile" in file_info
                            and "filename" in file_info["dataFile"]
                        ):
                            filename = file_info["dataFile"]["filename"]
                        elif "filename" in file_info:
                            filename = file_info["filename"]
                        elif "label" in file_info:
                            filename = file_info["label"]
                        else:
                            filename = f"file_{counter}"

                        pbar.set_postfix_str(f"Downloading {filename}")

                        filepath = os.path.join(folder, filename)

                        self.log.debug(
                            f"Downloading file {counter}/{len(files)}: {filename}"
                        )

                        # Download file
                        response = self._request(
                            download_url,
                            throttle=self.throttle,
                            stream=True,
                        )
                        response.raise_for_status()

                        # Write file to disk
                        with open(filepath, "wb") as dst:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    dst.write(chunk)

                        self.log.debug(
                            f"Downloaded: {filename} ({counter}/{len(files)})"
                        )
                        counter += 1
                        pbar.update(1)

                    except Exception as e:
                        self.log.warning(f"Failed to download file {filename}: {e}")
                        continue

        except Exception as e:
            self.log.error(f"Error downloading Dataverse dataset: {e}")
            raise Exception(f"Failed to download Dataverse dataset: {e}")

    def get_metadata_dict(self):
        """
        Extract metadata dictionary from Dataverse dataset.

        Returns:
            dict: Metadata dictionary with title, description, authors, etc.
        """
        try:
            metadata = self._get_dataset_metadata()
            latest_version = metadata["latestVersion"]
            citation_block = latest_version["metadataBlocks"]["citation"]
            fields = citation_block["fields"]

            # Extract key metadata fields
            result = {
                "identifier": metadata.get("persistentUrl", ""),
                "title": "",
                "description": "",
                "authors": [],
                "subjects": [],
                "publication_date": metadata.get("publicationDate", ""),
                "license": "",
                "dataset_type": metadata.get("datasetType", ""),
            }

            # Process fields
            for field in fields:
                type_name = field["typeName"]
                value = field["value"]

                if type_name == "title":
                    result["title"] = value
                elif type_name == "dsDescription" and isinstance(value, list) and value:
                    # Extract first description
                    desc_obj = value[0]
                    if isinstance(desc_obj, dict) and "dsDescriptionValue" in desc_obj:
                        result["description"] = desc_obj["dsDescriptionValue"]["value"]
                elif type_name == "author" and isinstance(value, list):
                    # Extract author names
                    for author_obj in value:
                        if isinstance(author_obj, dict) and "authorName" in author_obj:
                            result["authors"].append(author_obj["authorName"]["value"])
                elif type_name == "subject" and isinstance(value, list):
                    result["subjects"] = value

            # Add license information
            if "license" in latest_version:
                license_info = latest_version["license"]
                result["license"] = license_info.get("name", "")

            return result

        except Exception as e:
            self.log.error(f"Failed to extract metadata: {e}")
            return {}

    def __str__(self):
        """String representation of the Dataverse provider."""
        return f"Dataverse(host={self.host}, persistent_id={self.persistent_id}, dataset_id={self.dataset_id})"

    def __repr__(self):
        """Detailed representation of the Dataverse provider."""
        return self.__str__()
