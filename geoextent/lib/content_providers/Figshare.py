from requests import HTTPError
from .providers import DoiProvider
from ..extent import *
from .. import helpfunctions as hf


class Figshare(DoiProvider):
    def __init__(self):
        super().__init__()
        self.log = logging.getLogger("geoextent")
        self.host = {
            "hostname": [
                "https://figshare.com/articles/",
                "http://figshare.com/articles/",
                "https://api.figshare.com/v2/articles/",
            ],
            "api": "https://api.figshare.com/v2/articles/",
        }
        self.reference = None
        self.record_id = None
        self.name = "Figshare"
        self.throttle = False

    def validate_provider(self, reference):
        import re

        self.reference = reference
        url = self.get_url

        if any([url.startswith(p) for p in self.host["hostname"]]):
            # Handle different Figshare URL patterns:
            # https://figshare.com/articles/dataset/title/RECORD_ID/VERSION
            # https://figshare.com/articles/RECORD_ID
            # https://api.figshare.com/v2/articles/RECORD_ID

            # Try to extract numeric record ID from URL
            # Pattern matches one or more digits that are followed by either end of string or /version
            figshare_pattern = re.compile(r"/(\d+)(?:/\d+)?/?$")
            match = figshare_pattern.search(url)

            if match:
                self.record_id = match.group(1)
                return True
            else:
                # Reject incomplete URLs (no valid record ID found)
                return False
        else:
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
                    "The Figshare item : https://figshare.com/articles/"
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
            m = "This item does not have Open Access files. Verify the Access rights of the item."
            self.log.warning(m)
            raise ValueError(m)

        file_list = []
        for j in files:
            name = j["name"]
            link = j["download_url"]
            file_list.append([name, link])
            # TODO: files can be empty
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
                "Figshare provider does not have geospatial metadata. "
                "Using download_data=False may result in limited or no spatial extent information. "
                "Consider using download_data=True to download actual data files for better geospatial extraction."
            )
            return

        self.log.debug("Downloading Figshare item id: {} ".format(self.record_id))
        try:
            # Get metadata to access file information including sizes
            metadata = self._get_metadata()
            files = metadata.get("files", [])

            if not files:
                self.log.warning(f"No files found in Figshare item {self.record_id}")
                return

            # Extract file information from metadata with progress bar
            file_info = []
            total_size = 0
            if show_progress:
                metadata_pbar = tqdm(
                    total=len(files),
                    desc=f"Processing Figshare metadata for {self.record_id}",
                    unit="file",
                    leave=False,
                )

            try:
                for file_data in files:
                    filename = file_data.get("name", "unknown")
                    file_url = file_data.get("download_url")
                    file_size = file_data.get("size", 0)

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
                    f"No downloadable files found in Figshare item {self.record_id}"
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
                self.log.warning(f"No files selected for download after filtering")
                return

            # Recalculate total size for filtered files
            filtered_total_size = sum(f.get("size", 0) for f in filtered_files)

            # Log download summary before starting
            self.log.info(
                f"Starting download of {len(filtered_files)} files from Figshare item {self.record_id} ({filtered_total_size:,} bytes total)"
            )

            # Use new parallel download batch method
            self._download_files_batch(
                filtered_files,
                folder,
                show_progress=show_progress,
                max_workers=max_download_workers,
            )

            self.log.info(
                f"Downloaded {len(filtered_files)} files from Figshare item {self.record_id} ({filtered_total_size} bytes total)"
            )

        except ValueError as e:
            raise Exception(e)
