from pathlib import Path
from requests import HTTPError
import urllib.parse
from .providers import DoiProvider
from ..extent import *


class Dryad(DoiProvider):
    def __init__(self):
        super().__init__()
        self.log = logging.getLogger("geoextent")
        self.host = {
            "hostname": [
                "https://datadryad.org/dataset/",
                "http://datadryad.org/dataset/",
            ],
            "api": "https://datadryad.org/api/v2/datasets/",
        }
        self.reference = None
        self.record_id = None
        self.record_id_html = None
        self.name = "Dryad"
        self.throttle = False

    def validate_provider(self, reference):
        self.reference = reference
        url = self.get_url
        if any([url.startswith(p) for p in self.host["hostname"]]):
            self.record_id = url.rsplit("/")[-2] + "/" + url.rsplit("/")[-1]
            self.record_id_html = urllib.parse.quote(self.record_id, safe="")
            return True
        else:
            return False

    def _get_metadata(self):
        if self.validate_provider:
            try:
                resp = self._request(
                    "{}{}".format(
                        self.host["api"],
                        self.record_id_html,
                    ),
                    headers={"accept": "application/json"},
                    throttle=self.throttle,
                )
                self.record = resp.json()
            except Exception:
                m = "The Dryad dataset : " + self.get_url + " does not exist"
                self.log.warning(m)
                raise HTTPError(m)

            latest_version = self.record["_links"]["stash:version"]["href"]

            try:
                resp = self._request(
                    "{}{}{}".format(
                        "https://datadryad.org",
                        latest_version,
                        "/files",
                    ),
                    headers={"accept": "application/json"},
                    throttle=self.throttle,
                )
                self.record2 = resp.json()
            except Exception as e:
                # TODO: make it prettier
                print("DEBUG:", e)
                raise

            return self.record2

        else:
            raise ValueError("Invalid content provider")

    @property
    def _get_file_links(self):
        try:
            record = self._get_metadata()
        except ValueError as e:
            raise Exception(e)

        try:
            files = record["_embedded"]["stash:files"]
        except Exception:
            m = "This record does not have Open Access files. Verify the Access rights of the record."
            self.log.warning(m)
            raise ValueError(m)

        file_list = []
        for j in files:
            link = "https://datadryad.org" + j["_links"]["stash:download"]["href"]
            path = j["path"]
            file_list.append([link, path])
        return file_list

    def download(self, folder, throttle=False, download_data=True, show_progress=True):
        from tqdm import tqdm

        self.throttle = throttle
        if not download_data:
            self.log.warning(
                "Dryad provider does not have geospatial metadata. "
                "Using download_data=False may result in limited or no spatial extent information. "
                "Consider using download_data=True to download actual data files for better geospatial extraction."
            )
            return

        self.log.debug("Downloading Dryad dataset id: {} ".format(self.record_id))
        try:
            # Try bulk ZIP download first with progress bar
            download_url = self.host["api"] + self.record_id_html + "/download"

            with tqdm(
                desc=f"Downloading Dryad dataset {self.record_id}",
                unit="B",
                unit_scale=True,
            ) as pbar:
                pbar.set_postfix_str("Downloading dataset.zip (bulk)")

                resp = self._request(
                    download_url,
                    throttle=self.throttle,
                    stream=True,
                )
                filename = "dataset.zip"
                filepath = os.path.join(folder, filename)

                with open(filepath, "wb") as dst:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            dst.write(chunk)
                            pbar.update(len(chunk))

            self.log.info(f"Downloaded Dryad dataset {self.record_id} as ZIP file")

        except ValueError as e:
            raise Exception(e)
        except HTTPError as e:
            if (
                e.response.content
                != b"The dataset is too large for zip file generation. Please download each file individually."
            ):
                m = "The Dryad dataset : " + self.get_url + " cannot be accessed"
                self.log.warning(m)
                raise HTTPError(m)

        try:
            self.log.info("Dataset too large for ZIP, downloading individual files...")

            # Get file information with sizes from metadata
            try:
                metadata = self._get_metadata()
                files = metadata.get("_embedded", {}).get("stash:files", [])

                # Calculate total size from metadata with progress bar
                total_size = 0
                file_info = []
                with tqdm(
                    total=len(files),
                    desc=f"Processing Dryad metadata for {self.record_id}",
                    unit="file",
                    leave=False,
                ) as metadata_pbar:
                    for file_data in files:
                        file_link = (
                            "https://datadryad.org"
                            + file_data["_links"]["stash:download"]["href"]
                        )
                        file_path = file_data["path"]
                        file_size = file_data.get("size", 0)  # Size in bytes

                        file_info.append(
                            {"url": file_link, "path": file_path, "size": file_size}
                        )
                        total_size += file_size

                        metadata_pbar.set_postfix_str(
                            f"Processing {Path(file_path).name} ({file_size:,} bytes)"
                        )
                        metadata_pbar.update(1)

            except Exception as metadata_error:
                self.log.warning(
                    f"Could not get file metadata: {metadata_error}, falling back to simple download"
                )
                # Fallback to original method without progress tracking
                download_links = self._get_file_links
                file_info = [
                    {"url": link, "path": path, "size": 0}
                    for link, path in download_links
                ]
                total_size = 0

            if not file_info:
                self.log.warning(f"No files found for Dryad dataset {self.record_id}")
                return

            # Log download summary before starting
            self.log.info(
                f"Starting download of {len(file_info)} files from Dryad dataset {self.record_id} ({total_size:,} bytes total)"
            )

            # Download individual files with progress bar
            with tqdm(
                total=total_size,
                desc=f"Downloading Dryad dataset {self.record_id}",
                unit="B",
                unit_scale=True,
            ) as pbar:
                for i, file_data in enumerate(file_info, 1):
                    file_link = file_data["url"]
                    file_path = file_data["path"]
                    file_size = file_data["size"]

                    pbar.set_postfix_str(
                        f"File {i}/{len(file_info)}: {Path(file_path).name}"
                    )

                    resp = self._request(
                        file_link,
                        throttle=self.throttle,
                        stream=True,
                    )
                    filepath = Path(folder).joinpath(file_path)
                    filepath.parent.mkdir(parents=True, exist_ok=True)

                    with open(filepath, "wb") as dst:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                dst.write(chunk)
                                pbar.update(len(chunk))

                    self.log.debug(
                        f"Downloaded Dryad file {i}/{len(file_info)}: {file_path}"
                    )

            self.log.info(
                f"Downloaded {len(file_info)} files from Dryad dataset {self.record_id} ({total_size} bytes total)"
            )

        except ValueError as e:
            raise Exception(e)
