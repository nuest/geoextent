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

    def download(self, folder, throttle=False):
        self.throttle = throttle
        self.log.debug("Downloading Dryad dataset id: {} ".format(self.record_id))
        try:
            # very simple method for download only, instead of 2+ API queries, but without metadata capabilities
            download_links = [self.host["api"] + self.record_id_html + "/download"]
            counter = 1
            for file_link in download_links:
                resp = self._request(
                    file_link,
                    throttle=self.throttle,
                    stream=True,
                )
                filename = "dataset.zip"
                filepath = os.path.join(folder, filename)

                with open(filepath, "wb") as dst:
                    for chunk in resp.iter_content(chunk_size=None):
                        dst.write(chunk)

                self.log.debug(
                    "{} out of {} files downloaded.".format(
                        counter, len(download_links)
                    )
                )
                counter += 1
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
            print("Downloading individial files.")
            download_links = self._get_file_links
            counter = 1
            for file_link, filename in download_links:
                resp = self._request(
                    file_link,
                    throttle=self.throttle,
                    stream=True,
                )
                filepath = Path(folder).joinpath(filename)
                # TODO: catch http error (?)
                with open(filepath, "wb") as dst:
                    for chunk in resp.iter_content(chunk_size=None):
                        dst.write(chunk)
                self.log.debug(
                    "{} out of {} files downloaded.".format(
                        counter, len(download_links)
                    )
                )
                counter += 1
        except ValueError as e:
            raise Exception(e)
