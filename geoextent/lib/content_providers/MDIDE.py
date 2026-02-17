"""
MDI-DE (Marine Daten-Infrastruktur Deutschland) content provider for geoextent.

MDI-DE is a distributed spatial data infrastructure for German marine and coastal data.
Its metadata catalog NOKIS (North Sea and Baltic Sea Coastal Information System) uses
CSW 2.0.2 with ISO 19115/19139 metadata. Data is served via WFS endpoints at various
GeoServer instances.

Supported identifiers:
- Landing page: https://nokis.mdi-de-dienste.org/trefferanzeige?docuuid={UUID}
- Bare UUID (verified against NOKIS CSW catalog)

Three extraction phases:
- Phase 1: Metadata-only extraction from CSW records (bbox + temporal)
- Phase 2: Direct download of pre-built WFS GetFeature URLs found in metadata
- Phase 3: WFS-based download using OWSLib WebFeatureService when only endpoint URLs exist
"""

import json
import logging
import os
import re
from urllib.parse import parse_qs, urlparse

from owslib.csw import CatalogueServiceWeb
from owslib.wfs import WebFeatureService
from xml.etree import ElementTree as ET

from geoextent.lib import helpfunctions as hf
from geoextent.lib.content_providers.providers import DoiProvider

logger = logging.getLogger("geoextent")

_CSW_URL = "https://nokis.mdi-de-dienste.org/csw"
_LANDING_URL = "https://nokis.mdi-de-dienste.org/trefferanzeige"

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)

# GML namespaces used by NOKIS for temporal extents
_GML_NS = "http://www.opengis.net/gml"
_GML32_NS = "http://www.opengis.net/gml/3.2"

# Default max features to request from WFS (prevent unbounded downloads)
_WFS_MAX_FEATURES = 100000

# Preferred WFS output formats in order of preference
_WFS_FORMAT_PREFERENCE = [
    "SHAPE-ZIP",
    "shape-zip",
    "application/json",
    "json",
    "csv",
    "GML",
    "application/gml+xml; version=3.2",
    "text/xml; subtype=gml/3.2.1",
    "text/xml; subtype=gml/3.1.1",
]

# File extensions for WFS output formats
_FORMAT_EXTENSIONS = {
    "SHAPE-ZIP": ".zip",
    "shape-zip": ".zip",
    "application/json": ".geojson",
    "json": ".geojson",
    "csv": ".csv",
    "GML": ".gml",
    "application/gml+xml; version=3.2": ".gml",
    "text/xml; subtype=gml/3.2.1": ".gml",
    "text/xml; subtype=gml/3.1.1": ".gml",
}


class MDIDE(DoiProvider):
    """Content provider for MDI-DE (Marine Daten-Infrastruktur Deutschland).

    Uses OGC CSW 2.0.2 via NOKIS catalog with ISO 19115/19139 metadata,
    plus WFS-based data download from distributed GeoServer instances.

    Identifier types:
    - Landing page URL: https://nokis.mdi-de-dienste.org/trefferanzeige?docuuid={UUID}
    - Bare UUID (verified against NOKIS CSW catalog)
    """

    doi_prefixes = ()  # MDI-DE has no DOIs

    @classmethod
    def provider_info(cls):
        return {
            "name": "MDI-DE",
            "description": (
                "MDI-DE (Marine Daten-Infrastruktur Deutschland / Marine Data "
                "Infrastructure Germany) is a distributed spatial data infrastructure "
                "for German marine and coastal data. The NOKIS catalog provides "
                "ISO 19115/19139 metadata via CSW 2.0.2, with data served via WFS "
                "endpoints at various GeoServer instances."
            ),
            "website": "https://www.mdi-de.org/",
            "supported_identifiers": [
                "https://nokis.mdi-de-dienste.org/trefferanzeige?docuuid={uuid}",
                "{uuid}",
            ],
            "examples": [
                "https://nokis.mdi-de-dienste.org/trefferanzeige?docuuid=00100e9d-7838-4563-9dd7-2570b0d932cb",
                "c7d748c9-e12f-4038-a556-b1698eb4033e",
            ],
            "notes": (
                "Uses OGC CSW 2.0.2 endpoint (NOKIS) with ISO 19115/19139 metadata. "
                "Data files are served via WFS endpoints at distributed GeoServer instances. "
                "Supports metadata-only extraction (Phase 1), direct download of pre-built "
                "WFS GetFeature URLs (Phase 2), and WFS-based download via OWSLib (Phase 3)."
            ),
        }

    @property
    def supports_metadata_extraction(self):
        return True

    def __init__(self):
        super().__init__()
        self.host = {
            "hostname": [
                "https://nokis.mdi-de-dienste.org",
                "http://nokis.mdi-de-dienste.org",
                "nokis.mdi-de-dienste.org",
            ]
        }
        self.name = "MDI-DE"
        self.record_uuid = None
        self._csw = None

    def _get_csw(self):
        """Get or create a CatalogueServiceWeb connection."""
        if self._csw is None:
            self._csw = CatalogueServiceWeb(_CSW_URL, version="2.0.2", timeout=30)
        return self._csw

    def validate_provider(self, reference):
        """Validate if the reference is a supported MDI-DE identifier.

        Args:
            reference (str): URL or UUID

        Returns:
            bool: True if valid MDI-DE reference
        """
        self.reference = reference

        # Check for NOKIS landing page URL
        if "nokis.mdi-de-dienste.org" in reference:
            uuid_match = re.search(
                r"docuuid=(" + _UUID_RE.pattern + r")",
                reference,
                re.IGNORECASE,
            )
            if uuid_match:
                self.record_uuid = uuid_match.group(1)
                logger.debug(
                    "Extracted UUID from MDI-DE landing page URL: %s",
                    self.record_uuid,
                )
                return True

            # Check for UUID anywhere in the URL
            uuid_match = _UUID_RE.search(reference)
            if uuid_match:
                self.record_uuid = uuid_match.group(0)
                logger.debug("Extracted UUID from MDI-DE URL: %s", self.record_uuid)
                return True

        # Bare UUID — verify against NOKIS CSW catalog
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
                        "Verified bare UUID against MDI-DE CSW: %s",
                        self.record_uuid,
                    )
                    return True
            except Exception:
                logger.debug("MDI-DE CSW lookup failed for UUID %s", reference)
            return False

        return False

    def _fetch_record(self):
        """Fetch CSW record metadata via OWSLib.

        Returns:
            dict: Extracted metadata with bbox, temporal_extent, online_resources, title
        """
        csw = self._get_csw()
        csw.getrecordbyid(
            id=[self.record_uuid],
            outputschema="http://www.isotc211.org/2005/gmd",
        )

        if self.record_uuid not in csw.records:
            raise Exception(f"MDI-DE CSW record not found: {self.record_uuid}")

        rec = csw.records[self.record_uuid]
        metadata = {
            "title": None,
            "bbox": None,
            "temporal_extent": None,
            "online_resources": [],
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
                    logger.warning(f"Could not parse MDI-DE bounding box: {e}")

        # Extract temporal extent from raw XML
        # NOKIS uses both GML 3.2 and regular GML namespaces
        if rec.xml:
            root = ET.fromstring(rec.xml)

            # Try GML 3.2 first (more common in NOKIS)
            begin_elems = root.findall(f".//{{{_GML32_NS}}}beginPosition")
            end_elems = root.findall(f".//{{{_GML32_NS}}}endPosition")

            # Fall back to regular GML namespace
            if not begin_elems or not end_elems:
                begin_elems = root.findall(f".//{{{_GML_NS}}}beginPosition")
                end_elems = root.findall(f".//{{{_GML_NS}}}endPosition")

            if begin_elems and end_elems:
                begin_text = begin_elems[0].text
                end_text = end_elems[0].text
                if begin_text and end_text:
                    metadata["temporal_extent"] = {
                        "start": begin_text.split("T")[0],
                        "end": end_text.split("T")[0],
                    }

            # Extract online resources from raw XML for richer info
            # (OWSLib online resources sometimes miss the name attribute)
            gmd_ns = "http://www.isotc211.org/2005/gmd"
            gco_ns = "http://www.isotc211.org/2005/gco"
            online_elems = root.findall(f".//{{{gmd_ns}}}CI_OnlineResource")
            for elem in online_elems:
                url_elem = elem.find(f"{{{gmd_ns}}}linkage/{{{gmd_ns}}}URL")
                name_elem = elem.find(f"{{{gmd_ns}}}name/{{{gco_ns}}}CharacterString")
                protocol_elem = elem.find(
                    f"{{{gmd_ns}}}protocol/{{{gco_ns}}}CharacterString"
                )
                function_elem = elem.find(
                    f"{{{gmd_ns}}}function/{{{gmd_ns}}}CI_OnLineFunctionCode"
                )

                resource = {
                    "url": (
                        url_elem.text
                        if url_elem is not None and url_elem.text
                        else None
                    ),
                    "name": (
                        name_elem.text
                        if name_elem is not None and name_elem.text
                        else None
                    ),
                    "protocol": (
                        protocol_elem.text
                        if protocol_elem is not None and protocol_elem.text
                        else None
                    ),
                    "function": (
                        function_elem.get("codeListValue")
                        if function_elem is not None
                        else None
                    ),
                }

                if resource["url"]:
                    metadata["online_resources"].append(resource)

        return metadata

    def _classify_online_resources(self, online_resources):
        """Classify online resources into download categories.

        Args:
            online_resources (list): List of online resource dicts

        Returns:
            dict: {'direct_download': [...], 'wfs_endpoint': [...], 'other': [...]}
        """
        classified = {
            "direct_download": [],
            "wfs_endpoint": [],
            "other": [],
        }

        for resource in online_resources:
            url = resource.get("url", "")
            if not url:
                continue

            url_lower = url.lower()

            # Phase 2: Pre-built WFS GetFeature URLs (direct download)
            if "request=getfeature" in url_lower:
                classified["direct_download"].append(resource)
            # Phase 3: WFS endpoint URLs (need to construct GetFeature requests)
            elif "service=wfs" in url_lower or "/wfs" in url_lower:
                classified["wfs_endpoint"].append(resource)
            else:
                classified["other"].append(resource)

        return classified

    def _download_direct_urls(self, resources, download_dir, show_progress=True):
        """Download pre-built WFS GetFeature URLs (Phase 2).

        Args:
            resources (list): List of online resource dicts with pre-built URLs
            download_dir (str): Target directory
            show_progress (bool): Whether to show progress

        Returns:
            int: Number of files downloaded
        """
        file_list = []
        for resource in resources:
            url = resource["url"]
            parsed = urlparse(url)
            params = parse_qs(parsed.query, keep_blank_values=True)

            # Infer filename from typeName and outputFormat
            type_name = params.get("typeName", params.get("typename", ["unknown"]))[0]
            output_format = params.get(
                "outputFormat", params.get("outputformat", ["gml"])
            )[0]

            # Clean up type name for filename
            safe_type = type_name.replace(":", "_").replace("/", "_")

            # Determine file extension from output format
            fmt_lower = output_format.lower()
            if "shape" in fmt_lower or "zip" in fmt_lower:
                ext = ".zip"
            elif "json" in fmt_lower:
                ext = ".geojson"
            elif "csv" in fmt_lower:
                ext = ".csv"
            else:
                ext = ".gml"

            filename = f"{safe_type}{ext}"

            file_list.append(
                {
                    "url": url,
                    "name": filename,
                    "size": 0,
                }
            )

        if file_list:
            logger.info(f"Downloading {len(file_list)} direct WFS GetFeature URLs")
            self._download_files_batch(
                file_list,
                download_dir,
                show_progress=show_progress,
                max_workers=4,
            )

        return len(file_list)

    def _download_wfs_features(self, wfs_resources, download_dir, show_progress=True):
        """Download features via WFS endpoints using OWSLib (Phase 3).

        Args:
            wfs_resources (list): List of WFS endpoint resource dicts
            download_dir (str): Target directory
            show_progress (bool): Whether to show progress

        Returns:
            int: Number of files downloaded
        """
        downloaded = 0

        # Group resources by base WFS URL
        seen_endpoints = set()

        for resource in wfs_resources:
            url = resource["url"]
            parsed = urlparse(url)
            # Strip query params to get base WFS URL
            base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

            if base_url in seen_endpoints:
                continue
            seen_endpoints.add(base_url)

            try:
                logger.info(f"Connecting to WFS endpoint: {base_url}")

                # Try WFS 2.0.0 first, fall back to 1.1.0
                wfs = None
                wfs_version = None
                for version in ["2.0.0", "1.1.0"]:
                    try:
                        wfs = WebFeatureService(
                            url=base_url, version=version, timeout=60
                        )
                        wfs_version = version
                        logger.debug(f"Connected to WFS {version} at {base_url}")
                        break
                    except Exception as e:
                        logger.debug(f"WFS {version} failed for {base_url}: {e}")
                        continue

                if wfs is None:
                    logger.warning(f"Could not connect to WFS at {base_url}")
                    continue

                # Determine which layers to download
                available_types = list(wfs.contents.keys())
                logger.debug(
                    f"WFS has {len(available_types)} feature types: {available_types}"
                )

                # Try to determine target layer from resource name or URL
                target_layers = []
                resource_name = resource.get("name")
                if resource_name and resource_name in available_types:
                    target_layers = [resource_name]
                else:
                    # Check URL params for typeName
                    params = parse_qs(parsed.query, keep_blank_values=True)
                    type_param = params.get("typeName", params.get("typename", []))
                    if type_param:
                        requested = type_param[0].split(",")
                        target_layers = [t for t in requested if t in available_types]

                if not target_layers:
                    # Use all available feature types
                    target_layers = available_types

                # Choose output format
                output_format = None
                for fmt in _WFS_FORMAT_PREFERENCE:
                    for layer in target_layers:
                        layer_meta = wfs.contents.get(layer)
                        if layer_meta:
                            available_formats = getattr(layer_meta, "outputFormats", [])
                            if fmt in available_formats:
                                output_format = fmt
                                break
                    if output_format:
                        break

                # Fall back: try formats from GetCapabilities
                if output_format is None:
                    get_feature_op = None
                    for op in wfs.operations:
                        if op.name == "GetFeature":
                            get_feature_op = op
                            break

                    if get_feature_op:
                        op_formats = get_feature_op.parameters.get("outputFormat", {})
                        format_values = (
                            op_formats.get("values", [])
                            if isinstance(op_formats, dict)
                            else op_formats
                        )
                        for fmt in _WFS_FORMAT_PREFERENCE:
                            if fmt in format_values:
                                output_format = fmt
                                break

                if output_format is None:
                    output_format = "GML"

                ext = _FORMAT_EXTENSIONS.get(output_format, ".gml")

                # Download each target layer
                for layer in target_layers:
                    try:
                        safe_layer = layer.replace(":", "_").replace("/", "_")
                        filename = f"wfs_{safe_layer}{ext}"
                        filepath = os.path.join(download_dir, filename)

                        logger.info(f"Downloading WFS layer {layer} as {output_format}")

                        # Build getfeature kwargs
                        kwargs = {
                            "typename": [layer],
                            "outputFormat": output_format,
                        }
                        # OWSLib uses 'maxfeatures' for both WFS versions
                        # (translates to 'count' in WFS 2.0.0 requests internally)
                        kwargs["maxfeatures"] = str(_WFS_MAX_FEATURES)

                        response = wfs.getfeature(**kwargs)

                        with open(filepath, "wb") as f:
                            f.write(response.read())

                        file_size = os.path.getsize(filepath)
                        logger.info(
                            f"Downloaded WFS layer {layer}: {file_size:,} bytes"
                        )
                        downloaded += 1

                    except Exception as e:
                        logger.warning(f"Failed to download WFS layer {layer}: {e}")
                        continue

            except Exception as e:
                logger.warning(f"Failed to process WFS endpoint {base_url}: {e}")
                continue

        return downloaded

    def _create_metadata_geojson(self, metadata, target_dir):
        """Create a GeoJSON file from CSW metadata (Phase 1).

        Args:
            metadata (dict): Extracted metadata
            target_dir (str): Target directory
        """
        if not metadata.get("bbox"):
            logger.warning("No bounding box in MDI-DE metadata, cannot create GeoJSON")
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
                        "source": "MDI-DE",
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

        geojson_file = os.path.join(target_dir, f"mdide_{self.record_uuid}.geojson")
        with open(geojson_file, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Created MDI-DE GeoJSON metadata file: {geojson_file}")

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
        """Download data from MDI-DE.

        Orchestrates the three extraction phases:
        1. Metadata-only: create GeoJSON from CSW bbox
        2. Direct download: pre-built WFS GetFeature URLs
        3. WFS download: construct GetFeature requests via OWSLib

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

        logger.info(f"Downloading from MDI-DE: {self.reference}")

        if not self.record_uuid:
            raise Exception("No record UUID available for download")

        metadata = self._fetch_record()
        logger.debug(f"MDI-DE metadata: {metadata}")

        folder_name = f"mdide_{self.record_uuid}"
        download_dir = os.path.join(folder, folder_name)
        os.makedirs(download_dir, exist_ok=True)

        if not download_data:
            # Phase 1: metadata-only GeoJSON
            logger.info("Creating MDI-DE metadata-only GeoJSON file")
            self._create_metadata_geojson(metadata, download_dir)
            return download_dir

        # Classify online resources
        classified = self._classify_online_resources(
            metadata.get("online_resources", [])
        )

        total_downloaded = 0

        # Phase 2: Try direct download URLs first
        if classified["direct_download"]:
            logger.info(
                f"Phase 2: {len(classified['direct_download'])} direct download URLs"
            )
            total_downloaded += self._download_direct_urls(
                classified["direct_download"],
                download_dir,
                show_progress=show_progress,
            )

        # Phase 3: Try WFS endpoints
        if classified["wfs_endpoint"]:
            logger.info(f"Phase 3: {len(classified['wfs_endpoint'])} WFS endpoints")
            total_downloaded += self._download_wfs_features(
                classified["wfs_endpoint"],
                download_dir,
                show_progress=show_progress,
            )

        # Fall back to metadata GeoJSON if no data was downloaded
        if total_downloaded == 0:
            logger.info("No data files downloaded, falling back to metadata GeoJSON")
            self._create_metadata_geojson(metadata, download_dir)

        return download_dir
