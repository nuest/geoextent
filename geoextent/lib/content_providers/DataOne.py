import json
import logging
import os
import re
from urllib.parse import quote, urlparse, unquote

from .providers import ContentProvider
from .. import helpfunctions as hf

logger = logging.getLogger("geoextent")


# DataONE member nodes already handled by dedicated geoextent providers.
# Datasets from these nodes should be skipped to avoid redundant processing.
_SKIP_NODES = {
    "urn:node:ARCTIC",  # Arctic Data Center provider
    "urn:node:PANGAEA",  # PANGAEA provider
    "urn:node:DRYAD",  # Dryad provider
}


class DataOne(ContentProvider):
    """Content provider for DataONE (Data Observation Network for Earth).

    DataONE federates ~38 member nodes including KNB, EDI/LTER, PISCO,
    NEON, BCO-DMO, ESS-DIVE, NCEI, TDAR, and others.  This provider
    queries the Coordinating Node (CN) Solr API for pre-computed spatial
    bounding boxes and temporal ranges — no file downloads needed.

    Supports:
    - DOI prefixes: 10.5063/ (KNB), 10.6085/ (PISCO)
    - URL patterns: search.dataone.org, dataone.org/datasets/
    - CN object/resolve URLs: cn.dataone.org/cn/v2/object/... or .../resolve/...
    """

    doi_prefixes = ("10.5063/", "10.6085/")

    CN_SOLR = "https://cn.dataone.org/cn/v2/query/solr/"
    SOLR_FIELDS = (
        "id,title,northBoundCoord,southBoundCoord,"
        "eastBoundCoord,westBoundCoord,beginDate,endDate,datasource"
    )

    @classmethod
    def provider_info(cls):
        return {
            "name": "DataONE",
            "description": (
                "DataONE (Data Observation Network for Earth) federates ~38 member "
                "node repositories.  Extracts pre-computed spatial bounding boxes and "
                "temporal ranges from the Coordinating Node Solr API without downloading "
                "data files."
            ),
            "website": "https://www.dataone.org/",
            "supported_identifiers": [
                "https://search.dataone.org/view/{pid}",
                "https://dataone.org/datasets/{pid}",
                "https://cn.dataone.org/cn/v2/object/{pid}",
                "https://doi.org/10.5063/{id}",
                "https://doi.org/10.6085/{id}",
                "10.5063/{id}",
                "10.6085/{id}",
            ],
            "doi_prefix": "10.5063, 10.6085",
            "examples": [
                "10.5063/F1Z60M87",
                "https://search.dataone.org/view/doi%3A10.5063%2FF1Z60M87",
            ],
            "notes": (
                "Metadata-only provider.  Datasets from Arctic Data Center, PANGAEA, "
                "and Dryad are deferred to their dedicated providers."
            ),
        }

    def __init__(self):
        super().__init__()
        self.dataset_id = None
        self.metadata = None
        self.name = "DataONE"
        self._session = None

    @property
    def supports_metadata_extraction(self):
        return True

    def _get_session(self):
        if self._session is None:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            self._session = requests.Session()
            retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503])
            self._session.mount("https://", HTTPAdapter(max_retries=retry))
            self._session.headers["User-Agent"] = (
                "geoextent (https://github.com/nuest/geoextent)"
            )
        return self._session

    def _request(self, url, **kwargs):
        kwargs.setdefault("timeout", 30)
        return self._get_session().get(url, **kwargs)

    # ------------------------------------------------------------------ #
    # Identifier parsing
    # ------------------------------------------------------------------ #

    _DOI_RE = re.compile(r"(10\.5063/[^\s]+|10\.6085/[^\s]+)")

    _SEARCH_HOST_RE = re.compile(
        r"^(search\.dataone\.org|dataone\.org)$", re.IGNORECASE
    )
    _CN_HOST = "cn.dataone.org"

    def _extract_pid_from_url(self, url):
        """Extract a DataONE PID from a URL, or return None."""
        try:
            parsed = urlparse(url)
            hostname = (parsed.hostname or "").lower()
        except Exception:
            return None

        path = unquote(parsed.path) if parsed.path else ""
        fragment = unquote(parsed.fragment) if parsed.fragment else ""

        # search.dataone.org/view/{pid} or /#view/{pid}
        if self._SEARCH_HOST_RE.match(hostname):
            for segment in (path, fragment):
                m = re.search(r"/view/(.+)", segment)
                if m:
                    return m.group(1).strip().rstrip("/")
            # /datasets/{pid}
            m = re.search(r"/datasets/(.+)", path)
            if m:
                return m.group(1).strip().rstrip("/")
            return None

        # cn.dataone.org/cn/v2/object/{pid} or /resolve/{pid}
        if hostname == self._CN_HOST:
            m = re.search(r"/(?:object|resolve)/(.+)", path)
            if m:
                return m.group(1).strip().rstrip("/")

        return None

    def validate_provider(self, reference):
        """Validate if the reference is a DataONE identifier."""
        self.reference = reference

        # 1) DOI prefix match — construct Solr PID
        doi_match = self._DOI_RE.search(reference)
        if doi_match:
            self.dataset_id = "doi:" + doi_match.group(1)
            return True

        # 2) URL patterns
        pid = self._extract_pid_from_url(reference)
        if pid is not None:
            self.dataset_id = pid
            return True

        return False

    # ------------------------------------------------------------------ #
    # Solr metadata retrieval
    # ------------------------------------------------------------------ #

    def _solr_lookup(self, pid):
        """Query the CN Solr for a PID, trying ``id`` then ``seriesId``.

        Returns the first matching Solr doc, or None.
        """
        encoded_pid = pid.replace('"', '\\"')

        # Try exact id match
        url = (
            f'{self.CN_SOLR}?q=id:"{encoded_pid}"'
            f"&fl={self.SOLR_FIELDS}&wt=json&rows=1"
        )
        logger.debug("DataONE Solr query: %s", url)
        resp = self._request(url)
        resp.raise_for_status()
        docs = resp.json().get("response", {}).get("docs", [])
        if docs:
            return docs[0]

        # Try seriesId (version chains)
        url2 = (
            f'{self.CN_SOLR}?q=seriesId:"{encoded_pid}"'
            f"&fl={self.SOLR_FIELDS}&wt=json&rows=1"
            f"&sort=dateUploaded+desc"
        )
        logger.debug("DataONE Solr seriesId query: %s", url2)
        resp2 = self._request(url2)
        resp2.raise_for_status()
        docs2 = resp2.json().get("response", {}).get("docs", [])
        if docs2:
            return docs2[0]

        return None

    def _get_metadata(self):
        """Fetch dataset metadata from the DataONE CN Solr API."""
        if self.metadata is not None:
            return self.metadata

        if not self.dataset_id:
            raise ValueError("No dataset ID available for metadata extraction")

        doc = self._solr_lookup(self.dataset_id)
        if doc is None:
            raise ValueError(f"No metadata found in DataONE for: {self.dataset_id}")

        # Check if this dataset belongs to a node with a dedicated provider
        datasource = doc.get("datasource", "")
        if datasource in _SKIP_NODES:
            logger.info(
                "DataONE dataset %s belongs to %s which has a dedicated "
                "provider — skipping",
                self.dataset_id,
                datasource,
            )
            raise ValueError(
                f"Dataset {self.dataset_id} belongs to {datasource}, "
                f"use the dedicated provider instead"
            )

        self.metadata = doc
        logger.debug(
            "Retrieved DataONE metadata for: %s (node: %s)",
            doc.get("title", self.dataset_id),
            datasource,
        )
        return self.metadata

    def _extract_spatial_metadata(self):
        """Extract spatial extent from DataONE Solr metadata.

        Returns dict with bbox in [W, S, E, N] (internal lon/lat order), or None.
        """
        if not self.metadata:
            self._get_metadata()

        try:
            north = float(self.metadata["northBoundCoord"])
            south = float(self.metadata["southBoundCoord"])
            east = float(self.metadata["eastBoundCoord"])
            west = float(self.metadata["westBoundCoord"])
        except (KeyError, TypeError, ValueError) as e:
            logger.debug("DataONE: no spatial metadata: %s", e)
            return None

        bbox = [west, south, east, north]
        if not hf.validate_bbox_wgs84(bbox):
            logger.warning(
                "DataONE: bbox %s outside valid WGS84 bounds, skipping", bbox
            )
            return None

        return {"bbox": bbox, "crs": "4326"}

    def _extract_temporal_metadata(self):
        """Extract temporal extent from DataONE Solr metadata.

        Returns [start_date, end_date] or None.
        """
        if not self.metadata:
            self._get_metadata()

        begin = self.metadata.get("beginDate")
        end = self.metadata.get("endDate")

        if not begin and not end:
            return None

        def parse_date(date_str):
            if not date_str:
                return None
            return date_str[:10]  # "2020-01-01T00:00:00Z" → "2020-01-01"

        start_date = parse_date(begin)
        end_date = parse_date(end)

        if start_date or end_date:
            return [start_date or end_date, end_date or start_date]
        return None

    # ------------------------------------------------------------------ #
    # GeoJSON output
    # ------------------------------------------------------------------ #

    def _create_geojson_from_metadata(self, target_folder, spatial, temporal):
        """Write a GeoJSON file encoding the extracted extent."""
        bbox = spatial["bbox"]
        min_lon, min_lat, max_lon, max_lat = bbox

        properties = {
            "source": self.name,
            "dataset_id": self.dataset_id,
            "title": self.metadata.get("title", "") if self.metadata else "",
        }

        if temporal and isinstance(temporal, list) and len(temporal) >= 2:
            if temporal[0]:
                properties["start_time"] = temporal[0]
            if temporal[1]:
                properties["end_time"] = temporal[1]

        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [min_lon, min_lat],
                                [max_lon, min_lat],
                                [max_lon, max_lat],
                                [min_lon, max_lat],
                                [min_lon, min_lat],
                            ]
                        ],
                    },
                    "properties": properties,
                }
            ],
        }

        safe_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", self.dataset_id)
        geojson_file = os.path.join(target_folder, f"dataone_{safe_id}.geojson")
        with open(geojson_file, "w") as f:
            json.dump(geojson_data, f, indent=2)

        temporal_info = f" with temporal extent {temporal}" if temporal else ""
        logger.info(
            "Created GeoJSON metadata file for DataONE dataset %s%s",
            self.dataset_id,
            temporal_info,
        )

    # ------------------------------------------------------------------ #
    # Download entry point
    # ------------------------------------------------------------------ #

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
        progress_callback=None,
    ):
        """Extract metadata from DataONE.

        This is a metadata-only provider — ``download_data`` is ignored.
        Spatial and temporal extents are always extracted from the CN Solr API.
        """
        logger.info("Processing DataONE dataset: %s", self.reference)

        try:
            self._get_metadata()
            spatial = self._extract_spatial_metadata()
            temporal = self._extract_temporal_metadata()

            if spatial and "bbox" in spatial:
                self._create_geojson_from_metadata(folder, spatial, temporal)
            else:
                logger.warning(
                    "DataONE dataset %s has no extractable spatial metadata",
                    self.dataset_id,
                )
        except Exception as e:
            logger.error("Failed to extract DataONE metadata: %s", e)
            raise

        return folder
