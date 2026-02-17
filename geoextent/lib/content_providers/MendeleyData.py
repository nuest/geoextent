from requests import HTTPError
from .providers import DoiProvider
from ..extent import *
from .. import helpfunctions as hf


class MendeleyData(DoiProvider):
    doi_prefixes = ("10.17632/",)

    @classmethod
    def provider_info(cls):
        return {
            "name": "Mendeley Data",
            "description": "Mendeley Data is a free and secure cloud-based data repository by Elsevier where researchers can store, share, and publish research data. It assigns DOIs to all published datasets and supports any file format.",
            "website": "https://data.mendeley.com/",
            "supported_identifiers": [
                "https://data.mendeley.com/datasets/{dataset_id}",
                "https://doi.org/10.17632/{dataset_id}",
                "10.17632/{dataset_id}",
            ],
            "doi_prefix": "10.17632",
            "examples": [
                "https://data.mendeley.com/datasets/example123",
                "10.17632/example123",
            ],
        }

    def __init__(self):
        super().__init__()
        self.log = logging.getLogger("geoextent")
        self.host = {
            "hostname": [
                "https://data.mendeley.com/datasets/",
                "http://data.mendeley.com/datasets/",
            ],
            "api": "https://data.mendeley.com/public-api/datasets/",
        }
        self.reference = None
        self.record_id = None
        self.version = None
        self.name = "Mendeley Data"
        self.throttle = False

    def validate_provider(self, reference):
        import re

        self.reference = reference
        url = self.get_url

        # Match Mendeley Data URLs: https://data.mendeley.com/datasets/{id}/{version}
        if any(url.startswith(p) for p in self.host["hostname"]):
            # Extract dataset ID (alphanumeric, typically 10 chars) and optional version
            pattern = re.compile(
                r"data\.mendeley\.com/datasets/([a-z0-9]+)(?:/(\d+))?", re.IGNORECASE
            )
            match = pattern.search(url)
            if match:
                self.record_id = match.group(1)
                self.version = match.group(2)
                return True

        # Match DOI prefix 10.17632/{id}.{version}
        doi_pattern = re.compile(r"10\.17632/([a-z0-9]+)(?:\.(\d+))?", re.IGNORECASE)
        doi_match = doi_pattern.search(reference)
        if doi_match:
            self.record_id = doi_match.group(1)
            self.version = doi_match.group(2)
            return True

        return False

    def _get_metadata(self):
        if self.record_id:
            try:
                # The public API does not support version parameters for file listing;
                # it always returns the latest version's files.
                api_url = "{}{}".format(self.host["api"], self.record_id)
                resp = self._request(
                    api_url,
                    headers={"Accept": "application/json"},
                    throttle=self.throttle,
                )
                resp.raise_for_status()
                self.record = resp.json()
                return self.record
            except Exception as e:
                m = (
                    "The Mendeley Data dataset: "
                    + self.record_id
                    + " does not exist or is not accessible"
                )
                self.log.warning(m)
                raise HTTPError(m)
        else:
            raise ValueError("Invalid content provider")

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
        from tqdm import tqdm

        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        self.throttle = throttle
        if not download_data:
            self.log.warning(
                "Mendeley Data provider does not have geospatial metadata. "
                "Using download_data=False may result in limited or no spatial extent information. "
                "Consider using download_data=True to download actual data files for better geospatial extraction."
            )
            return

        self.log.debug(
            "Downloading Mendeley Data dataset id: {} ".format(self.record_id)
        )
        try:
            metadata = self._get_metadata()
            files = metadata.get("files", [])

            if not files:
                self.log.warning(
                    f"No files found in Mendeley Data dataset {self.record_id}"
                )
                return

            # Extract file information from metadata
            file_info = []
            total_size = 0
            if show_progress:
                metadata_pbar = tqdm(
                    total=len(files),
                    desc=f"Processing Mendeley Data metadata for {self.record_id}",
                    unit="file",
                    leave=False,
                )

            try:
                for file_data in files:
                    filename = file_data.get("filename", "unknown")
                    content = file_data.get("content_details", {})
                    file_url = content.get("download_url")
                    file_size = content.get("size", 0)

                    if file_url:
                        file_info.append(
                            {"name": filename, "url": file_url, "size": file_size}
                        )
                        total_size += file_size

                    if show_progress:
                        metadata_pbar.set_postfix_str(
                            f"Processing {filename} ({file_size:,} bytes)"
                        )
                        metadata_pbar.update(1)

            finally:
                if show_progress:
                    metadata_pbar.close()

            if not file_info:
                self.log.warning(
                    f"No downloadable files found in Mendeley Data dataset {self.record_id}"
                )
                return

            # Apply file filtering for geospatial relevance and size constraints
            max_size_mb = max_size_bytes / (1024 * 1024) if max_size_bytes else None
            filtered_files = self._filter_geospatial_files(
                file_info,
                skip_non_geospatial=download_skip_nogeo,
                max_size_mb=max_size_mb,
                additional_extensions=download_skip_nogeo_exts,
            )

            if not filtered_files:
                self.log.warning("No files selected for download after filtering")
                return

            filtered_total_size = sum(f.get("size", 0) for f in filtered_files)

            self.log.info(
                f"Starting download of {len(filtered_files)} files from Mendeley Data dataset "
                f"{self.record_id} ({filtered_total_size:,} bytes total)"
            )

            self._download_files_batch(
                filtered_files,
                folder,
                show_progress=show_progress,
                max_workers=max_download_workers,
            )

            self.log.info(
                f"Downloaded {len(filtered_files)} files from Mendeley Data dataset "
                f"{self.record_id} ({filtered_total_size:,} bytes total)"
            )

        except ValueError as e:
            raise Exception(e)
