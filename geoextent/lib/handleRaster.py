import osgeo
from osgeo import gdal
from osgeo import osr
import logging
from . import helpfunctions as hf

logger = logging.getLogger("geoextent")


def get_handler_name():
    return "handleRaster"


def get_handler_display_name():
    """Return human-readable name for this handler"""
    return "Raster data"


def checkFileSupported(filepath):
    """Checks whether it is valid raster file or not. \n
    input "path": type string, path to file which shall be extracted \n
    raise exception if not valid
    """

    logger.info(filepath)
    try:
        file = gdal.OpenEx(filepath)
        driver = file.GetDriver().ShortName
    except:
        logger.debug("File {} is NOT supported by handleRaster module".format(filepath))
        return False

    if file.RasterCount > 0:
        logger.debug("File {} is supported by handleRaster module".format(filepath))
        return True
    else:
        logger.debug("File {} is NOT supported by handleRaster module".format(filepath))
        return False


def getBoundingBox(filepath, assume_wgs84=False):
    """extracts bounding box from raster \n
    input "filepath": type string, file path to raster file \n
    input "assume_wgs84": type bool, if True assume WGS84 for ungeoreferenced rasters (default False) \n
    returns bounding box of the file: type list, length = 4 , type = float, schema = [min(longs), min(lats), max(longs), max(lats)]
    """
    # Enable exceptions

    crs_output = hf.WGS84_EPSG_ID
    gdal.UseExceptions()

    geotiffContent = gdal.Open(filepath)

    # get the existing coordinate system
    projection_ref = geotiffContent.GetProjectionRef()

    # Check if projection exists (may be empty for world files without .prj)
    has_projection = projection_ref and projection_ref.strip()

    old_crs = osr.SpatialReference()
    if has_projection:
        try:
            old_crs.ImportFromWkt(projection_ref)
        except Exception as e:
            logger.debug(
                f"{filepath}: Failed to parse projection: {e}. "
                "Assuming coordinates are in WGS84 (EPSG:4326)"
            )
            has_projection = False

    # create the new coordinate system
    new_crs = osr.SpatialReference()
    new_crs.ImportFromEPSG(crs_output)

    # get the point to transform, pixel (0,0) in this case
    width = geotiffContent.RasterXSize
    height = geotiffContent.RasterYSize
    gt = geotiffContent.GetGeoTransform()

    min_x = gt[0]
    min_y = gt[3] + width * gt[4] + height * gt[5]
    max_x = gt[0] + width * gt[1] + height * gt[2]
    max_y = gt[3]

    # Transform coordinates if we have a projection, otherwise handle missing CRS
    if has_projection:
        transform = osr.CoordinateTransformation(old_crs, new_crs)
        try:
            # get the coordinates in lat long
            lat_long_min = transform.TransformPoint(min_x, min_y)
            lat_long_max = transform.TransformPoint(max_x, max_y)
        except:
            # Assume that coordinates are in EPSG:4326
            logger.debug(
                "{}: Coordinate transformation failed. Assuming coordinates are in WGS84 (EPSG:4326)".format(
                    filepath
                )
            )
            lat_long_min = [min_x, min_y]
            lat_long_max = [max_x, max_y]
    else:
        # No projection info — use raw coordinates and validate below
        lat_long_min = [min_x, min_y]
        lat_long_max = [max_x, max_y]

        candidate_bbox = [
            lat_long_min[0],
            lat_long_min[1],
            lat_long_max[0],
            lat_long_max[1],
        ]

        if assume_wgs84:
            # Explicitly enabled: always assume WGS84 for ungeoreferenced rasters
            logger.debug(
                "{}: No projection reference found. assume_wgs84=True, "
                "treating coordinates as WGS84 (EPSG:4326)".format(filepath)
            )
        elif hf.validate_bbox_wgs84(candidate_bbox):
            # Coordinates are within valid WGS84 bounds (e.g., world file without .prj)
            logger.debug(
                "{}: No projection reference found, but coordinates {} are within "
                "valid WGS84 bounds. Assuming WGS84 (EPSG:4326).".format(
                    filepath, candidate_bbox
                )
            )
        else:
            # Coordinates are outside WGS84 bounds — likely pixel coordinates
            logger.warning(
                "{}: No projection reference found and coordinates {} are outside "
                "valid WGS84 bounds. This typically indicates pixel coordinates from "
                "an ungeoreferenced raster. Skipping file "
                "(use --assume-wgs84 to force WGS84 interpretation).".format(
                    filepath, candidate_bbox
                )
            )
            return None

    bbox = [lat_long_min[0], lat_long_min[1], lat_long_max[0], lat_long_max[1]]

    if has_projection and int(osgeo.__version__[0]) >= 3:
        if old_crs.GetAxisMappingStrategy() == 1:
            bbox = [lat_long_min[1], lat_long_min[0], lat_long_max[1], lat_long_max[0]]

    # Final validation: coordinates must be within WGS84 bounds after transformation
    if not hf.validate_bbox_wgs84(bbox):
        logger.warning(
            "{}: Bounding box {} is outside valid WGS84 coordinate ranges after "
            "transformation. Skipping file.".format(filepath, bbox)
        )
        return None

    spatialExtent = {"bbox": bbox, "crs": str(crs_output)}

    return spatialExtent


def getTemporalExtent(filepath):
    """extracts temporal extent of the geotiff \n
    input "filepath": type string, file path to geotiff file \n
    returns None as There is no time value for GeoTIFF files
    """
    logger.debug("{} There is no time value for raster files".format(filepath))
    return None
