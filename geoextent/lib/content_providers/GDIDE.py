"""
GDI-DE (Geodateninfrastruktur Deutschland) content provider for geoextent.

GDI-DE is the national spatial data infrastructure for Germany, aggregating metadata
from federal, state, and municipal agencies (BKG, DWD, DLR, etc.) with 771,000+ records.
Its catalogue uses a standard OGC CSW 2.0.2 endpoint with ISO 19115/19139 metadata.

Supported identifiers:
- Landing page: https://www.geoportal.de/Metadata/{UUID}
- CSW URL: https://gdk.gdi-de.org/gdi-de/srv/eng/csw?...Id={UUID}
- Bare UUID (verified against GDI-DE CSW catalog)

This is a metadata-only provider — GDI-DE is a catalogue pointing to external
WMS/WFS/Atom services. Data download would require provider-specific logic per agency.
"""

import json
import logging
import os
import re
from xml.etree import ElementTree as ET

from owslib.csw import CatalogueServiceWeb

from geoextent.lib import helpfunctions as hf
from geoextent.lib.content_providers.providers import DoiProvider

logger = logging.getLogger("geoextent")

_CSW_URL = "https://gdk.gdi-de.org/gdi-de/srv/eng/csw"

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)

# GML namespaces used by GDI-DE for temporal extents
_GML_NS = "http://www.opengis.net/gml"
_GML32_NS = "http://www.opengis.net/gml/3.2"


class GDIDE(DoiProvider):
    """Content provider for GDI-DE (Geodateninfrastruktur Deutschland).

    Uses OGC CSW 2.0.2 with ISO 19115/19139 metadata via OWSLib.
    Metadata-only provider — no data download support.

    Identifier types:
    - Landing page URL: https://www.geoportal.de/Metadata/{UUID}
    - CSW endpoint URL: https://gdk.gdi-de.org/gdi-de/srv/eng/csw?...Id={UUID}
    - Bare UUID (verified against GDI-DE CSW catalog)
    """

    doi_prefixes = ()  # GDI-DE has no DOIs

    @classmethod
    def provider_info(cls):
        return {
            "name": "GDI-DE",
            "description": (
                "GDI-DE (Geodateninfrastruktur Deutschland / Spatial Data "
                "Infrastructure Germany) is the national spatial data "
                "infrastructure catalogue with 771,000+ records, aggregating "
                "metadata from German federal, state, and municipal agencies "
                "(BKG, DWD, DLR, etc.)."
            ),
            "website": "https://www.geoportal.de/",
            "supported_identifiers": [
                "https://www.geoportal.de/Metadata/{uuid}",
                "https://gdk.gdi-de.org/gdi-de/srv/eng/csw?...Id={uuid}",
                "{uuid}",
            ],
            "examples": [
                "https://www.geoportal.de/Metadata/75987CE0-AA66-4445-AC44-068B98390E89",
                "75987CE0-AA66-4445-AC44-068B98390E89",
            ],
            "notes": (
                "Uses OGC CSW 2.0.2 endpoint with ISO 19115/19139 metadata. "
                "Metadata-only provider — GDI-DE is a catalogue pointing to "
                "external WMS/WFS/Atom services."
            ),
        }

    @property
    def supports_metadata_extraction(self):
        return True

    def __init__(self):
        super().__init__()
        self.host = {
            "hostname": [
                "https://www.geoportal.de",
                "http://www.geoportal.de",
                "www.geoportal.de",
                "https://geoportal.de",
                "geoportal.de",
                "https://gdk.gdi-de.org",
                "http://gdk.gdi-de.org",
                "gdk.gdi-de.org",
            ]
        }
        self.name = "GDI-DE"
        self.record_uuid = None
        self._csw = None

    def _get_csw(self):
        """Get or create a CatalogueServiceWeb connection."""
        if self._csw is None:
            self._csw = CatalogueServiceWeb(_CSW_URL, version="2.0.2", timeout=30)
        return self._csw

    def validate_provider(self, reference):
        """Validate if the reference is a supported GDI-DE identifier.

        Args:
            reference (str): URL or UUID

        Returns:
            bool: True if valid GDI-DE reference
        """
        self.reference = reference

        # Check for geoportal.de landing page URL
        # Pattern: https://www.geoportal.de/Metadata/{UUID}
        if "geoportal.de" in reference:
            uuid_match = _UUID_RE.search(reference)
            if uuid_match:
                self.record_uuid = uuid_match.group(0)
                logger.debug(
                    "Extracted UUID from GDI-DE geoportal.de URL: %s",
                    self.record_uuid,
                )
                return True

        # Check for gdk.gdi-de.org CSW endpoint URL
        if "gdk.gdi-de.org" in reference:
            uuid_match = _UUID_RE.search(reference)
            if uuid_match:
                self.record_uuid = uuid_match.group(0)
                logger.debug(
                    "Extracted UUID from GDI-DE CSW URL: %s",
                    self.record_uuid,
                )
                return True

        # Bare UUID — verify against GDI-DE CSW catalog
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
                        "Verified bare UUID against GDI-DE CSW: %s",
                        self.record_uuid,
                    )
                    return True
            except Exception:
                logger.debug("GDI-DE CSW lookup failed for UUID %s", reference)
            return False

        return False

    def _fetch_record(self):
        """Fetch CSW record metadata via OWSLib.

        Returns:
            dict: Extracted metadata with bbox, temporal_extent, title
        """
        csw = self._get_csw()
        csw.getrecordbyid(
            id=[self.record_uuid],
            outputschema="http://www.isotc211.org/2005/gmd",
        )

        if self.record_uuid not in csw.records:
            raise Exception(f"GDI-DE CSW record not found: {self.record_uuid}")

        rec = csw.records[self.record_uuid]
        metadata = {
            "title": None,
            "bbox": None,
            "temporal_extent": None,
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
                    logger.warning(f"Could not parse GDI-DE bounding box: {e}")

        # Extract temporal extent from raw XML
        # GDI-DE uses both GML 3.2 and regular GML namespaces
        if rec.xml:
            root = ET.fromstring(rec.xml)

            # Try GML 3.2 first (more common)
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

        return metadata

    def _create_metadata_geojson(self, metadata, target_dir):
        """Create a GeoJSON file from CSW metadata.

        Args:
            metadata (dict): Extracted metadata
            target_dir (str): Target directory
        """
        if not metadata.get("bbox"):
            logger.warning("No bounding box in GDI-DE metadata, cannot create GeoJSON")
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
                        "source": "GDI-DE",
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

        geojson_file = os.path.join(target_dir, f"gdide_{self.record_uuid}.geojson")
        with open(geojson_file, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Created GDI-DE GeoJSON metadata file: {geojson_file}")

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
        """Download data from GDI-DE.

        GDI-DE is a metadata-only provider. This method always creates a
        GeoJSON file from the CSW record metadata.

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

        logger.info(f"Extracting metadata from GDI-DE: {self.reference}")

        if not self.record_uuid:
            raise Exception("No record UUID available for download")

        metadata = self._fetch_record()
        logger.debug(f"GDI-DE metadata: {metadata}")

        folder_name = f"gdide_{self.record_uuid}"
        download_dir = os.path.join(folder, folder_name)
        os.makedirs(download_dir, exist_ok=True)

        if download_data:
            logger.info(
                "GDI-DE is a metadata-only catalogue provider. "
                "Creating GeoJSON from metadata instead of downloading data files."
            )

        self._create_metadata_geojson(metadata, download_dir)

        return download_dir
