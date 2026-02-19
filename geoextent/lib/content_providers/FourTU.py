from requests import HTTPError
from .providers import DoiProvider
from ..extent import *
from .. import helpfunctions as hf


class FourTU(DoiProvider):
    doi_prefixes = ("10.4121/",)

    @classmethod
    def provider_info(cls):
        return {
            "name": "4TU.ResearchData",
            "description": "4TU.ResearchData is a Dutch national data repository for science, engineering, and design. Hosted by the 4TU Federation of Dutch technical universities, it assigns DOIs and provides long-term data archiving.",
            "website": "https://data.4tu.nl/",
            "supported_identifiers": [
                "https://data.4tu.nl/datasets/{uuid}/{version}",
                "https://data.4tu.nl/articles/{article_id}",
                "https://doi.org/10.4121/{dataset_id}",
                "10.4121/{dataset_id}",
            ],
            "doi_prefix": "10.4121",
            "examples": [
                "https://data.4tu.nl/datasets/3035126d-ee51-4dbd-a187-5f6b0be85e9f/1",
                "10.4121/3035126d-ee51-4dbd-a187-5f6b0be85e9f",
            ],
            "notes": "Supports metadata-only extraction (geolocation from custom_fields, temporal from published_date). Uses Djehuty platform (https://djehuty.4tu.nl) with Figshare-compatible v2 API.",
        }

    def __init__(self):
        super().__init__()
        self.log = logging.getLogger("geoextent")
        self.host = {
            "hostname": [
                "https://data.4tu.nl/articles/",
                "https://data.4tu.nl/datasets/",
            ],
            "api": "https://data.4tu.nl/v2/articles/",
        }
        self.reference = None
        self.record_id = None
        self.name = "4TU.ResearchData"
        self.throttle = False

    @property
    def supports_metadata_extraction(self):
        return True

    def validate_provider(self, reference):
        import re

        self.reference = reference
        url = self.get_url

        if any([url.startswith(p) for p in self.host["hostname"]]):
            # Handle 4TU URL patterns:
            # https://data.4tu.nl/articles/_/RECORD_ID
            # https://data.4tu.nl/articles/_/RECORD_ID/VERSION
            # https://data.4tu.nl/articles/dataset/TITLE/RECORD_ID
            # https://data.4tu.nl/articles/dataset/TITLE/RECORD_ID/VERSION
            # https://data.4tu.nl/datasets/UUID
            # https://data.4tu.nl/datasets/UUID/VERSION

            # Try UUID pattern first (new-style URLs)
            uuid_pattern = re.compile(
                r"/datasets/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:/\d+)?/?$"
            )
            match = uuid_pattern.search(url)
            if match:
                self.record_id = match.group(1)
                return True

            # Try numeric ID pattern (old-style /articles/_/ID or /articles/dataset/title/ID)
            numeric_pattern = re.compile(r"/(\d+)(?:/\d+)?/?$")
            match = numeric_pattern.search(url)
            if match:
                self.record_id = match.group(1)
                return True

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
                m = (
                    "The 4TU.ResearchData item with id "
                    + str(self.record_id)
                    + " does not exist"
                )
                self.log.warning(m)
                raise HTTPError(m)
        else:
            raise ValueError("Invalid content provider")

    def _parse_custom_fields(self, metadata):
        """Parse geolocation and temporal coverage from 4TU custom_fields.

        4TU stores metadata in the Figshare v2 API custom_fields array:
        - "Geolocation Latitude" (string, e.g. "51.050407")
        - "Geolocation Longitude" (string, e.g. "13.737262")
        - "Geolocation" (place name, optional)
        - "Time coverage" (string, e.g. "2025-05-21 to 2025-06-17")

        Returns:
            dict with keys 'lat', 'lon', 'time_coverage' (any may be None)
        """
        custom_fields = metadata.get("custom_fields", [])
        lat = lon = None
        time_coverage = None

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
            elif name == "Time coverage":
                time_coverage = value

        return {"lat": lat, "lon": lon, "time_coverage": time_coverage}

    def _parse_time_coverage(self, time_coverage):
        """Parse '2025-05-21 to 2025-06-17' into (start, end) tuple or None."""
        if not time_coverage:
            return None
        parts = [p.strip() for p in time_coverage.split(" to ")]
        if len(parts) == 2:
            return (parts[0], parts[1])
        elif len(parts) == 1:
            return (parts[0], parts[0])
        return None

    def _write_metadata_geojson(self, folder, metadata, filename_suffix=""):
        """Write a GeoJSON file from 4TU custom_fields metadata.

        Args:
            folder: Target directory
            metadata: Record metadata from _get_metadata()
            filename_suffix: Optional suffix for the filename (e.g. "_temporal")
        """
        import json
        import os

        parsed = self._parse_custom_fields(metadata)

        properties = {
            "source": "4TU.ResearchData metadata",
            "dataset_id": self.record_id,
            "title": metadata.get("title", ""),
        }

        # Add temporal coverage
        temporal = self._parse_time_coverage(parsed["time_coverage"])
        if temporal:
            properties["start_time"] = temporal[0]
            properties["end_time"] = temporal[1]

        # Geometry: Point if coordinates available, null otherwise
        if parsed["lat"] is not None and parsed["lon"] is not None:
            geometry = {
                "type": "Point",
                "coordinates": [parsed["lon"], parsed["lat"]],
            }
        else:
            geometry = None

        if geometry is None and temporal is None:
            self.log.debug(
                f"4TU item {self.record_id}: no geolocation or temporal coverage in metadata"
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

        geojson_file = os.path.join(
            folder, f"fourtu_{self.record_id}{filename_suffix}.geojson"
        )
        with open(geojson_file, "w") as f:
            json.dump(geojson_data, f, indent=2)

        parts = []
        if parsed["lat"] is not None:
            parts.append(f"lat={parsed['lat']}, lon={parsed['lon']}")
        if temporal:
            parts.append(f"time={temporal[0]} to {temporal[1]}")
        self.log.info(
            f"Created GeoJSON metadata file for 4TU item {self.record_id} ({', '.join(parts)})"
        )
        return geojson_file

    def _download_metadata_only(self, folder):
        """Extract geolocation and temporal coverage from 4TU metadata (no data download)."""
        try:
            metadata = self._get_metadata()
        except Exception as e:
            self.log.warning(f"Failed to fetch 4TU metadata: {e}")
            return

        result = self._write_metadata_geojson(folder, metadata)
        if result is None:
            self.log.warning(
                f"4TU.ResearchData item {self.record_id} has no geolocation or temporal "
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

        self.log.debug(
            "Downloading 4TU.ResearchData item id: {} ".format(self.record_id)
        )
        try:
            metadata = self._get_metadata()
            files = metadata.get("files", [])

            if not files:
                self.log.warning(
                    f"No files found in 4TU.ResearchData item {self.record_id}"
                )
                return

            file_info = []
            total_size = 0
            if show_progress:
                metadata_pbar = tqdm(
                    total=len(files),
                    desc=f"Processing 4TU metadata for {self.record_id}",
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
                    f"No downloadable files found in 4TU.ResearchData item {self.record_id}"
                )
                return

            filtered_files = self._filter_geospatial_files(
                file_info,
                skip_non_geospatial=download_skip_nogeo,
                additional_extensions=download_skip_nogeo_exts,
            )

            if not filtered_files:
                self.log.warning(f"No files selected for download after filtering")
                return

            # Apply size filtering if specified
            if max_size_bytes is not None:
                filtered_files, filtered_total_size, skipped_files = (
                    hf.filter_files_by_size(
                        filtered_files,
                        max_size_bytes,
                        max_download_method,
                        max_download_method_seed,
                        provider_name=(
                            self.name
                            if getattr(self, "_download_size_soft_limit", False)
                            else None
                        ),
                    )
                )
                if not filtered_files:
                    self.log.warning("No files can be downloaded within the size limit")
                    return

            filtered_total_size = sum(f.get("size", 0) for f in filtered_files)

            self.log.info(
                f"Starting download of {len(filtered_files)} files from 4TU.ResearchData item {self.record_id} ({filtered_total_size:,} bytes total)"
            )

            self._download_files_batch(
                filtered_files,
                folder,
                show_progress=show_progress,
                max_workers=max_download_workers,
            )

            self.log.info(
                f"Downloaded {len(filtered_files)} files from 4TU.ResearchData item {self.record_id} ({filtered_total_size} bytes total)"
            )

            # Write temporal metadata sidecar from custom_fields.
            # Data files (GeoJSON, GeoPackage) often lack temporal columns;
            # the API's "Time coverage" custom field provides a fallback.
            # The sidecar filename (_metadata_temporal) appears in details
            # for provenance transparency.
            self._write_metadata_geojson(
                folder, metadata, filename_suffix="_metadata_temporal"
            )

        except ValueError as e:
            raise Exception(e)
