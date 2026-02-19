"""
BAW (Bundesanstalt für Wasserbau) content provider for geoextent.

The BAW-Datenrepository is a research data repository for waterway engineering data,
built on InGrid Portal. It exposes a standard OGC CSW 2.0.2 endpoint with ISO 19115/19139
metadata.

Supported identifiers:
- DOI: 10.48437/* or https://doi.org/10.48437/*
- Landing page: https://datenrepository.baw.de/trefferanzeige?docuuid={UUID}
- Bare UUID (verified against CSW catalog)

Uses OWSLib for CSW access as recommended by OGC standards.
"""

import json
import logging
import os
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from owslib.csw import CatalogueServiceWeb
from xml.etree import ElementTree as ET

from geoextent.lib import helpfunctions as hf
from geoextent.lib.content_providers.providers import DoiProvider

logger = logging.getLogger("geoextent")

_CSW_URL = "https://datenrepository.baw.de/csw"
_LANDING_URL = "https://datenrepository.baw.de/trefferanzeige"
_DOWNLOAD_HOST = "https://dl.datenrepository.baw.de/"

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)

# GML 3.2 namespace used by BAW for temporal extents
_GML32_NS = "http://www.opengis.net/gml/3.2"


class BAW(DoiProvider):
    """Content provider for BAW-Datenrepository (Bundesanstalt für Wasserbau).

    Uses OGC CSW 2.0.2 with ISO 19115/19139 metadata via OWSLib.

    Identifier types:
    - DOI: 10.48437/* (resolves to landing page with UUID)
    - Landing page URL: https://datenrepository.baw.de/trefferanzeige?docuuid={UUID}
    - Bare UUID (verified against CSW catalog)
    """

    doi_prefixes = ("10.48437/",)

    @classmethod
    def provider_info(cls):
        return {
            "name": "BAW",
            "description": "BAW (Bundesanstalt für Wasserbau / Federal Waterways Engineering and Research Institute) Datenrepository provides research data for waterway engineering, including hydrodynamic models, sediment data, and measurement data. Metadata follows ISO 19115/19139 standards via CSW 2.0.2.",
            "website": "https://datenrepository.baw.de/",
            "supported_identifiers": [
                "https://datenrepository.baw.de/trefferanzeige?docuuid={uuid}",
                "https://doi.org/10.48437/{id}",
                "10.48437/{id}",
                "{uuid}",
            ],
            "doi_prefix": "10.48437",
            "examples": [
                "10.48437/7ca5ef-2e1287",
                "https://doi.org/10.48437/02.2023.K.0601.0001",
                "https://datenrepository.baw.de/trefferanzeige?docuuid=40936F66-3DD8-43D0-99AE-7CA5EF2E1287",
            ],
            "notes": "Uses OGC CSW 2.0.2 endpoint with ISO 19115/19139 metadata. Data files served from Apache directory listings on dl.datenrepository.baw.de.",
        }

    @property
    def supports_metadata_extraction(self):
        return True

    def __init__(self):
        super().__init__()
        self.host = {
            "hostname": [
                "https://datenrepository.baw.de",
                "http://datenrepository.baw.de",
                "datenrepository.baw.de",
                "https://dl.datenrepository.baw.de",
                "dl.datenrepository.baw.de",
            ]
        }
        self.name = "BAW"
        self.record_uuid = None
        self._csw = None

    def _get_csw(self):
        """Get or create a CatalogueServiceWeb connection."""
        if self._csw is None:
            self._csw = CatalogueServiceWeb(_CSW_URL, version="2.0.2", timeout=30)
        return self._csw

    def validate_provider(self, reference):
        """Validate if the reference is a supported BAW identifier.

        Args:
            reference (str): DOI, URL, or UUID

        Returns:
            bool: True if valid BAW reference
        """
        self.reference = reference

        # Check for BAW DOI pattern: 10.48437/*
        doi_pattern = r"(?:https?://(?:dx\.)?doi\.org/)?10\.48437/[\w.\-_]+"
        doi_match = re.match(doi_pattern, reference, re.IGNORECASE)
        if doi_match:
            if reference.startswith("http"):
                self.doi = reference.split("doi.org/")[-1]
            else:
                self.doi = reference

            logger.debug(f"Detected BAW DOI: {self.doi}")

            # Resolve DOI to get UUID from landing page
            try:
                resolved_url = self._resolve_doi_to_url(self.doi)
                logger.debug(f"Resolved DOI to: {resolved_url}")
                uuid_match = re.search(
                    r"docuuid=(" + _UUID_RE.pattern + r")",
                    resolved_url,
                    re.IGNORECASE,
                )
                if uuid_match:
                    self.record_uuid = uuid_match.group(1)
                    logger.debug(f"Extracted UUID from DOI: {self.record_uuid}")
                    return True
                else:
                    logger.warning(
                        f"Could not extract UUID from resolved DOI URL: {resolved_url}"
                    )
                    return False
            except Exception as e:
                logger.error(f"Failed to resolve BAW DOI {self.doi}: {e}")
                return False

        # Check for BAW landing page URL
        if "datenrepository.baw.de" in reference:
            uuid_match = re.search(
                r"docuuid=(" + _UUID_RE.pattern + r")",
                reference,
                re.IGNORECASE,
            )
            if uuid_match:
                self.record_uuid = uuid_match.group(1)
                logger.debug(
                    f"Extracted UUID from landing page URL: {self.record_uuid}"
                )
                return True

            # Check for UUID in URL path
            uuid_match = _UUID_RE.search(reference)
            if uuid_match:
                self.record_uuid = uuid_match.group(0)
                logger.debug(f"Extracted UUID from BAW URL: {self.record_uuid}")
                return True

        # Bare UUID — verify against CSW catalog
        if re.match(r"^" + _UUID_RE.pattern + r"$", reference, re.IGNORECASE):
            try:
                csw = self._get_csw()
                csw.getrecordbyid(
                    id=[reference],
                    outputschema="http://www.isotc211.org/2005/gmd",
                )
                if reference in csw.records:
                    self.record_uuid = reference
                    logger.debug(
                        "Verified bare UUID against BAW CSW: %s", self.record_uuid
                    )
                    return True
            except Exception:
                logger.debug("BAW CSW lookup failed for UUID %s", reference)
            return False

        return False

    def _resolve_doi_to_url(self, doi):
        """Resolve a BAW DOI to its landing page URL.

        Args:
            doi (str): BAW DOI (e.g., "10.48437/7ca5ef-2e1287")

        Returns:
            str: Resolved landing page URL
        """
        if not doi.startswith("http"):
            doi_url = f"https://doi.org/{doi}"
        else:
            doi_url = doi

        response = self.session.head(doi_url, allow_redirects=True, timeout=30)
        if response.status_code in [200, 302, 303]:
            return response.url
        else:
            raise Exception(f"DOI resolution returned status {response.status_code}")

    def _fetch_record(self):
        """Fetch CSW record metadata via OWSLib.

        Returns:
            dict: Extracted metadata with bbox, temporal_extent, distribution_urls, title
        """
        csw = self._get_csw()
        csw.getrecordbyid(
            id=[self.record_uuid],
            outputschema="http://www.isotc211.org/2005/gmd",
        )

        if self.record_uuid not in csw.records:
            raise Exception(f"BAW CSW record not found: {self.record_uuid}")

        rec = csw.records[self.record_uuid]
        metadata = {
            "title": None,
            "bbox": None,
            "temporal_extent": None,
            "distribution_urls": [],
        }

        # Extract identification metadata
        if rec.identification and len(rec.identification) > 0:
            ident = rec.identification[0]
            metadata["title"] = ident.title

            # Extract bounding box
            if ident.bbox:
                bb = ident.bbox
                try:
                    metadata["bbox"] = [
                        float(bb.minx),
                        float(bb.miny),
                        float(bb.maxx),
                        float(bb.maxy),
                    ]
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not parse BAW bounding box: {e}")

        # Extract temporal extent from raw XML (GML 3.2 namespace)
        if rec.xml:
            root = ET.fromstring(rec.xml)
            begin_elems = root.findall(f".//{{{_GML32_NS}}}beginPosition")
            end_elems = root.findall(f".//{{{_GML32_NS}}}endPosition")
            if begin_elems and end_elems:
                begin_text = begin_elems[0].text
                end_text = end_elems[0].text
                if begin_text and end_text:
                    # Strip timezone info for consistency (just date part)
                    metadata["temporal_extent"] = {
                        "start": begin_text.split("T")[0],
                        "end": end_text.split("T")[0],
                    }

        # Extract download URLs from distribution
        if rec.distribution and rec.distribution.online:
            for online in rec.distribution.online:
                if online.function == "download" and online.url:
                    metadata["distribution_urls"].append(online.url)

        return metadata

    def _crawl_directory_listing(self, url, max_depth=3):
        """Crawl an Apache directory listing to find downloadable files.

        Args:
            url (str): URL of the directory listing
            max_depth (int): Maximum recursion depth

        Returns:
            list[dict]: List of file info dicts with 'url', 'name', 'size' keys
        """
        if max_depth <= 0:
            return []

        files = []
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            for link in soup.find_all("a"):
                href = link.get("href")
                if not href or href.startswith("?") or href.startswith("/"):
                    continue

                full_url = urljoin(url if url.endswith("/") else url + "/", href)

                if href.endswith("/"):
                    # Subdirectory — recurse
                    files.extend(self._crawl_directory_listing(full_url, max_depth - 1))
                else:
                    files.append(
                        {
                            "url": full_url,
                            "name": href,
                            "size": 0,
                        }
                    )

        except Exception as e:
            logger.warning(f"Error crawling directory {url}: {e}")

        return files

    def _create_metadata_geojson(self, metadata, target_dir):
        """Create a GeoJSON file from metadata.

        Args:
            metadata (dict): Extracted metadata
            target_dir (str): Target directory
        """
        if not metadata.get("bbox"):
            logger.warning("No bounding box in BAW metadata, cannot create GeoJSON")
            return

        minx, miny, maxx, maxy = metadata["bbox"]

        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [minx, miny],
                                [maxx, miny],
                                [maxx, maxy],
                                [minx, maxy],
                                [minx, miny],
                            ]
                        ],
                    },
                    "properties": {
                        "source": "BAW",
                        "dataset_id": self.record_uuid,
                        "title": metadata.get("title", ""),
                    },
                }
            ],
        }

        if metadata.get("temporal_extent"):
            geojson_data["features"][0]["properties"]["temporal_extent"] = metadata[
                "temporal_extent"
            ]

        geojson_file = os.path.join(target_dir, f"baw_{self.record_uuid}.geojson")
        with open(geojson_file, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Created BAW GeoJSON metadata file: {geojson_file}")

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
        """Download data from BAW-Datenrepository.

        Args:
            folder (str): Target directory for downloads
            throttle (bool): Whether to throttle requests
            download_data (bool): Whether to download actual data files
            show_progress (bool): Whether to show progress bars
            max_size_bytes (int): Maximum total download size in bytes
            max_download_method (str): Method for selecting files when size limit applies
            max_download_method_seed (int): Random seed for sampling methods
            download_skip_nogeo (bool): Skip non-geospatial files
            download_skip_nogeo_exts (set): Additional geospatial file extensions
            max_download_workers (int): Maximum number of parallel download workers

        Returns:
            str: Path to downloaded data directory
        """
        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        logger.info(f"Downloading from BAW-Datenrepository: {self.reference}")

        if not self.record_uuid:
            raise Exception("No record UUID available for download")

        metadata = self._fetch_record()
        logger.debug(f"BAW metadata: {metadata}")

        folder_name = f"baw_{self.record_uuid}"
        download_dir = os.path.join(folder, folder_name)
        os.makedirs(download_dir, exist_ok=True)

        if not download_data:
            logger.info("Creating BAW metadata-only GeoJSON file")
            self._create_metadata_geojson(metadata, download_dir)
            return download_dir

        # Download data files
        if metadata.get("distribution_urls"):
            logger.info(f"Found {len(metadata['distribution_urls'])} distribution URLs")

            # Crawl directory listings to find actual files
            all_files = []
            for dist_url in metadata["distribution_urls"]:
                if dist_url.rstrip("/").endswith(
                    (
                        ".zip",
                        ".tif",
                        ".geotiff",
                        ".csv",
                        ".dat",
                        ".txt",
                        ".nc",
                        ".geojson",
                        ".shp",
                        ".gml",
                        ".gpkg",
                    )
                ):
                    # Direct file URL
                    all_files.append(
                        {
                            "url": dist_url,
                            "name": os.path.basename(dist_url.rstrip("/")),
                            "size": 0,
                        }
                    )
                else:
                    # Likely a directory listing
                    all_files.extend(self._crawl_directory_listing(dist_url))

            if not all_files:
                logger.warning("No downloadable files found in distribution URLs")
                self._create_metadata_geojson(metadata, download_dir)
                return download_dir

            # Filter geospatial files if requested
            if download_skip_nogeo:
                filtered_files = self._filter_geospatial_files(
                    all_files,
                    skip_non_geospatial=True,
                    additional_extensions=download_skip_nogeo_exts,
                )
            else:
                filtered_files = all_files

            # Apply size filtering
            if max_size_bytes is not None:
                # Get file sizes via HEAD requests
                for f in filtered_files:
                    if f["size"] == 0:
                        try:
                            head = self.session.head(f["url"], timeout=10)
                            f["size"] = int(head.headers.get("content-length", 0))
                        except Exception:
                            pass

                selected_files, total_size, skipped = hf.filter_files_by_size(
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

                if not selected_files:
                    logger.warning("No files can be downloaded within the size limit")
                    self._create_metadata_geojson(metadata, download_dir)
                    return download_dir

                logger.info(
                    f"Size limit: downloading {len(selected_files)} of "
                    f"{len(filtered_files)} files ({total_size:,} bytes)"
                )
                filtered_files = selected_files

            # Download files
            if filtered_files:
                self._download_files_batch(
                    filtered_files,
                    download_dir,
                    show_progress=show_progress,
                    max_workers=max_download_workers,
                )
        else:
            logger.warning("No distribution URLs found in BAW metadata")
            self._create_metadata_geojson(metadata, download_dir)

        return download_dir
