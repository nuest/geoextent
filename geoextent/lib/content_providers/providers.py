from requests import Session, HTTPError
from geoextent.lib import helpfunctions as hf
import logging
import math
import time


class ContentProvider:
    def __init__(self):
        self.log = logging.getLogger("geoextent")


class DoiProvider(ContentProvider):

    def __init__(self):
        self.session = Session()

    def _request(self, url, throttle=False, **kwargs):
        while True:
            try:
                response = self.session.get(url, **kwargs)
                response.raise_for_status()
                break  # break while loop
            except HTTPError as e:
                # http error
                # dryad     dict_keys(['undefined', '404', '502', '503'])
                # figshare  dict_keys(['404', '422'])
                # zenodo    dict_keys(['410', '502', '404', '504'])
                # https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status

                if e.response.status_code == 429:
                    self._throttle(e.response)
                else:
                    print(e.response.status_code)
                    raise

        if throttle:
            self._throttle(response)

        return response

    def _throttle(self, response):
        values = [
            (response.headers.get("x-ratelimit-remaining")),  # Zenodo
            (response.headers.get("x-ratelimit-reset")),  # Zenodo
            (response.headers.get("ratelimit-remaining")),  # Dryad
            (response.headers.get("ratelimit-reset")),  # Dryad
        ]
        http_error = response.status_code

        wait_seconds = 1

        match values:
            case [None, None, None, None]:
                if http_error == 429:
                    wait_seconds = 60
                else:
                    wait_seconds = 1

            case [_, _, None, None]:
                remaining = int(values[0])
                reset = int(values[1])

                if remaining < 2 or http_error == 429:
                    wait_seconds = math.ceil(reset - time.time())

            case [None, None, _, _]:
                remaining = int(values[2])
                reset = int(values[3])

                if remaining < 2 or http_error == 429:
                    wait_seconds = math.ceil(reset - time.time())

            case _:
                if http_error == 429:
                    wait_seconds = 60
                else:
                    wait_seconds = 1

        print(f"INFO: Sleep {wait_seconds:.0f} s...")
        time.sleep(wait_seconds)

        return

    def _type_of_reference(self):
        if hf.doi_regexp.match(self.reference):
            return "DOI"
        elif hf.https_regexp.match(self.reference):
            return "Link"

    @property
    def get_url(self):

        if self._type_of_reference() == "DOI":
            doi = hf.doi_regexp.match(self.reference).group(2)

            try:
                resp = self._request("https://doi.org/{}".format(doi))
                resp.raise_for_status()

            except HTTPError:
                return doi

            return resp.url

        else:
            return self.reference
