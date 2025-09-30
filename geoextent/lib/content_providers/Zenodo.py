from requests import HTTPError
from .providers import DoiProvider
from .. import helpfunctions as hf
from ..extent import *


class Zenodo(DoiProvider):
    def __init__(self):
        super().__init__()
        self.log = logging.getLogger("geoextent")
        self.host = {
            "hostname": [
                "https://zenodo.org/records/",
                "http://zenodo.org/records/",
                "https://zenodo.org/record/",  # Legacy format
                "http://zenodo.org/record/",  # Legacy format
                "https://zenodo.org/api/records/",
            ],
            "api": "https://zenodo.org/api/records/",
        }
        self.reference = None
        self.record_id = None
        self.name = "Zenodo"
        self.throttle = False

    def validate_provider(self, reference):
        import re

        self.reference = reference
        url = self.get_url

        # Check if it starts with any of our known hostname patterns
        if any([url.startswith(p) for p in self.host["hostname"]]):
            # Handle trailing slashes by removing them first
            clean_url = url.rstrip("/")
            self.record_id = clean_url.rsplit("/", maxsplit=1)[1]
            return True

        # Check for legacy zenodo patterns and bare numeric IDs
        # This matches the original zenodo_regexp pattern: (https://zenodo.org/record/)?(.\d*)$
        zenodo_pattern = re.compile(
            r"(https://zenodo\.org/record/)?(.\d*)$", flags=re.I
        )
        match = zenodo_pattern.match(reference)
        if match:
            # Extract the numeric ID (second group)
            self.record_id = match.group(2)
            return True

        return False

    def _get_metadata(self):

        if self.validate_provider:
            try:
                resp = self._request(
                    "{}{}".format(self.host["api"], self.record_id),
                    headers={"accept": "application/json"},
                    throttle=self.throttle,
                )
                resp.raise_for_status()
                self.record = resp.json()
                return self.record
            except Exception as e:
                print("DEBUG:", e)
                m = (
                    "The zenodo record : https://zenodo.org/records/"
                    + self.record_id
                    + " does not exist"
                )
                self.log.warning(m)
                raise HTTPError(m)
        else:
            raise ValueError("Invalid content provider")

    @property
    def _get_file_links(self):

        try:
            self._get_metadata()
            record = self.record
        except ValueError as e:
            raise Exception(e)

        try:
            files = record["files"]
        except Exception:
            m = "This record does not have Open Access files. Verify the Access rights of the record."
            self.log.warning(m)
            raise ValueError(m)

        file_list = []
        for j in files:
            file_list.append(j["links"]["self"])
        return file_list

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
                "Zenodo provider does not have geospatial metadata. "
                "Using download_data=False may result in limited or no spatial extent information. "
                "Consider using download_data=True to download actual data files for better geospatial extraction."
            )
            return

        self.log.debug("Downloading Zenodo record id: {} ".format(self.record_id))
        try:
            # Get metadata to access file information including sizes
            metadata = self._get_metadata()
            files = metadata.get("files", [])

            if not files:
                self.log.warning(f"No files found in Zenodo record {self.record_id}")
                return

            # Extract file information from metadata with progress bar
            file_info = []
            total_size = 0
            if show_progress:
                metadata_pbar = tqdm(
                    total=len(files),
                    desc=f"Processing Zenodo metadata for {self.record_id}",
                    unit="file",
                    leave=False,
                )

            try:
                for file_data in files:
                    file_url = file_data["links"]["self"]
                    filename = file_data.get("key", file_url.split("/")[-2])
                    file_size = file_data.get("size", 0)

                    file_info.append(
                        {"url": file_url, "name": filename, "size": file_size}
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

            # Apply geospatial filtering first
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
                file_info = selected_files
            else:
                file_info = filtered_files
                total_size = sum(f.get("size", 0) for f in file_info)

            if not file_info:
                self.log.warning(f"No files selected for download after filtering")
                return

            # Log download summary before starting
            self.log.info(
                f"Starting download of {len(file_info)} files from Zenodo record {self.record_id} ({total_size:,} bytes total)"
            )

            # Use new parallel download batch method
            self._download_files_batch(
                file_info,
                folder,
                show_progress=show_progress,
                max_workers=max_download_workers,
            )

            self.log.info(
                f"Downloaded {len(file_info)} files from Zenodo record {self.record_id} ({total_size} bytes total)"
            )

        except ValueError as e:
            raise Exception(e)
