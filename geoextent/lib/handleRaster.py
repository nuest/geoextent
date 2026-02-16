import math
import re
from datetime import datetime, timedelta

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
    elif file.GetSubDatasets():
        logger.debug(
            "File {} is supported by handleRaster module (has subdatasets)".format(
                filepath
            )
        )
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

    # Handle files with subdatasets (e.g., NetCDF) — open first subdataset
    if geotiffContent.RasterCount == 0:
        subdatasets = geotiffContent.GetSubDatasets()
        if subdatasets:
            geotiffContent = gdal.Open(subdatasets[0][0])
        else:
            return None

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


def _parse_netcdf_time(ds, time_format=None):
    """Extract temporal extent from NetCDF CF time dimension metadata.

    Reads ``time#units`` (e.g. "hours since 1900-01-01 00:00:0.0") and
    ``NETCDF_DIM_time_VALUES`` from dataset metadata and computes min/max dates.

    Returns [min_date_str, max_date_str] or None.
    """
    metadata = ds.GetMetadata()

    time_units = metadata.get("time#units")
    time_values_str = metadata.get("NETCDF_DIM_time_VALUES")

    if not time_units or not time_values_str:
        return None

    # Parse "unit since reference_date" from time#units
    match = re.match(
        r"(hours|days|minutes|seconds)\s+since\s+(.+)",
        time_units.strip(),
    )
    if not match:
        logger.debug("Cannot parse time#units: {}".format(time_units))
        return None

    unit = match.group(1)
    ref_date_str = match.group(2).strip()

    # Parse reference date — try common CF formats
    ref_date = None
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.0",
        "%Y-%m-%d",
    ):
        try:
            ref_date = datetime.strptime(ref_date_str, fmt)
            break
        except ValueError:
            continue
    # Handle trailing ".0" that strptime may not match directly
    if ref_date is None:
        cleaned = re.sub(r"\.0+$", "", ref_date_str)
        try:
            ref_date = datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    if ref_date is None:
        logger.debug("Cannot parse reference date: {}".format(ref_date_str))
        return None

    # Parse time values from "{val1,val2,...}" format
    values_str = time_values_str.strip().strip("{}")
    try:
        time_offsets = [float(v) for v in values_str.split(",")]
    except ValueError:
        logger.debug("Cannot parse NETCDF_DIM_time_VALUES: {}".format(time_values_str))
        return None

    # Filter out NaN values
    time_offsets = [v for v in time_offsets if not math.isnan(v)]

    if not time_offsets:
        return None

    min_offset = min(time_offsets)
    max_offset = max(time_offsets)

    # Convert offsets to timedelta
    unit_map = {
        "hours": "hours",
        "days": "days",
        "minutes": "minutes",
        "seconds": "seconds",
    }
    td_unit = unit_map[unit]
    min_date = ref_date + timedelta(**{td_unit: min_offset})
    max_date = ref_date + timedelta(**{td_unit: max_offset})

    out_fmt = hf.resolve_time_format(time_format)
    return [min_date.strftime(out_fmt), max_date.strftime(out_fmt)]


def _parse_acdd_time(ds, time_format=None):
    """Extract temporal extent from ACDD global attributes.

    Reads ``NC_GLOBAL#time_coverage_start`` and ``NC_GLOBAL#time_coverage_end``
    from dataset metadata (Attribute Convention for Data Discovery).

    Returns [min_date_str, max_date_str] or None.
    """
    metadata = ds.GetMetadata()

    start_str = metadata.get("NC_GLOBAL#time_coverage_start")
    end_str = metadata.get("NC_GLOBAL#time_coverage_end")

    if not start_str and not end_str:
        return None

    formats = ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]

    def _try_parse(s):
        if not s:
            return None
        for fmt in formats:
            try:
                return datetime.strptime(s.strip(), fmt)
            except ValueError:
                continue
        logger.debug("Cannot parse ACDD time_coverage value: {}".format(s))
        return None

    start_dt = _try_parse(start_str)
    end_dt = _try_parse(end_str)

    out_fmt = hf.resolve_time_format(time_format)
    if start_dt and end_dt:
        return [start_dt.strftime(out_fmt), end_dt.strftime(out_fmt)]
    elif start_dt:
        date_str = start_dt.strftime(out_fmt)
        return [date_str, date_str]
    elif end_dt:
        date_str = end_dt.strftime(out_fmt)
        return [date_str, date_str]

    return None


def _parse_imagery_acquisition_time(ds, time_format=None):
    """Extract temporal extent from band-level IMAGERY domain metadata.

    Reads ``ACQUISITIONDATETIME`` from each band's IMAGERY metadata domain.

    Returns [min_date_str, max_date_str] or None.
    """
    formats = ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]
    dates = []

    for i in range(1, ds.RasterCount + 1):
        band = ds.GetRasterBand(i)
        imagery_md = band.GetMetadata("IMAGERY")
        acq_str = imagery_md.get("ACQUISITIONDATETIME")
        if not acq_str:
            continue
        for fmt in formats:
            try:
                dates.append(datetime.strptime(acq_str.strip(), fmt))
                break
            except ValueError:
                continue
        else:
            logger.debug("Cannot parse ACQUISITIONDATETIME: {}".format(acq_str))

    if not dates:
        return None

    out_fmt = hf.resolve_time_format(time_format)
    min_date = min(dates)
    max_date = max(dates)
    return [min_date.strftime(out_fmt), max_date.strftime(out_fmt)]


def getTemporalExtent(filepath, time_format=None):
    """Extract temporal extent from raster files.

    Tries metadata sources in this order, returning the first non-None result:

    1. NetCDF CF time dimension (subdataset, then main dataset)
    2. ACDD global attributes (``NC_GLOBAL#time_coverage_start/end``)
    3. GeoTIFF ``TIFFTAG_DATETIME``
    4. Band-level ``ACQUISITIONDATETIME`` (IMAGERY domain)

    Returns [min_date_str, max_date_str] or None.
    """
    gdal.UseExceptions()
    ds = gdal.Open(filepath)
    if ds is None:
        return None

    # Handle files with subdatasets (e.g., NetCDF)
    if ds.RasterCount == 0:
        subdatasets = ds.GetSubDatasets()
        if subdatasets:
            subds = gdal.Open(subdatasets[0][0])
            if subds is not None:
                result = _parse_netcdf_time(subds, time_format)
                if result:
                    return result

    # Try NetCDF time on the main dataset
    result = _parse_netcdf_time(ds, time_format)
    if result:
        return result

    # Try ACDD global attributes
    result = _parse_acdd_time(ds, time_format)
    if result:
        return result

    # Try GeoTIFF TIFFTAG_DATETIME
    tifftag = ds.GetMetadataItem("TIFFTAG_DATETIME")
    if tifftag and tifftag.strip():
        try:
            dt = datetime.strptime(tifftag.strip(), "%Y:%m:%d %H:%M:%S")
            out_fmt = hf.resolve_time_format(time_format)
            date_str = dt.strftime(out_fmt)
            return [date_str, date_str]
        except ValueError:
            logger.debug("Cannot parse TIFFTAG_DATETIME: {}".format(tifftag))

    # Try band-level ACQUISITIONDATETIME (IMAGERY domain)
    result = _parse_imagery_acquisition_time(ds, time_format)
    if result:
        return result

    logger.debug("{}: No temporal metadata found in raster file".format(filepath))
    return None
