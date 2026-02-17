from requests import HTTPError
from .providers import DoiProvider
from ..extent import *
from .. import helpfunctions as hf


class Figshare(DoiProvider):
    doi_prefixes = ("10.6084/m9.figshare",)

    @classmethod
    def provider_info(cls):
        return {
            "name": "Figshare",
            "description": "Figshare is an online open access repository where researchers can preserve and share their research outputs including figures, datasets, images, and videos. It allows researchers to publish files in any format with assigned DOIs and tracks download statistics for altmetrics.",
            "website": "https://figshare.com/",
            "supported_identifiers": [
                "https://figshare.com/articles/{article_id}",
                "https://doi.org/10.6084/m9.figshare.{article_id}",
                "10.6084/m9.figshare.{article_id}",
            ],
            "doi_prefix": "10.6084/m9.figshare",
            "examples": ["https://doi.org/10.6084/m9.figshare.12345678"],
        }

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

    @property
    def supports_metadata_extraction(self):
        return True

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

        # Fallback: match *.figshare.com institutional portals
        # (e.g. springernature.figshare.com, monash.figshare.com)
        from urllib.parse import urlparse

        parsed_url = urlparse(url)
        if parsed_url.hostname and parsed_url.hostname.endswith("figshare.com"):
            figshare_pattern = re.compile(r"/(\d+)(?:/\d+)?/?$")
            match = figshare_pattern.search(url)
            if match:
                self.record_id = match.group(1)
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

    def _parse_geolocation(self, metadata):
        """Parse geolocation from Figshare API metadata.

        Sources (in priority order):
        1. custom_fields with 'Geolocation Latitude'/'Geolocation Longitude'
           (used by institutional portals like 4TU, springernature)
        2. Top-level latitude/longitude fields (rarely populated on core figshare.com)

        Returns: dict with 'lat', 'lon' (any may be None)
        """
        lat = lon = None

        # Try custom_fields first (institutional portals)
        custom_fields = metadata.get("custom_fields", [])
        for field in custom_fields:
            name = field.get("name", "")
            value = field.get("value", "")
            if name == "Geolocation Latitude":
                try:
                    lat = float(value)
                except (ValueError, TypeError):
                    pass
            elif name == "Geolocation Longitude":
                try:
                    lon = float(value)
                except (ValueError, TypeError):
                    pass

        # Fallback to top-level latitude/longitude
        if lat is None and metadata.get("latitude") is not None:
            try:
                lat = float(metadata["latitude"])
            except (ValueError, TypeError):
                pass
        if lon is None and metadata.get("longitude") is not None:
            try:
                lon = float(metadata["longitude"])
            except (ValueError, TypeError):
                pass

        return {"lat": lat, "lon": lon}

    def _parse_geo_coverage(self, metadata):
        """Parse 'Geographic Coverage' custom field containing GeoJSON.

        Used by USDA Ag Data Commons and similar institutional portals that store
        GeoJSON FeatureCollections in a custom_fields entry.

        Returns: dict (GeoJSON FeatureCollection) or None
        """
        import json

        custom_fields = metadata.get("custom_fields", [])
        for field in custom_fields:
            name = field.get("name", "")
            value = field.get("value", "")
            if name == "Geographic Coverage" and value:
                try:
                    geojson = json.loads(value) if isinstance(value, str) else value
                    if isinstance(geojson, dict) and geojson.get("type") in (
                        "FeatureCollection",
                        "Feature",
                        "Point",
                        "Polygon",
                        "MultiPolygon",
                        "MultiPoint",
                        "LineString",
                        "MultiLineString",
                    ):
                        return geojson
                except (json.JSONDecodeError, TypeError):
                    pass
        return None

    def _parse_temporal(self, metadata):
        """Parse temporal extent from Figshare metadata.

        Sources (in priority order):
        1. custom_fields 'Temporal Extent Start Date'/'Temporal Extent End Date'
           (used by USDA Ag Data Commons)
        2. published_date (always available)

        Returns (start, end) tuple or None.
        """
        start = end = None

        # Try custom_fields first (USDA Ag Data Commons)
        custom_fields = metadata.get("custom_fields", [])
        for field in custom_fields:
            name = field.get("name", "")
            value = field.get("value", "")
            if name == "Temporal Extent Start Date" and value:
                start = value[:10]
            elif name == "Temporal Extent End Date" and value:
                end = value[:10]

        if start or end:
            return (start or end, end or start)

        # Fallback to published_date
        published_date = metadata.get("published_date")
        if not published_date:
            return None

        # published_date is ISO 8601, e.g. "2022-03-28T06:15:38Z"
        date_str = published_date[:10]
        return (date_str, date_str)

    def _write_metadata_geojson(self, folder, metadata):
        """Write GeoJSON from Figshare metadata.

        Priority:
        1. 'Geographic Coverage' custom field with full GeoJSON (USDA Ag Data Commons)
        2. Point geometry from lat/lon fields
        3. Null geometry with temporal-only properties

        Returns: path to created file, or None if no extractable metadata.
        """
        import json
        import os

        geo_coverage = self._parse_geo_coverage(metadata)
        geo = self._parse_geolocation(metadata)
        temporal = self._parse_temporal(metadata)

        properties = {
            "source": "Figshare metadata",
            "dataset_id": self.record_id,
            "title": metadata.get("title", ""),
        }

        if temporal:
            properties["start_time"] = temporal[0]
            properties["end_time"] = temporal[1]

        # Priority 1: Use full GeoJSON coverage if available
        if geo_coverage is not None:
            # Wrap raw geometries in a FeatureCollection
            if geo_coverage.get("type") == "FeatureCollection":
                geojson_data = geo_coverage
                # Inject temporal properties into all features
                for feature in geojson_data.get("features", []):
                    if temporal:
                        if feature.get("properties") is None:
                            feature["properties"] = {}
                        feature["properties"]["start_time"] = temporal[0]
                        feature["properties"]["end_time"] = temporal[1]
            elif geo_coverage.get("type") == "Feature":
                if temporal:
                    if geo_coverage.get("properties") is None:
                        geo_coverage["properties"] = {}
                    geo_coverage["properties"]["start_time"] = temporal[0]
                    geo_coverage["properties"]["end_time"] = temporal[1]
                geojson_data = {
                    "type": "FeatureCollection",
                    "features": [geo_coverage],
                }
            else:
                # Raw geometry type
                geojson_data = {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": geo_coverage,
                            "properties": properties,
                        }
                    ],
                }
        else:
            # Priority 2: Point from lat/lon, or null geometry
            if geo["lat"] is not None and geo["lon"] is not None:
                geometry = {
                    "type": "Point",
                    "coordinates": [geo["lon"], geo["lat"]],
                }
            else:
                geometry = None

            if geometry is None and temporal is None:
                self.log.debug(
                    f"Figshare item {self.record_id}: no geolocation or temporal coverage in metadata"
                )
                return None

            geojson_data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": geometry,
                        "properties": properties,
                    }
                ],
            }

        geojson_file = os.path.join(folder, f"figshare_{self.record_id}.geojson")
        with open(geojson_file, "w") as f:
            json.dump(geojson_data, f, indent=2)

        parts = []
        if geo_coverage is not None:
            parts.append("geographic coverage from GeoJSON")
        elif geo["lat"] is not None:
            parts.append(f"lat={geo['lat']}, lon={geo['lon']}")
        if temporal:
            parts.append(f"time={temporal[0]} to {temporal[1]}")
        self.log.info(
            f"Created GeoJSON metadata file for Figshare item {self.record_id} ({', '.join(parts)})"
        )
        return geojson_file

    def _download_metadata_only(self, folder):
        """Extract metadata from Figshare API (no data download)."""
        try:
            metadata = self._get_metadata()
        except Exception as e:
            self.log.warning(f"Failed to fetch Figshare metadata: {e}")
            return

        result = self._write_metadata_geojson(folder, metadata)
        if result is None:
            self.log.warning(
                f"Figshare item {self.record_id} has no geolocation or temporal "
                "coverage in metadata. Consider using download_data=True."
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
        from tqdm import tqdm

        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        self.throttle = throttle
        if not download_data:
            self._download_metadata_only(folder)
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
