from requests import HTTPError
from .providers import DoiProvider
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

    def download(self, folder, throttle=False, download_data=True, show_progress=True):
        from tqdm import tqdm

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
                        {"url": file_url, "filename": filename, "size": file_size}
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

            # Log download summary before starting
            self.log.info(
                f"Starting download of {len(file_info)} files from Zenodo record {self.record_id} ({total_size:,} bytes total)"
            )

            # Download files with progress bar
            if show_progress:
                pbar = tqdm(
                    total=total_size,
                    desc=f"Downloading Zenodo record {self.record_id}",
                    unit="B",
                    unit_scale=True,
                )

            try:
                for i, file_data in enumerate(file_info, 1):
                    file_link = file_data["url"]
                    filename = file_data["filename"]
                    file_size = file_data["size"]

                    if show_progress:
                        pbar.set_postfix_str(f"File {i}/{len(file_info)}: {filename}")

                    resp = self._request(
                        file_link,
                        throttle=self.throttle,
                        stream=True,
                    )
                    filepath = os.path.join(folder, filename)

                    # Download with chunk-based progress tracking
                    downloaded_bytes = 0
                    with open(filepath, "wb") as dst:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                dst.write(chunk)
                                chunk_size = len(chunk)
                                downloaded_bytes += chunk_size
                                if show_progress:
                                    pbar.update(chunk_size)

                    self.log.debug(
                        f"Downloaded Zenodo file {i}/{len(file_info)}: {filename} ({downloaded_bytes} bytes)"
                    )

            finally:
                if show_progress:
                    pbar.close()

            self.log.info(
                f"Downloaded {len(file_info)} files from Zenodo record {self.record_id} ({total_size} bytes total)"
            )

        except ValueError as e:
            raise Exception(e)
