import json
import logging
import os
import re
from urllib.parse import urlparse

from requests import HTTPError

from .providers import DoiProvider
from .. import helpfunctions as hf

logger = logging.getLogger("geoextent")

# Registry of known InvenioRDM instances.
# Each entry maps a hostname key to its API base URL, DOI prefixes,
# display name, and recognized URL patterns.
INVENIORDM_INSTANCES = {
    "zenodo.org": {
        "api": "https://zenodo.org/api/records/",
        "doi_prefixes": ("10.5281/zenodo",),
        "name": "Zenodo",
        "hostnames": [
            "https://zenodo.org/records/",
            "https://zenodo.org/record/",
            "https://zenodo.org/api/records/",
        ],
    },
    "data.caltech.edu": {
        "api": "https://data.caltech.edu/api/records/",
        "doi_prefixes": ("10.22002",),
        "name": "CaltechDATA",
        "hostnames": ["https://data.caltech.edu/records/"],
    },
    "researchdata.tuwien.ac.at": {
        "api": "https://researchdata.tuwien.ac.at/api/records/",
        "doi_prefixes": ("10.48436",),
        "name": "TU Wien Research Data",
        "hostnames": ["https://researchdata.tuwien.ac.at/records/"],
    },
    "freidata.uni-freiburg.de": {
        "api": "https://freidata.uni-freiburg.de/api/records/",
        "doi_prefixes": ("10.60493",),
        "name": "Frei-Data",
        "hostnames": ["https://freidata.uni-freiburg.de/records/"],
    },
    "gkhub.earthobservations.org": {
        "api": "https://gkhub.earthobservations.org/api/records/",
        "doi_prefixes": ("10.60566",),
        "name": "GEO Knowledge Hub",
        "hostnames": ["https://gkhub.earthobservations.org/records/"],
    },
    "repository.tugraz.at": {
        "api": "https://repository.tugraz.at/api/records/",
        "doi_prefixes": ("10.3217",),
        "name": "TU Graz Repository",
        "hostnames": ["https://repository.tugraz.at/records/"],
    },
    "archive.materialscloud.org": {
        "api": "https://archive.materialscloud.org/api/records/",
        "doi_prefixes": ("10.24435",),
        "name": "Materials Cloud Archive",
        "hostnames": ["https://archive.materialscloud.org/records/"],
    },
    "fdat.uni-tuebingen.de": {
        "api": "https://fdat.uni-tuebingen.de/api/records/",
        "doi_prefixes": ("10.57754",),
        "name": "FDAT",
        "hostnames": ["https://fdat.uni-tuebingen.de/records/"],
    },
    "archive.nfdi4plants.org": {
        "api": "https://archive.nfdi4plants.org/api/records/",
        "doi_prefixes": ("10.60534",),
        "name": "DataPLANT ARChive",
        "hostnames": ["https://archive.nfdi4plants.org/records/"],
    },
    "datarepository.kth.se": {
        "api": "https://datarepository.kth.se/api/records/",
        "doi_prefixes": ("10.71775",),
        "name": "KTH Data Repository",
        "hostnames": ["https://datarepository.kth.se/records/"],
    },
    "prism.northwestern.edu": {
        "api": "https://prism.northwestern.edu/api/records/",
        "doi_prefixes": ("10.18131",),
        "name": "Prism",
        "hostnames": ["https://prism.northwestern.edu/records/"],
    },
    "ultraviolet.library.nyu.edu": {
        "api": "https://ultraviolet.library.nyu.edu/api/records/",
        "doi_prefixes": ("10.58153",),
        "name": "NYU Ultraviolet",
        "hostnames": ["https://ultraviolet.library.nyu.edu/records/"],
    },
}

# Record ID pattern: numeric (Zenodo legacy), alphanumeric slug (InvenioRDM),
# or dotted version (Materials Cloud, e.g. "2022.126")
_RECORD_ID_PATTERN = re.compile(r"^[a-z0-9][-a-z0-9.]*$", re.IGNORECASE)


class InvenioRDM(DoiProvider):
    """Generic content provider for InvenioRDM-based research data repositories.

    Supports all instances registered in INVENIORDM_INSTANCES.
    The Zenodo subclass handles zenodo.org specifically; this class catches
    all other InvenioRDM instances (CaltechDATA, TU Wien, Frei-Data, etc.).
    """

    @classmethod
    def provider_info(cls):
        # Build instance list from registry (excluding Zenodo, which has its own entry)
        instances = []
        for host_key, config in INVENIORDM_INSTANCES.items():
            if host_key == "zenodo.org":
                continue
            instances.append(
                {
                    "name": config["name"],
                    "hostnames": config["hostnames"],
                    "api": config["api"],
                    "doi_prefixes": list(config["doi_prefixes"]),
                }
            )
        return {
            "name": "InvenioRDM",
            "description": "Generic provider for InvenioRDM-based research data repositories. Supports multiple institutional instances sharing the same platform and REST API.",
            "website": "https://inveniosoftware.org/products/rdm/",
            "instances": instances,
            "supported_identifiers": [
                "https://{instance}/records/{record_id}",
                "https://doi.org/{doi_prefix}/{record_id}",
                "{doi_prefix}/{record_id}",
            ],
            "doi_prefixes": list(cls.doi_prefixes),
            "examples": [
                "10.22002/D1.1705",
                "https://data.caltech.edu/records/0ca1t-hzt77",
                "10.48436/jpzv9-c8w75",
            ],
            "notes": "Handles S3 redirect downloads (Zenodo), S3 signed URL responses (CaltechDATA, Frei-Data), and direct binary downloads (TU Wien). Supports metadata-only extraction via metadata.locations and metadata.dates.",
        }

    # DOI prefixes for non-Zenodo InvenioRDM instances (Phase 1 fast matching)
    doi_prefixes = (
        "10.22002",  # CaltechDATA
        "10.48436",  # TU Wien
        "10.60493",  # Frei-Data
        "10.60566",  # GEO Knowledge Hub
        "10.3217",  # TU Graz
        "10.24435",  # Materials Cloud Archive
        "10.57754",  # FDAT
        "10.60534",  # DataPLANT ARChive
        "10.71775",  # KTH Data Repository
        "10.18131",  # Prism
        "10.58153",  # NYU Ultraviolet
    )

    def __init__(self):
        super().__init__()
        self.log = logging.getLogger("geoextent")
        self._instance_config = None
        self.host = {"hostname": [], "api": None}
        self.reference = None
        self.record_id = None
        self.name = "InvenioRDM"
        self.throttle = False

    @property
    def supports_metadata_extraction(self):
        return True

    def _find_instance(self, url):
        """Match a resolved URL against all known InvenioRDM hostnames.

        Returns the instance config dict or None.
        """
        for _key, config in INVENIORDM_INSTANCES.items():
            for hostname_prefix in config["hostnames"]:
                if url.startswith(hostname_prefix):
                    return config
        return None

    def validate_provider(self, reference):
        """Match reference against all known InvenioRDM instances.

        1. Resolve DOI/URL via parent get_url
        2. Check resolved URL against all registered hostnames
        3. Extract record_id (numeric or alphanumeric slug)
        4. Set self._instance_config, self.host, self.name
        """
        self.reference = reference
        url = self.get_url

        config = self._find_instance(url)
        if config is not None:
            # Extract record ID from URL
            clean_url = url.rstrip("/")
            record_id = clean_url.rsplit("/", maxsplit=1)[1]

            if _RECORD_ID_PATTERN.match(record_id):
                self._instance_config = config
                self.host = {
                    "hostname": config["hostnames"],
                    "api": config["api"],
                }
                self.name = config["name"]
                self.record_id = record_id
                return True

        return False

    def _get_metadata(self):
        """Fetch record metadata from GET /api/records/{id}."""
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
            m = "The {} record {} does not exist or is not accessible: {}".format(
                self.name, self.record_id, e
            )
            self.log.warning(m)
            raise HTTPError(m)

    def _get_files_info(self, record):
        """Extract file info from record metadata.

        Handles both formats:
        - Legacy (Zenodo): record["files"] is a list with links.self
        - InvenioRDM standard: record["files"]["entries"] is a dict with links.content
        - Fallback: fetch /api/records/{id}/files separately

        Returns list of dicts with 'url', 'name', 'size' keys.
        """
        file_info = []

        files = record.get("files")
        if files is None:
            return file_info

        # Zenodo legacy format: files is a list of file dicts
        if isinstance(files, list):
            for f in files:
                url = f.get("links", {}).get("self")
                name = f.get("key", url.split("/")[-2] if url else "unknown")
                size = f.get("size", 0)
                if url:
                    file_info.append({"url": url, "name": name, "size": size})
            return file_info

        # InvenioRDM standard: files is a dict with "entries" or "enabled"
        if isinstance(files, dict):
            entries = files.get("entries")
            if entries and isinstance(entries, dict):
                for key, entry in entries.items():
                    url = entry.get("links", {}).get("content")
                    name = key
                    size = entry.get("size", 0)
                    if url:
                        file_info.append({"url": url, "name": name, "size": size})
                return file_info

        # Fallback: fetch the files endpoint separately
        if not file_info:
            try:
                resp = self._request(
                    "{}{}{}".format(self.host["api"], self.record_id, "/files"),
                    headers={"accept": "application/json"},
                    throttle=self.throttle,
                )
                resp.raise_for_status()
                files_data = resp.json()
                entries = files_data.get("entries", {})
                if isinstance(entries, dict):
                    for key, entry in entries.items():
                        url = entry.get("links", {}).get("content")
                        name = key
                        size = entry.get("size", 0)
                        if url:
                            file_info.append({"url": url, "name": name, "size": size})
                elif isinstance(entries, list):
                    for entry in entries:
                        url = entry.get("links", {}).get("content") or entry.get(
                            "links", {}
                        ).get("self")
                        name = entry.get("key", "unknown")
                        size = entry.get("size", 0)
                        if url:
                            file_info.append({"url": url, "name": name, "size": size})
            except Exception as e:
                self.log.warning(
                    "Failed to fetch files from /files endpoint: {}".format(e)
                )

        return file_info

    def _download_file_optimized(
        self, url, filepath, chunk_size=None, show_progress=False
    ):
        """Download a file handling InvenioRDM download patterns:

        1. Zenodo: HTTP 302 redirect to S3 (requests follows automatically)
        2. CaltechDATA/Frei-Data/GKHub: HTTP 200 with S3 signed URL in text/plain body
        3. FDAT: HTTP 200 with S3 signed URL in body + Location header
        4. TU Wien: HTTP 200 with binary content directly

        Detection: check text/plain Content-Type, Location header with S3 URL,
        or peek at response body for small redirect URLs.
        """
        if chunk_size is None:
            chunk_size = self.download_chunk_size

        self.log.debug(
            "Downloading {} to {} with {} byte chunks".format(url, filepath, chunk_size)
        )

        try:
            resp = self.session.get(url, stream=True)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "").lower()

            redirect_url = None

            # Pattern 2: explicit text/plain body containing S3 URL
            if "text/plain" in content_type:
                body = resp.text.strip()
                resp.close()
                if body.startswith("http"):
                    redirect_url = body

            # Pattern 3: Location header with S3 URL on 200 response (FDAT)
            elif resp.status_code == 200 and "location" in resp.headers:
                loc = resp.headers["location"]
                if loc.startswith("http"):
                    resp.close()
                    redirect_url = loc

            if redirect_url:
                self.log.debug(
                    "Following S3 redirect URL for {}".format(
                        os.path.basename(filepath)
                    )
                )
                resp = self.session.get(redirect_url, stream=True)
                resp.raise_for_status()

            # Stream binary to file
            downloaded = 0
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

            self.log.debug("Download completed: {} bytes".format(downloaded))
            return downloaded

        except Exception as e:
            self.log.error("Failed to download {}: {}".format(url, e))
            if os.path.exists(filepath):
                os.remove(filepath)
            raise

    def _parse_locations(self, record):
        """Parse metadata.locations.features[] into a list of GeoJSON geometries.

        InvenioRDM metadata.locations follows GeoJSON conventions with
        coordinates in [lon, lat] order, matching geoextent internal order.

        Returns list of GeoJSON geometry dicts, or empty list.
        """
        locations = record.get("metadata", {}).get("locations", {})
        features = locations.get("features", [])

        geometries = []
        for feature in features:
            geometry = feature.get("geometry")
            if geometry and geometry.get("type") and geometry.get("coordinates"):
                geometries.append(geometry)

        return geometries

    def _parse_temporal(self, record):
        """Parse temporal extent from InvenioRDM metadata.

        Sources (in priority order):
        1. metadata.dates[] — EDTF format (e.g. "2015/2018", "2020-01-01")
        2. metadata.publication_date — fallback

        Returns (start, end) tuple or None.
        """
        metadata = record.get("metadata", {})

        # Try metadata.dates first
        dates = metadata.get("dates", [])
        for date_entry in dates:
            date_str = date_entry.get("date", "")
            if "/" in date_str:
                # EDTF range: "2015/2018" or "2020-01-01/2020-12-31"
                parts = date_str.split("/", 1)
                return (parts[0].strip(), parts[1].strip())
            elif date_str:
                return (date_str.strip(), date_str.strip())

        # Fallback to publication_date
        pub_date = metadata.get("publication_date")
        if pub_date:
            return (pub_date[:10], pub_date[:10])

        return None

    def _write_metadata_geojson(self, folder, record):
        """Write GeoJSON from InvenioRDM metadata (locations + dates).

        Returns path to created file, or None if no extractable metadata.
        """
        geometries = self._parse_locations(record)
        temporal = self._parse_temporal(record)

        properties = {
            "source": "{} metadata".format(self.name),
            "dataset_id": self.record_id,
            "title": record.get("metadata", {}).get("title", ""),
        }

        if temporal:
            properties["start_time"] = temporal[0]
            properties["end_time"] = temporal[1]

        features = []

        if geometries:
            for geom in geometries:
                feature = {
                    "type": "Feature",
                    "geometry": geom,
                    "properties": dict(properties),
                }
                features.append(feature)
        elif temporal:
            # Null geometry with temporal-only properties
            features.append(
                {
                    "type": "Feature",
                    "geometry": None,
                    "properties": properties,
                }
            )
        else:
            self.log.debug(
                "{} record {}: no geolocation or temporal metadata".format(
                    self.name, self.record_id
                )
            )
            return None

        geojson_data = {
            "type": "FeatureCollection",
            "features": features,
        }

        safe_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", self.record_id)
        geojson_file = os.path.join(folder, "inveniordm_{}.geojson".format(safe_id))
        with open(geojson_file, "w") as f:
            json.dump(geojson_data, f, indent=2)

        parts = []
        if geometries:
            parts.append("{} location(s)".format(len(geometries)))
        if temporal:
            parts.append("time={} to {}".format(temporal[0], temporal[1]))
        self.log.info(
            "Created GeoJSON metadata file for {} record {} ({})".format(
                self.name, self.record_id, ", ".join(parts)
            )
        )
        return geojson_file

    def _download_metadata_only(self, folder):
        """Metadata-only extraction from /api/records/{id}."""
        try:
            record = self._get_metadata()
        except Exception as e:
            self.log.warning("Failed to fetch {} metadata: {}".format(self.name, e))
            return

        result = self._write_metadata_geojson(folder, record)
        if result is None:
            self.log.warning(
                "{} record {} has no geolocation or temporal coverage in metadata. "
                "Consider using download_data=True.".format(self.name, self.record_id)
            )

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
        """Download files from any InvenioRDM instance.

        Routes to _download_metadata_only when download_data=False.
        Uses _get_files_info + _download_files_batch for data download.
        """
        from tqdm import tqdm

        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        self.throttle = throttle

        if not download_data:
            self._download_metadata_only(folder)
            return

        self.log.debug("Downloading {} record id: {}".format(self.name, self.record_id))

        try:
            record = self._get_metadata()
            file_info = self._get_files_info(record)

            if not file_info:
                self.log.warning(
                    "No files found in {} record {}".format(self.name, self.record_id)
                )
                return

            # Show metadata processing progress
            total_size = sum(f.get("size", 0) for f in file_info)

            # Apply geospatial filtering first
            if download_skip_nogeo:
                filtered_files = self._filter_geospatial_files(
                    file_info,
                    skip_non_geospatial=download_skip_nogeo,
                    additional_extensions=download_skip_nogeo_exts,
                )
            else:
                filtered_files = file_info

            # Apply size filtering if specified
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
                self.log.warning("No files selected for download after filtering")
                return

            self.log.info(
                "Starting download of {} files from {} record {} ({:,} bytes total)".format(
                    len(file_info), self.name, self.record_id, total_size
                )
            )

            # Use parallel download batch method
            self._download_files_batch(
                file_info,
                folder,
                show_progress=show_progress,
                max_workers=max_download_workers,
            )

            self.log.info(
                "Downloaded {} files from {} record {} ({} bytes total)".format(
                    len(file_info), self.name, self.record_id, total_size
                )
            )

        except ValueError as e:
            raise Exception(e)
