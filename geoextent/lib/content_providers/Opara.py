import logging
import os
import re
from requests import HTTPError
from .providers import DoiProvider
from .. import helpfunctions as hf


class Opara(DoiProvider):
    doi_prefixes = ("10.25532/OPARA",)

    @classmethod
    def provider_info(cls):
        return {
            "name": "Opara",
            "description": "OPARA is the Open Access Repository and Archive for research data of Saxon universities, jointly operated by TU Dresden and TU Bergakademie Freiberg. It offers free archiving for at least ten years and open access publishing of research data with DOI assignment, running on DSpace 7.x platform.",
            "website": "https://opara.zih.tu-dresden.de/",
            "supported_identifiers": [
                "https://opara.zih.tu-dresden.de/items/{uuid}",
                "https://opara.zih.tu-dresden.de/handle/{handle}",
                "https://doi.org/10.25532/OPARA-{id}",
                "10.25532/OPARA-{id}",
                "{uuid}",
            ],
            "doi_prefix": "10.25532/OPARA",
            "examples": [
                "https://opara.zih.tu-dresden.de/items/4cdf08d6-2738-4c9e-9d27-345a0647ff7c",
                "https://opara.zih.tu-dresden.de/handle/123456789/821",
                "10.25532/OPARA-581",
            ],
            "notes": "TU Dresden institutional repository using DSpace 7.x",
        }

    def __init__(self):
        super().__init__()
        self.log = logging.getLogger("geoextent")
        self.host = {
            "hostname": [
                "https://opara.zih.tu-dresden.de/items/",
                "http://opara.zih.tu-dresden.de/items/",
                "https://opara.zih.tu-dresden.de/handle/",
                "http://opara.zih.tu-dresden.de/handle/",
            ],
            "api": "https://opara.zih.tu-dresden.de/server/api/",
        }
        self.reference = None
        self.item_uuid = None
        self.name = "Opara"
        self.throttle = False

    def validate_provider(self, reference):
        """Validate if the reference is a TU Dresden Opara repository URL or DOI"""
        self.reference = reference

        # Check for DOI resolver URLs pointing to OPARA DOIs
        doi_url_patterns = [
            r"^https?://(?:dx\.)?doi\.org/10\.25532/OPARA-(\d+)/?(?:[?#].*)?$",
            r"^https?://(?:www\.)?doi\.org/10\.25532/OPARA-(\d+)/?(?:[?#].*)?$",
        ]

        for pattern in doi_url_patterns:
            doi_url_match = re.search(pattern, reference, re.IGNORECASE)
            if doi_url_match:
                # We have the OPARA ID, but need to resolve to UUID via API
                opara_id = doi_url_match.group(1)
                doi = f"10.25532/OPARA-{opara_id}"
                try:
                    self.item_uuid = self._resolve_doi_to_uuid(doi)
                    return True
                except Exception as e:
                    self.log.debug(f"Failed to resolve DOI {doi}: {e}")
                    return False

        # Check for bare OPARA DOI pattern: 10.25532/OPARA-XXX
        bare_doi_pattern = r"^10\.25532/OPARA-(\d+)$"
        doi_match = re.search(bare_doi_pattern, reference, re.IGNORECASE)
        if doi_match:
            opara_id = doi_match.group(1)
            doi = f"10.25532/OPARA-{opara_id}"
            try:
                self.item_uuid = self._resolve_doi_to_uuid(doi)
                return True
            except Exception as e:
                self.log.debug(f"Failed to resolve DOI {doi}: {e}")
                return False

        # Check for direct OPARA repository URLs with item UUIDs
        item_url_pattern = re.compile(
            r"https?://opara\.zih\.tu-dresden\.de/items/([a-f0-9-]{36})/?(?:[?#].*)?$",
            re.IGNORECASE,
        )
        item_match = item_url_pattern.search(reference)
        if item_match:
            self.item_uuid = item_match.group(1)
            return True

        # Check for OPARA handle URLs (e.g., https://opara.zih.tu-dresden.de/handle/123456789/821)
        handle_url_pattern = re.compile(
            r"https?://opara\.zih\.tu-dresden\.de/handle/([0-9/]+)/?(?:[?#].*)?$",
            re.IGNORECASE,
        )
        handle_match = handle_url_pattern.search(reference)
        if handle_match:
            handle = handle_match.group(1)
            try:
                self.item_uuid = self._resolve_handle_to_uuid(handle)
                return True
            except Exception as e:
                self.log.debug(f"Failed to resolve handle {handle}: {e}")
                return False

        # Check for direct UUID (36 character hyphenated format) — verify against API
        if re.match(r"^[a-f0-9-]{36}$", reference, re.IGNORECASE):
            try:
                resp = self.session.get(
                    f"{self.host['api']}core/items/{reference.lower()}"
                )
                if resp.status_code == 200:
                    self.item_uuid = reference.lower()
                    return True
            except Exception:
                self.log.debug("Opara API check failed for UUID %s", reference)
            return False

        return False

    def _resolve_doi_to_uuid(self, doi):
        """Resolve a DOI to item UUID using the PID find endpoint"""
        pid_url = f"{self.host['api']}pid/find"
        response = self._request(pid_url, params={"id": doi})
        response.raise_for_status()

        data = response.json()
        uuid = data.get("uuid")
        if not uuid:
            raise ValueError(f"No UUID found for DOI {doi}")

        self.log.debug(f"Resolved DOI {doi} to UUID {uuid}")
        return uuid

    def _resolve_handle_to_uuid(self, handle):
        """Resolve a handle to item UUID using the PID find endpoint"""
        # Handles in DSpace are typically in format: prefix/suffix
        # For Opara, construct the full handle identifier
        handle_id = (
            f"123456789/{handle}" if not handle.startswith("123456789/") else handle
        )

        pid_url = f"{self.host['api']}pid/find"
        response = self._request(pid_url, params={"id": handle_id})
        response.raise_for_status()

        data = response.json()
        uuid = data.get("uuid")
        if not uuid:
            raise ValueError(f"No UUID found for handle {handle_id}")

        self.log.debug(f"Resolved handle {handle_id} to UUID {uuid}")
        return uuid

    def _get_metadata(self):
        """Get item metadata from DSpace API"""
        if not self.item_uuid:
            raise ValueError("No item UUID available for metadata extraction")

        metadata_url = f"{self.host['api']}core/items/{self.item_uuid}"
        response = self._request(metadata_url)
        response.raise_for_status()

        self.metadata = response.json()
        return self.metadata

    def _get_file_information(self):
        """Get file information including names, sizes, and download URLs"""
        if not self.item_uuid:
            raise ValueError("No item UUID available")

        # Get bundles for this item
        bundles_url = f"{self.host['api']}core/items/{self.item_uuid}/bundles"
        response = self._request(bundles_url)
        response.raise_for_status()

        bundles_data = response.json()
        files = []

        # Process each bundle
        for bundle in bundles_data.get("_embedded", {}).get("bundles", []):
            bundle_name = bundle.get("name", "")

            # Skip license bundles - focus on ORIGINAL content
            if bundle_name.upper() in ["LICENSE", "CC-LICENSE"]:
                continue

            bundle_uuid = bundle.get("uuid")
            if not bundle_uuid:
                continue

            # Get bitstreams (actual files) for this bundle
            bitstreams_url = f"{self.host['api']}core/bundles/{bundle_uuid}/bitstreams"
            bitstreams_response = self._request(bitstreams_url)
            bitstreams_response.raise_for_status()

            bitstreams_data = bitstreams_response.json()

            for bitstream in bitstreams_data.get("_embedded", {}).get("bitstreams", []):
                bitstream_uuid = bitstream.get("uuid")
                filename = bitstream.get("name", "")
                filesize = bitstream.get("sizeBytes", 0)

                if bitstream_uuid and filename:
                    download_url = (
                        f"{self.host['api']}core/bitstreams/{bitstream_uuid}/content"
                    )

                    files.append(
                        {
                            "name": filename,
                            "url": download_url,
                            "size": filesize,
                            "bundle": bundle_name,
                            "uuid": bitstream_uuid,
                        }
                    )

        self.log.debug(f"Found {len(files)} files in Opara item {self.item_uuid}")
        return files

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
        Download files from TU Dresden Opara repository.

        Parameters:
        - folder: Directory to store downloaded files
        - throttle: Rate limiting for API calls (not typically needed for Opara)
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
            self.log.warning(
                "Opara provider has limited metadata-only extraction capabilities. "
                "Using download_data=False may result in incomplete spatial extent information. "
                "Consider using download_data=True to download actual data files for better geospatial extraction."
            )
            try:
                metadata = self._get_metadata()
                self.log.info(f"Opara metadata extracted for item {self.item_uuid}")
                return
            except Exception as e:
                self.log.error(f"Failed to extract Opara metadata: {e}")
                raise

        self.log.debug(f"Downloading Opara item: {self.item_uuid}")

        try:
            # Get file information
            file_info = self._get_file_information()

            if not file_info:
                self.log.warning(f"No files found in Opara item {self.item_uuid}")
                return

            # Apply geospatial filtering if requested
            if download_skip_nogeo:
                filtered_files = self._filter_geospatial_files(
                    file_info,
                    skip_non_geospatial=download_skip_nogeo,
                    max_size_mb=None,  # Don't apply size limit here
                    additional_extensions=download_skip_nogeo_exts,
                )
            else:
                filtered_files = file_info

            # Apply size filtering if specified using the proper cumulative logic
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

            # Log download summary before starting
            self.log.info(
                f"Starting download of {len(final_files)} files from Opara item {self.item_uuid} ({total_size:,} bytes total)"
            )

            # Use the parallel download batch method from parent class
            self._download_files_batch(
                final_files,
                folder,
                show_progress=show_progress,
                max_workers=max_download_workers,
            )

            self.log.info(
                f"Downloaded {len(final_files)} files from Opara item {self.item_uuid} ({total_size:,} bytes total)"
            )

        except Exception as e:
            self.log.error(f"Error downloading from Opara: {e}")
            raise
