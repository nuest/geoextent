"""
Remote Raster (COG) content provider for geoextent.

Extracts spatial and temporal extents from remote GeoTIFF files (especially
Cloud Optimized GeoTIFFs) via GDAL's ``/vsicurl/`` virtual filesystem.
Only the file header is read — no full download is required.

Supported identifiers:
- Direct HTTP(S) URLs ending in .tif or .tiff (with optional query params)

This is a metadata-only provider. It opens the remote raster using GDAL's
HTTP range-request support (``/vsicurl/``) and extracts CRS, bounding box,
and temporal metadata from the file header. For COGs, this typically requires
only 1–2 HTTP requests (~16 KB transferred).

This provider is positioned **last** in the provider list — it acts as a
catch-all for ``.tif`` / ``.tiff`` URLs that no other provider claims.
"""

import json
import logging
import os
import re
from urllib.parse import urlparse

from osgeo import gdal, osr

from geoextent.lib.content_providers.providers import ContentProvider
from geoextent.lib import handle_raster
from geoextent.lib import helpfunctions as hf

logger = logging.getLogger("geoextent")

# Match HTTP(S) URLs ending in .tif or .tiff (with optional query params)
_RASTER_URL_RE = re.compile(r"https?://.+\.(tif|tiff)(\?.*)?$", re.IGNORECASE)

# GDAL config options for efficient remote raster access
_VSICURL_OPTIONS = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.tiff",
    "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
    "VSI_CACHE": "TRUE",
    "VSI_CACHE_SIZE": "5000000",
    "GDAL_HTTP_TIMEOUT": "30",
    "GDAL_HTTP_MAX_RETRY": "3",
    "GDAL_HTTP_RETRY_DELAY": "2",
}


def _set_vsicurl_config():
    """Set GDAL config options for efficient /vsicurl/ access."""
    for key, val in _VSICURL_OPTIONS.items():
        gdal.SetConfigOption(key, val)


def _restore_vsicurl_config():
    """Restore GDAL config options to defaults."""
    for key in _VSICURL_OPTIONS:
        gdal.SetConfigOption(key, None)


def _bbox_to_polygon(bbox):
    """Convert a [west, south, east, north] bbox to a GeoJSON Polygon.

    Coordinates are in [longitude, latitude] order per RFC 7946.

    Args:
        bbox (list): [west, south, east, north]

    Returns:
        dict: GeoJSON Polygon geometry
    """
    west, south, east, north = bbox
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [west, south],
                [east, south],
                [east, north],
                [west, north],
                [west, south],
            ]
        ],
    }


def _extract_bbox_from_dataset(ds):
    """Extract WGS84 bounding box from a GDAL dataset.

    Uses explicit TRADITIONAL_GIS_ORDER axis mapping to ensure coordinates
    are always returned in [longitude, latitude] order, avoiding the
    axis-order ambiguity in GDAL 3.x.

    Args:
        ds: GDAL Dataset object

    Returns:
        list or None: [minlon, minlat, maxlon, maxlat] in WGS84, or None
    """
    gt = ds.GetGeoTransform()
    width = ds.RasterXSize
    height = ds.RasterYSize

    # Compute corners from GeoTransform (always in pixel→map order)
    min_x = gt[0]
    max_x = gt[0] + width * gt[1] + height * gt[2]
    max_y = gt[3]
    min_y = gt[3] + width * gt[4] + height * gt[5]

    # Get source CRS
    projection_ref = ds.GetProjectionRef()
    if not projection_ref or not projection_ref.strip():
        # No projection — assume WGS84 if coords look valid
        bbox = [min_x, min_y, max_x, max_y]
        if hf.validate_bbox_wgs84(bbox):
            return bbox
        logger.warning("No CRS and coordinates outside WGS84 bounds")
        return None

    src_crs = osr.SpatialReference()
    src_crs.ImportFromWkt(projection_ref)
    # Force traditional GIS order (lon, lat) to avoid GDAL 3.x ambiguity
    src_crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    dst_crs = osr.SpatialReference()
    dst_crs.ImportFromEPSG(hf.WGS84_EPSG_ID)
    dst_crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    transform = osr.CoordinateTransformation(src_crs, dst_crs)
    try:
        pt_min = transform.TransformPoint(min_x, min_y)
        pt_max = transform.TransformPoint(max_x, max_y)
    except Exception as e:
        logger.warning("Coordinate transformation failed: %s", e)
        return None

    # With TRADITIONAL_GIS_ORDER: result is (lon, lat, z)
    bbox = [pt_min[0], pt_min[1], pt_max[0], pt_max[1]]

    if not hf.validate_bbox_wgs84(bbox):
        logger.warning("Bounding box %s outside valid WGS84 ranges", bbox)
        return None

    return bbox


class RemoteRaster(ContentProvider):
    """Content provider for remote GeoTIFF / COG files.

    Opens remote rasters via GDAL ``/vsicurl/`` to extract spatial and
    temporal extents without downloading the full file.
    """

    @classmethod
    def provider_info(cls):
        return {
            "name": "Remote Raster (COG)",
            "description": (
                "Direct HTTP(S) URLs to GeoTIFF/COG files. Reads raster "
                "headers via GDAL /vsicurl/ without downloading the full "
                "file. Works best with Cloud Optimized GeoTIFFs (COG) but "
                "supports any HTTP-accessible GeoTIFF."
            ),
            "website": "https://www.cogeo.org/",
            "supported_identifiers": [
                "Direct HTTP(S) URLs ending in .tif or .tiff",
            ],
            "examples": [
                "https://zenodo.org/records/14711942/files/FSM_1-km_MED-epsg.4326_v01.tif",
                "https://raw.githubusercontent.com/GeoTIFF/test-data/main/files/gfw-azores.tif",
            ],
            "notes": (
                "Metadata-only provider. Reads raster headers via GDAL "
                "/vsicurl/ without downloading the full file. Works best "
                "with Cloud Optimized GeoTIFFs (COG) but supports any "
                "HTTP-accessible GeoTIFF."
            ),
        }

    @property
    def supports_metadata_extraction(self):
        return True

    def __init__(self):
        super().__init__()
        self.name = "RemoteRaster"
        self.reference = None
        self.url = None

    def validate_provider(self, reference):
        """Fast offline check: URL must match raster extension pattern.

        Args:
            reference (str): URL or identifier to validate

        Returns:
            bool: True if this is an HTTP(S) URL ending in .tif/.tiff
        """
        self.reference = reference

        # Must be an HTTP(S) URL with a .tif/.tiff extension
        if _RASTER_URL_RE.match(reference):
            self.url = reference
            return True
        return False

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
        """Extract extent from remote raster via /vsicurl/ (no full download).

        Uses GDAL's ``/vsicurl/`` virtual filesystem to read only the raster
        header via HTTP range requests. Extracts bbox with explicit
        TRADITIONAL_GIS_ORDER axis mapping and temporal extent via
        ``handle_raster``.

        Args:
            folder (str): Target directory for GeoJSON output
            (other parameters accepted for API compatibility)

        Returns:
            str: Path to output directory
        """
        logger.info("Extracting metadata from remote raster: %s", self.url)

        download_dir = os.path.join(folder, "remote_raster")
        os.makedirs(download_dir, exist_ok=True)

        vsicurl_path = f"/vsicurl/{self.url}"

        _set_vsicurl_config()
        try:
            bbox = self._extract_bbox(vsicurl_path)
            temporal = self._extract_temporal(vsicurl_path)
        finally:
            _restore_vsicurl_config()

        if bbox is None and temporal is None:
            logger.warning(
                "Remote raster %s: no spatial or temporal data extracted",
                self.url,
            )
            return download_dir

        self._create_geojson(bbox, temporal, download_dir)
        return download_dir

    def _extract_bbox(self, vsicurl_path):
        """Extract bounding box from remote raster.

        Opens the GDAL dataset and extracts the WGS84 bounding box using
        explicit TRADITIONAL_GIS_ORDER axis mapping to ensure [lon, lat]
        coordinate order for the intermediate GeoJSON.

        Args:
            vsicurl_path (str): GDAL /vsicurl/ path

        Returns:
            list or None: [minlon, minlat, maxlon, maxlat] in WGS84, or None
        """
        try:
            gdal.UseExceptions()
            ds = gdal.Open(vsicurl_path, gdal.GA_ReadOnly)
            if ds is None:
                logger.warning("Cannot open remote raster: %s", self.url)
                return None

            bbox = _extract_bbox_from_dataset(ds)
            ds = None  # close

            if bbox:
                logger.info("Remote raster spatial extent: %s", bbox)
            return bbox
        except Exception as e:
            logger.warning("Failed to extract bbox from %s: %s", self.url, e)
            return None

    def _extract_temporal(self, vsicurl_path):
        """Extract temporal extent via handle_raster.

        Args:
            vsicurl_path (str): GDAL /vsicurl/ path

        Returns:
            list or None: [start_date, end_date] strings, or None
        """
        try:
            temporal = handle_raster.get_temporal_extent(vsicurl_path)
            if temporal:
                logger.info("Remote raster temporal extent: %s", temporal)
            return temporal
        except Exception as e:
            logger.debug("No temporal extent from %s: %s", self.url, e)
            return None

    def _create_geojson(self, bbox, temporal, folder):
        """Create a GeoJSON file from extracted metadata.

        Args:
            bbox (list or None): [minlon, minlat, maxlon, maxlat]
            temporal (list or None): [start_date, end_date]
            folder (str): Target directory

        Returns:
            str: Path to created GeoJSON file
        """
        properties = {
            "source": "RemoteRaster",
            "url": self.url,
            "format": "GeoTIFF",
        }

        if temporal:
            properties["start_time"] = temporal[0]
            properties["end_time"] = temporal[1]

        geometry = None
        if bbox:
            # bbox is [minlon, minlat, maxlon, maxlat] — convert to
            # [west, south, east, north] for _bbox_to_polygon
            geometry = _bbox_to_polygon(bbox)

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

        # Create safe filename from URL
        parsed = urlparse(self.url)
        safe_name = re.sub(r"[^\w\-.]", "_", parsed.path.split("/")[-1])
        filename = f"remote_raster_{safe_name}.geojson"
        filepath = os.path.join(folder, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)

        logger.debug("Created remote raster GeoJSON file: %s", filepath)
        return filepath
