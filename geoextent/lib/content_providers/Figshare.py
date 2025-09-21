from requests import HTTPError
from .providers import DoiProvider
from ..extent import *


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
        self.reference = reference
        url = self.get_url
        if any([url.startswith(p) for p in self.host["hostname"]]):
            self.record_id = url.rsplit("/", maxsplit=1)[1]
            return True
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

    def download(self, folder, throttle=False):
        self.throttle = throttle
        self.log.debug("Downloading Figshare item id: {} ".format(self.record_id))
        try:
            download_links = self._get_file_links
            counter = 1
            for filename, file_link in download_links:
                resp = self._request(
                    file_link,
                    throttle=self.throttle,
                    stream=True,
                )
                filepath = os.path.join(folder, filename)
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
