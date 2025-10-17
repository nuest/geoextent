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


def getBoundingBox(filepath):
    """extracts bounding box from raster \n
    input "filepath": type string, file path to raster file \n
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

    # Transform coordinates if we have a projection, otherwise assume WGS84
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
        # No projection info (e.g., world file without .prj), assume WGS84
        logger.debug(
            "{}: No projection reference found (world file without .prj?). Assuming coordinates are in WGS84 (EPSG:4326)".format(
                filepath
            )
        )
        lat_long_min = [min_x, min_y]
        lat_long_max = [max_x, max_y]

    bbox = [lat_long_min[0], lat_long_min[1], lat_long_max[0], lat_long_max[1]]

    if has_projection and int(osgeo.__version__[0]) >= 3:
        if old_crs.GetAxisMappingStrategy() == 1:
            bbox = [lat_long_min[1], lat_long_min[0], lat_long_max[1], lat_long_max[0]]

    spatialExtent = {"bbox": bbox, "crs": str(crs_output)}

    return spatialExtent


def getTemporalExtent(filepath):
    """extracts temporal extent of the geotiff \n
    input "filepath": type string, file path to geotiff file \n
    returns None as There is no time value for GeoTIFF files
    """
    logger.debug("{} There is no time value for raster files".format(filepath))
    return None
