"""Handler for point cloud data (LAS/LAZ files) via laspy.

Extracts bounding boxes from LAS/LAZ file headers (no point loading required)
and temporal extent from the LAS header creation date field.
"""

import logging
import laspy
from . import helpfunctions as hf

logger = logging.getLogger("geoextent")


def get_handler_name():
    return "handle_pointcloud"


def get_handler_display_name():
    """Return human-readable name for this handler"""
    return "Point cloud data"


def check_file_supported(filepath):
    """Check whether the file is a valid LAS/LAZ point cloud file.

    Verifies the file extension (.las or .laz, case-insensitive) and then
    attempts to open the file with laspy to confirm it is valid.

    Args:
        filepath: Path to the file to check

    Returns:
        True if the file is a valid LAS/LAZ file, False otherwise
    """
    import os

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in (".las", ".laz"):
        return False

    try:
        with laspy.open(filepath) as f:
            # Successfully opened — it's a valid LAS/LAZ file
            pass
        logger.debug(
            "File {} is supported by handle_pointcloud module".format(filepath)
        )
        return True
    except Exception as e:
        logger.debug(
            "File {} is NOT supported by handle_pointcloud module: {}".format(
                filepath, e
            )
        )
        return False


def get_bounding_box(filepath):
    """Extract bounding box from LAS/LAZ file header.

    Reads only the file header (no point data loaded), extracts min/max
    coordinates and CRS information.

    Args:
        filepath: Path to the LAS/LAZ file

    Returns:
        dict with "bbox" ([minx, miny, maxx, maxy]) and "crs" (EPSG code as str)
        or "crs_wkt" (WKT string), or None if extraction fails.
    """
    try:
        with laspy.open(filepath) as f:
            header = f.header

            mins = header.mins
            maxs = header.maxs

            # Extract 2D bounding box [minx, miny, maxx, maxy]
            bbox = [float(mins[0]), float(mins[1]), float(maxs[0]), float(maxs[1])]

            # Check for degenerate bbox (all zeros or mins == maxs in both dimensions)
            if bbox[0] == bbox[2] and bbox[1] == bbox[3]:
                # Point count check: if truly empty, return None
                if header.point_count == 0:
                    logger.debug(
                        "{}: Empty point cloud (0 points), no bounding box".format(
                            filepath
                        )
                    )
                    return None

            # Try to extract CRS
            crs_epsg = None
            crs_wkt = None

            try:
                # laspy >= 2.4 provides parse_crs() returning a pyproj.CRS
                parsed_crs = header.parse_crs()
                if parsed_crs is not None:
                    try:
                        epsg = parsed_crs.to_epsg()
                        if epsg is not None:
                            crs_epsg = str(epsg)
                    except Exception:
                        pass

                    if crs_epsg is None:
                        # Fall back to WKT
                        try:
                            wkt = parsed_crs.to_wkt()
                            if wkt and wkt.strip():
                                crs_wkt = wkt
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(
                    "{}: Could not parse CRS from header: {}".format(filepath, e)
                )

            # If no CRS found, check if coordinates are within WGS84 bounds
            if crs_epsg is None and crs_wkt is None:
                if hf.validate_bbox_wgs84(bbox):
                    logger.debug(
                        "{}: No CRS in LAS header, but coordinates {} are within "
                        "valid WGS84 bounds. Assuming WGS84 (EPSG:4326).".format(
                            filepath, bbox
                        )
                    )
                    crs_epsg = str(hf.WGS84_EPSG_ID)
                else:
                    logger.warning(
                        "{}: No CRS in LAS header and coordinates {} are outside "
                        "valid WGS84 bounds. Cannot determine coordinate reference "
                        "system.".format(filepath, bbox)
                    )
                    return None

            result = {"bbox": bbox}
            if crs_epsg is not None:
                result["crs"] = crs_epsg
            elif crs_wkt is not None:
                result["crs_wkt"] = crs_wkt

            return result

    except Exception as e:
        logger.warning(
            "{}: Error extracting bounding box from point cloud: {}".format(filepath, e)
        )
        return None


def get_temporal_extent(filepath, time_format=None):
    """Extract temporal extent from LAS/LAZ file header creation date.

    The LAS specification includes a creation date (year + day-of-year) in
    the file header. This is used as a single-date temporal extent.

    Args:
        filepath: Path to the LAS/LAZ file
        time_format: Output time format (None for default, preset name, or strftime string)

    Returns:
        [date_str, date_str] (start == end for single creation date) or None
    """
    try:
        with laspy.open(filepath) as f:
            header = f.header

            # Check raw header fields: year=0 and day=0 means "no date set"
            # laspy defaults creation_date to today when the raw values are 0,
            # so we check the raw bytes via the LasData internal fields.
            try:
                # Read raw creation date fields from the file header
                import struct

                with open(filepath, "rb") as raw:
                    raw.seek(90)  # LAS header: creation_day at offset 90
                    raw_day, raw_year = struct.unpack("<HH", raw.read(4))
                if raw_year == 0 and raw_day == 0:
                    logger.debug(
                        "{}: No creation date in LAS header (year=0, day=0)".format(
                            filepath
                        )
                    )
                    return None
            except Exception:
                pass

            creation_date = header.creation_date

            if creation_date is None:
                logger.debug("{}: No creation date in LAS header".format(filepath))
                return None

            out_fmt = hf.resolve_time_format(time_format)
            # creation_date is a datetime.date object
            date_str = creation_date.strftime(out_fmt)
            return [date_str, date_str]

    except Exception as e:
        logger.debug(
            "{}: Error extracting temporal extent from point cloud: {}".format(
                filepath, e
            )
        )
        return None
