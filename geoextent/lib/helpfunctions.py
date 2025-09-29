import csv
import datetime
import itertools
import json
import logging
import os
import patoolib
import random
import re
import uuid
import pandas as pd
from osgeo import ogr
from osgeo import osr
from pathlib import Path

import geojsonio

# Default seed for reproducible random sampling
DEFAULT_DOWNLOAD_SAMPLE_SEED = 42

# to suppress warning "FutureWarning: Neither gdal.UseExceptions() nor gdal.DontUseExceptions() has been explicitly called. In GDAL 4.0, exceptions will be enabled by default."
ogr.UseExceptions()
osr.UseExceptions()


output_time_format = "%Y-%m-%d"
PREFERRED_SAMPLE_SIZE = 30
WGS84_EPSG_ID = 4326
logger = logging.getLogger("geoextent")

https_regexp = re.compile("https?://(.*)")  # Match both HTTP and HTTPS

# doi_regexp, is_doi, and normalize_doi are from idutils (https://github.com/inveniosoftware/idutils)
# Copyright (C) 2015-2018 CERN.
# Copyright (C) 2018 Alan Rubin.
# Licensed under BSD-3-Clause license
doi_regexp = re.compile(
    r"(doi:\s*|(?:https?://)?(?:dx\.)?doi\.org/)?(10\.\d+(.\d+)*/.+)$", flags=re.I
)


def getAllRowElements(row_name, elements, exp_data=None):
    """
    Function purpose: help-function to get all row elements for a specific string \n
    Input: row name, elements, exp_format \n
    Output: array values
    """
    values = []
    for idx, val in enumerate(elements[0]):
        if row_name in val:
            indexOf = idx
            for x in elements:
                try:
                    if x[indexOf] != row_name:
                        values.append(x[indexOf].replace(" ", ""))
                except IndexError as e:
                    logger.info(
                        "Row skipped,file might be corrupted. Error {}".format(e)
                    )
                    pass

    if exp_data == "time":
        if get_time_format(values, 30) is not None:
            return values

    elif exp_data == "numeric":
        try:
            values_num = list(map(float_convert, values))
            values_num_none = [i for i in values_num if i]
            if len(values_num_none) == 0:
                return None
            else:
                return values_num_none
        except Exception as e:
            logger.debug(e)
            return None
    else:
        return values


def float_convert(val):
    try:
        return float(val)
    except ValueError:
        pass


def searchForParameters(elements, param_array, exp_data=None):
    """
    Function purpose: return all attributes of a elements in the first row of a file \n
    Function purpose: return all attributes of a elements in the first row of a file \n
    Input: paramArray, elements \n
    Output: getAllRowElements(x,elements)
    """
    matching_elements = []
    for x in param_array:
        for row in elements[0]:
            p = re.compile(x, re.IGNORECASE)
            if p.search(row) is not None:
                row_to_extract = getAllRowElements(row, elements, exp_data)
                if row_to_extract is not None:
                    matching_elements.append(row_to_extract)

    matching_elements = sum(matching_elements, [])
    if len(matching_elements) == 0:
        return None

    return matching_elements


def transformingIntoWGS84(crs, coordinate):
    """
    Function purpose: transforming SRS into WGS84 (EPSG:4326) \n
    Input: crs, point \n
    Output: retPoint constisting of x2, y2 (transformed points)
    """
    # TODO: check whether current src is 4326
    source = osr.SpatialReference()
    source.ImportFromEPSG(int(crs))

    target = osr.SpatialReference()
    target.ImportFromEPSG(WGS84_EPSG_ID)

    transform = osr.CoordinateTransformation(source, target)

    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint(float(coordinate[0]), float(coordinate[1]))
    point = point.ExportToWkt()
    point = ogr.CreateGeometryFromWkt(point)

    point.Transform(transform)

    return [point.GetX(), point.GetY()]


def transformingArrayIntoWGS84(crs, pointArray):
    """
    Function purpose: transforming SRS into WGS84 (EPSG 4326) from an array
    Input: crs, pointArray \n
    Output: array array
    """
    # print("----<>", pointArray)#
    array = []
    # vector_rep
    if type(pointArray[0]) == list:
        for x in pointArray:
            array.append(transformingIntoWGS84(crs, x))
        return array
    # bbox
    elif len(pointArray) == 4:
        bbox = [[pointArray[0], pointArray[1]], [pointArray[2], pointArray[3]]]
        transf_bbox = transformingArrayIntoWGS84(crs, bbox)
        return [
            transf_bbox[0][0],
            transf_bbox[0][1],
            transf_bbox[1][0],
            transf_bbox[1][1],
        ]


def validate_bbox_wgs84(bbox):
    """
    Function purpose: Validate if bbox is correct for WGS84
    bbox: bounding box (list)
    Output: True if bbox is correct for WGS84
    """
    valid = True
    lon_values = bbox[0:3:2]
    lat_values = bbox[1:4:2]

    if (
        sum(list(map(lambda x: x < -90 or x > 90, lat_values)))
        + sum(list(map(lambda x: x < -180 or x > 180, lon_values)))
        > 0
    ):
        valid = False

    return valid


def flip_bbox(bbox):
    """
    bbox: Bounding box (list)
    Output: bbox flipped (Latitude to longitude if possible)
    """
    # Flip values
    lon_values = bbox[1:4:2]
    lat_values = bbox[0:3:2]

    bbox_flip = [lon_values[0], lat_values[0], lon_values[1], lat_values[1]]
    if validate_bbox_wgs84(bbox_flip):
        logger.warning("Longitude and latitude values flipped")
        return bbox_flip
    else:
        raise Exception(
            "Latitude and longitude values extracted do not seem to be correctly transformed. We tried "
            "flipping latitude and longitude values but both bbox are incorrect"
        )


def validate(date_text):
    try:
        if datetime.datetime.strptime(date_text, output_time_format):
            return True
    except:
        return False


def getDelimiter(csv_file):
    dialect = csv.Sniffer().sniff(csv_file.readline(1024))
    # To reset back position to beginning of the file
    csv_file.seek(0)
    return dialect.delimiter


def get_time_format(time_list, num_sample):
    """
    Function purpose: 'Guess' time format of a list of 'strings' by taking a representative sample
    time_list:  list of strings \n
    num_sample: size of the sample to determine time format \n
    Output: time format in string format (e.g '%Y.%M.d')
    """

    date_time_format = None

    if num_sample is None:
        num_sample = PREFERRED_SAMPLE_SIZE
        logger.info(
            "num_sample not provided, num_sample modified to SAMPLE_SIZE {}".format(
                PREFERRED_SAMPLE_SIZE
            )
        )
    elif type(num_sample) is not int:
        raise Exception("num_sample parameter  must be an integer")
    elif num_sample <= 0:
        raise Exception(
            "num_sample parameter: {} must be greater than 0".format(num_sample)
        )

    if len(time_list) < num_sample:
        time_sample = time_list
        logger.info(
            "num_sample is greater than the length of the list. num_sample modified to length of list {}".format(
                len(time_list)
            )
        )
    else:
        # Selects first and last element
        time_sample = [
            [time_list[1], time_list[-1]],
            random.sample(time_list[1:-1], num_sample - 2),
        ]
        # Selects num_sample-2 elements
        time_sample = sum(time_sample, [])

    # Primary method: pandas format detection (fallback approach without numpy)
    format_list = []
    for i in range(0, len(time_sample)):
        try:
            # Try to use pandas to infer format directly instead of _guess_datetime_format_for_array
            sample_series = pd.to_datetime([time_sample[i]])
            if not sample_series.isna().all():
                # If pandas can parse it, we'll use 'flexible' as indicator
                format_list.append("flexible")
            else:
                format_list.append(None)
        except Exception:
            format_list.append(None)
    unique_formats = list(set([f for f in format_list if f is not None]))

    logger.info("UNIQUE_FORMATS {}".format(unique_formats))
    if unique_formats is not None:
        for tf in unique_formats:
            try:
                pd.to_datetime(time_sample, format=tf)
                date_time_format = tf
                break
            except:
                pass

    # Fallback 1: Try pandas flexible parsing without explicit format
    if date_time_format is None:
        logger.debug("Primary format detection failed, trying flexible parsing")
        try:
            # Test if pandas can parse the sample without explicit format
            parsed_sample = pd.to_datetime(time_sample, errors="coerce")
            if not parsed_sample.isna().all():
                # If parsing succeeds, return a special indicator for flexible parsing
                date_time_format = "flexible"
                logger.debug("Flexible parsing successful")
        except Exception:
            pass

    # Fallback 2: Try common datetime format patterns
    if date_time_format is None:
        logger.debug("Flexible parsing failed, trying common format patterns")
        common_formats = [
            "%Y/%m/%d %H:%M:%S",  # 2023/03/23 23:23:23
            "%Y-%m-%d %H:%M:%S",  # 2023-03-23 23:23:23
            "%Y/%m/%d",  # 2023/03/23
            "%Y-%m-%d",  # 2023-03-23
            "%d/%m/%Y",  # 23/03/2023
            "%d-%m-%Y",  # 23-03-2023
            "%m/%d/%Y",  # 03/23/2023
            "%m-%d-%Y",  # 03-23-2023
            "%Y%m%d",  # 20230323
            "%d.%m.%Y",  # 23.03.2023
            "%Y.%m.%d",  # 2023.03.23
            "%Y-%m-%dT%H:%M:%S",  # 2023-03-23T23:23:23 (ISO 8601)
            "%Y-%m-%dT%H:%M:%S.%f",  # 2023-03-23T23:23:23.123456 (ISO with fractional)
            "%Y-%m-%dT%H:%M:%S%z",  # 2023-03-23T23:23:23+0200 (ISO with timezone offset)
            "%Y-%m-%d %H:%M:%S.%f",  # 2023-03-23 23:23:23.123456 (space sep with fractional)
            "%d %B %Y",  # 23 March 2023 (verbose month)
            "%d %b %Y",  # 23 Mar 2023 (abbrev month)
            "%a, %d %b %Y %H:%M:%S %z",  # Thu, 23 Mar 2023 23:23:23 +0200 (RFC 2822/email)
            "%H:%M:%S",  # 23:23:23 (time only)
            "%H:%M:%S.%f",  # 23:23:23.123 (time with fractional seconds)
            "%Y-%m",  # 2023-03 (year-month)
            "%Y",  # 2023 (year only)
            "%Y-%j",  # 2023-082 (ordinal day of year)
            "%d/%m/%y",  # 23/03/23 (two-digit year)
            "%m/%d/%y",  # 03/23/23 (US two-digit year)
            "%Y.%m.%d %H:%M:%S",  # 2023.03.23 23:23:23 (dotted date with time)
        ]

        for fmt in common_formats:
            try:
                pd.to_datetime(time_sample, format=fmt, errors="raise")
                date_time_format = fmt
                logger.debug("Found matching format: {}".format(fmt))
                break
            except Exception:
                continue

    return date_time_format


def date_parser(datetime_list, num_sample=None):
    """
    Function purpose: transform list of strings into date-time format
    datetime_list: list of date-times (strings) \n
    Output: list of DatetimeIndex
    """

    datetime_format = get_time_format(datetime_list, num_sample)

    if datetime_format is not None:
        if datetime_format == "flexible":
            # Use pandas flexible parsing without explicit format
            parse_time_input_format = pd.to_datetime(datetime_list, errors="coerce")
        else:
            # Use explicit format
            parse_time_input_format = pd.to_datetime(
                datetime_list, format=datetime_format, errors="coerce"
            )

        parse_time = pd.to_datetime(
            parse_time_input_format, format=output_time_format, errors="coerce"
        )
    else:
        parse_time = None

    return parse_time


def extract_archive(filepath) -> Path:
    """
    Function purpose: extract archive (always inside a new folder)
    filepath: filepath to archive
    """

    filepath = Path(filepath)

    while True:
        folder_to_extract = Path.joinpath(
            filepath.parent, f"{filepath.name}_{uuid.uuid4()}"
        )
        if not folder_to_extract.exists():
            break

    try:
        patoolib.extract_archive(
            archive=filepath, outdir=folder_to_extract, verbosity=-1
        )
    except patoolib.util.PatoolError:
        pass
    except TypeError:
        # exception to prevent this error:
        # TypeError: Path.replace() takes 2 positional arguments but 3 were given
        pass
    except Exception:
        pass
    finally:
        folder_to_extract.mkdir(parents=True, exist_ok=True)
        # to prevent this error:
        # [Errno 2] No such file or directory:

    return folder_to_extract


def bbox_merge(metadata, origin):
    """
    Function purpose: merge bounding boxes

    Args:
        metadata: metadata with geoextent extraction from multiple files (dict)
                 Each file should have a "bbox" field with [minx, miny, maxx, maxy] format
                 and a "crs" field with CRS identifier
        origin: folder path or filepath (str)

    Returns:
        Merged bbox dict with "bbox" (list) and "crs" (str) fields, or None if no valid extents

    Note: All coordinates are expected to be in [longitude, latitude] order (GeoJSON standard)
    """
    logger.debug("metadata {}".format(metadata))
    boxes_extent = []
    metadata_merge = {}
    num_files = len(metadata.items())
    for x, y in metadata.items():
        if isinstance(y, dict):
            try:
                bbox_extent = [y["bbox"], y["crs"]]
                boxes_extent.append(bbox_extent)
            except:
                logger.debug(
                    "{} does not have identifiable geographical extent (CRS+bbox)".format(
                        x
                    )
                )
                pass
    if len(boxes_extent) == 0:
        logger.debug(
            " ** {} does not have geometries with identifiable geographical extent (CRS+bbox)".format(
                origin
            )
        )
        return None
    elif len(boxes_extent) > 0:

        multipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
        des_crs = ogr.osr.SpatialReference()
        des_crs.ImportFromEPSG(WGS84_EPSG_ID)
        multipolygon.AssignSpatialReference(des_crs)

        for bbox in boxes_extent:

            try:
                box = ogr.Geometry(ogr.wkbLinearRing)
                box.AddPoint(bbox[0][0], bbox[0][1])
                box.AddPoint(bbox[0][2], bbox[0][1])
                box.AddPoint(bbox[0][2], bbox[0][3])
                box.AddPoint(bbox[0][0], bbox[0][3])
                box.AddPoint(bbox[0][0], bbox[0][1])

                if bbox[1] != str(WGS84_EPSG_ID):
                    source = osr.SpatialReference()
                    source.ImportFromEPSG(int(bbox[1]))
                    transform = osr.CoordinateTransformation(source, des_crs)
                    box.Transform(transform)

                polygon = ogr.Geometry(ogr.wkbPolygon)
                polygon.AddGeometry(box)
                multipolygon.AddGeometry(polygon)

            except Exception as e:
                logger.debug(
                    "Error extracting geographic extent. CRS {} may be invalid. Error: {}".format(
                        int(bbox[1]), e
                    )
                )
                continue

        num_geo_files = multipolygon.GetGeometryCount() / 4
        if num_geo_files > 0:
            logger.debug(
                "{} contains {} geometries out of {} with identifiable geographic extent".format(
                    origin, int(num_geo_files), num_files
                )
            )
            env = multipolygon.GetEnvelope()
            metadata_merge["bbox"] = [env[0], env[2], env[1], env[3]]
            metadata_merge["crs"] = str(WGS84_EPSG_ID)
        else:
            logger.debug(
                " {} does not have geometries with identifiable geographical extent (CRS+bbox)".format(
                    origin
                )
            )
            metadata_merge = None

    return metadata_merge


def convex_hull_merge(metadata, origin):
    """
    Function purpose: merge convex hulls by creating a convex hull from all individual geometries

    Args:
        metadata: metadata with geoextent extraction from multiple files (dict)
                 Each file should have:
                 - "bbox" field: either [minx, miny, maxx, maxy] or coordinate array
                 - "crs" field: CRS identifier
                 - "convex_hull" field: True if convex hull data is available
        origin: folder path or filepath (str)

    Returns:
        Merged convex hull as GeoJSON polygon dict with "bbox", "crs", and "convex_hull" fields
        Returns None if convex hull calculation fails (will trigger fallback to bbox_merge)

    Note: All coordinates are expected to be in [longitude, latitude] order (GeoJSON standard)
    """
    logger.debug("convex hull metadata {}".format(metadata))
    geometries = []
    metadata_merge = {}
    num_files = len(metadata.items())

    for x, y in metadata.items():
        if isinstance(y, dict):
            try:
                if "convex_hull" in y and "bbox" in y and "crs" in y:
                    # If we have an existing convex hull geometry from the vector handler, use it
                    bbox = y["bbox"]
                    crs = y["crs"]

                    # Check if bbox contains actual convex hull coordinates
                    if (
                        isinstance(bbox, dict)
                        and bbox.get("type") == "Polygon"
                        and "coordinates" in bbox
                    ):
                        # This is GeoJSON polygon format with actual convex hull geometry data
                        coords = bbox["coordinates"][0]  # Get the outer ring

                        # Create a polygon from the convex hull coordinates
                        ring = ogr.Geometry(ogr.wkbLinearRing)
                        for coord in coords:
                            ring.AddPoint(coord[0], coord[1])

                        polygon = ogr.Geometry(ogr.wkbPolygon)
                        polygon.AddGeometry(ring)
                    elif isinstance(bbox, list) and len(bbox) > 4:
                        # This is a coordinate array format with actual convex hull coordinates
                        ring = ogr.Geometry(ogr.wkbLinearRing)
                        for coord in bbox:
                            ring.AddPoint(coord[0], coord[1])

                        polygon = ogr.Geometry(ogr.wkbPolygon)
                        polygon.AddGeometry(ring)
                    elif (
                        isinstance(bbox, list)
                        and len(bbox) == 1
                        and isinstance(bbox[0], list)
                        and len(bbox[0]) == 2
                    ):
                        # This is a single point coordinate [[x, y]]
                        x, y = bbox[0]
                        epsilon = 1e-10  # Small value to avoid degenerate polygon
                        box = ogr.Geometry(ogr.wkbLinearRing)
                        box.AddPoint(x - epsilon, y - epsilon)
                        box.AddPoint(x + epsilon, y - epsilon)
                        box.AddPoint(x + epsilon, y + epsilon)
                        box.AddPoint(x - epsilon, y + epsilon)
                        box.AddPoint(x - epsilon, y - epsilon)  # close ring

                        polygon = ogr.Geometry(ogr.wkbPolygon)
                        polygon.AddGeometry(box)
                    elif isinstance(bbox, list) and len(bbox) == 4:
                        # This is a regular bounding box [minx, miny, maxx, maxy] - create rectangle
                        min_x, min_y, max_x, max_y = bbox

                        # Check for degenerate cases
                        if min_x == max_x and min_y == max_y:
                            # Point data - create a very small rectangle around the point
                            epsilon = 1e-10  # Small value to avoid degenerate polygon
                            box = ogr.Geometry(ogr.wkbLinearRing)
                            box.AddPoint(min_x - epsilon, min_y - epsilon)
                            box.AddPoint(min_x + epsilon, min_y - epsilon)
                            box.AddPoint(min_x + epsilon, min_y + epsilon)
                            box.AddPoint(min_x - epsilon, min_y + epsilon)
                            box.AddPoint(min_x - epsilon, min_y - epsilon)  # close ring
                        elif min_x == max_x or min_y == max_y:
                            # Line data - create a thin rectangle
                            epsilon = 1e-10
                            if min_x == max_x:
                                # vertical line
                                box = ogr.Geometry(ogr.wkbLinearRing)
                                box.AddPoint(min_x - epsilon, min_y)
                                box.AddPoint(min_x + epsilon, min_y)
                                box.AddPoint(min_x + epsilon, max_y)
                                box.AddPoint(min_x - epsilon, max_y)
                                box.AddPoint(min_x - epsilon, min_y)  # close ring
                            else:
                                # horizontal line
                                box = ogr.Geometry(ogr.wkbLinearRing)
                                box.AddPoint(min_x, min_y - epsilon)
                                box.AddPoint(max_x, min_y - epsilon)
                                box.AddPoint(max_x, min_y + epsilon)
                                box.AddPoint(min_x, min_y + epsilon)
                                box.AddPoint(min_x, min_y - epsilon)  # close ring
                        else:
                            # Normal rectangle
                            box = ogr.Geometry(ogr.wkbLinearRing)
                            box.AddPoint(min_x, min_y)  # min_x, min_y
                            box.AddPoint(max_x, min_y)  # max_x, min_y
                            box.AddPoint(max_x, max_y)  # max_x, max_y
                            box.AddPoint(min_x, max_y)  # min_x, max_y
                            box.AddPoint(min_x, min_y)  # close ring

                        polygon = ogr.Geometry(ogr.wkbPolygon)
                        polygon.AddGeometry(box)
                    else:
                        # Skip invalid bbox formats (empty lists, etc.)
                        continue

                    # Transform to WGS84 if necessary
                    if crs != str(WGS84_EPSG_ID):
                        source = osr.SpatialReference()
                        source.ImportFromEPSG(int(crs))
                        des_crs = osr.SpatialReference()
                        des_crs.ImportFromEPSG(WGS84_EPSG_ID)
                        transform = osr.CoordinateTransformation(source, des_crs)
                        polygon.Transform(transform)

                    geometries.append(polygon)
                elif "bbox" in y and "crs" in y:
                    # Fallback to bbox if no convex hull flag
                    bbox = y["bbox"]
                    crs = y["crs"]

                    # Create a polygon from the bounding box
                    box = ogr.Geometry(ogr.wkbLinearRing)
                    box.AddPoint(bbox[0], bbox[1])
                    box.AddPoint(bbox[2], bbox[1])
                    box.AddPoint(bbox[2], bbox[3])
                    box.AddPoint(bbox[0], bbox[3])
                    box.AddPoint(bbox[0], bbox[1])

                    polygon = ogr.Geometry(ogr.wkbPolygon)
                    polygon.AddGeometry(box)

                    # Transform to WGS84 if necessary
                    if crs != str(WGS84_EPSG_ID):
                        source = osr.SpatialReference()
                        source.ImportFromEPSG(int(crs))
                        des_crs = osr.SpatialReference()
                        des_crs.ImportFromEPSG(WGS84_EPSG_ID)
                        transform = osr.CoordinateTransformation(source, des_crs)
                        polygon.Transform(transform)

                    geometries.append(polygon)
            except Exception as e:
                logger.debug(
                    "{} does not have identifiable geographical extent for convex hull: {}".format(
                        x, e
                    )
                )
                pass

    if len(geometries) == 0:
        logger.debug(
            " ** {} does not have geometries with identifiable geographical extent for convex hull".format(
                origin
            )
        )
        return None
    elif len(geometries) > 0:
        try:
            # Create a geometry collection from all geometries
            geom_collection = ogr.Geometry(ogr.wkbGeometryCollection)
            for geom in geometries:
                geom_collection.AddGeometry(geom)

            # Calculate convex hull of all geometries together
            convex_hull = geom_collection.ConvexHull()

            if convex_hull is None:
                logger.warning(
                    "Could not calculate convex hull for merged geometries from {} - "
                    "insufficient data points or collinear coordinates. Falling back to bounding box.".format(
                        origin
                    )
                )
                # Fall back to regular bounding box merge
                return bbox_merge(metadata, origin)

            # Extract the actual convex hull coordinates for the merged result
            convex_hull_coords = []

            # Handle all polygon variants (2D, 3D, measured, etc.)
            geometry_type = convex_hull.GetGeometryType()

            # Check if it's a polygon (including 2.5D, 3D variants)
            if geometry_type in [
                ogr.wkbPolygon,
                ogr.wkbPolygon25D,
                ogr.wkbPolygonM,
                ogr.wkbPolygonZM,
            ]:
                # Get the exterior ring
                ring = convex_hull.GetGeometryRef(0)
                if ring is not None:
                    point_count = ring.GetPointCount()
                    for i in range(point_count):
                        x, y, z = ring.GetPoint(i)
                        convex_hull_coords.append([x, y])
            else:
                # Flatten the geometry type to handle 2.5D variants
                base_geometry_type = ogr.Geometry.wkbFlatten(geometry_type)

                if base_geometry_type == ogr.wkbPolygon:
                    # Get the exterior ring
                    ring = convex_hull.GetGeometryRef(0)
                    if ring is not None:
                        point_count = ring.GetPointCount()
                        for i in range(point_count):
                            x, y, z = ring.GetPoint(i)
                            convex_hull_coords.append([x, y])

            # Store as GeoJSON polygon format
            metadata_merge["bbox"] = {
                "type": "Polygon",
                "coordinates": [convex_hull_coords],
            }
            metadata_merge["crs"] = str(WGS84_EPSG_ID)
            metadata_merge["convex_hull"] = True

            logger.debug(
                "{} contains {} geometries with convex hull merged".format(
                    origin, len(geometries)
                )
            )

        except Exception as e:
            logger.warning(
                "Error calculating merged convex hull for {}: {}. Falling back to bounding box.".format(origin, e)
            )
            # Fall back to regular bounding box merge
            return bbox_merge(metadata, origin)

    return metadata_merge


def tbox_merge(metadata, path):
    """
    Function purpose: Merge time boxes
    metadata: metadata with geoextent extraction from multiple files (dict)
    path: path of directory being merged
    Output: Merged tbox
    """
    boxes = []
    num_files = len(metadata.items())
    for x, y in metadata.items():
        if isinstance(y, dict):
            try:
                boxes.append(y["tbox"][0])
                boxes.append(y["tbox"][1])
            except:
                pass

    num_time_files = len(boxes)
    if num_time_files == 0:
        logger.debug(
            " ** Directory {} does not have files with identifiable temporal extent".format(
                path
            )
        )
        return None

    else:
        for i in range(0, len(boxes)):
            boxes[i] = datetime.datetime.strptime(boxes[i], output_time_format)
        min_date = min(boxes).strftime(output_time_format)
        max_date = max(boxes).strftime(output_time_format)
        logger.debug(
            "Folder {} contains {} files out of {} with identifiable temporal extent".format(
                path, int(num_time_files), num_files
            )
        )
        time_ext = [min_date, max_date]

    return time_ext


def transform_bbox(x):
    """
    Function purpose: Transform bounding box (str) into geometry
    x: bounding box (str)
    """

    try:
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(x[0], x[1])
        ring.AddPoint(x[2], x[1])
        ring.AddPoint(x[2], x[3])
        ring.AddPoint(x[0], x[3])
        ring.CloseRings()
        # Create polygon
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)
        poly.FlattenTo2D()
        bbox = poly.ExportToWkt()

    except:

        bbox = None

    return bbox


def transform_tbox(x):
    """
    Function purpose: Transform time box (list) into int
    x: time box (list)
    """

    if x is None:
        return None
    elif isinstance(x, list):
        return str(x[0]) + "/" + str(x[1])


def extract_details(details):
    """
    Function purpose: Extracts details from geoextent extraction
    details: dictionary with geoextent extraction
    Output: dataframe organized by filename, file format, handler, bbox, tbox and crs by file.
    """

    filename = []
    file_format = []
    handler = []
    bbox = []
    tbox = []
    crs = []

    for i in details:

        file = details[i]

        if file is None:
            filename.append([i])
            file_format_v = os.path.splitext(i)[1][1:]
            if file_format_v == "":
                file_format_v = "undetected"
            file_format.append([file_format_v])
            handler.append([None])
            bbox.append([None])
            tbox.append([None])
            crs.append([None])
        else:
            filename.append([i])
            file_format.append([file.get("format")])
            handler_v = file.get("geoextent_handler")
            bbox_v = file.get("bbox")
            tbox_v = file.get("tbox")
            crs_v = file.get("crs")
            handler.append([handler_v])
            bbox.append([bbox_v])
            tbox.append([tbox_v])
            crs.append([crs_v])

            if file.get("format") == "folder":
                details_folder = extract_details(file["details"])
                filename.append(details_folder["filename"])
                file_format.append(details_folder["format"])
                handler.append(details_folder["handler"])
                bbox.append(details_folder["bbox"])
                tbox.append(details_folder["tbox"])
                crs.append(details_folder["crs"])

    if any(isinstance(i, list) for i in filename):
        filename = list(itertools.chain.from_iterable(filename))
        file_format = list(itertools.chain.from_iterable(file_format))
        handler = list(itertools.chain.from_iterable(handler))
        bbox = list(itertools.chain.from_iterable(bbox))
        tbox = list(itertools.chain.from_iterable(tbox))
        crs = list(itertools.chain.from_iterable(crs))

    d = {
        "filename": filename,
        "format": file_format,
        "handler": handler,
        "bbox": bbox,
        "tbox": tbox,
        "crs": crs,
    }
    files = pd.DataFrame(d)
    return files


def extract_output(result, files, current_version):
    """
    Function purpose: Extracts final output from geoextent including all files and containing folder
    result: geoextent output from extraction
    files: user input for initial extraction (e.g name of the main folder)
    current_version: Current geoextent version
    Output: Dataframe with geoextent of all files AND final output (merge) of user request
    """
    filename = files
    file_format = result.get("format")
    handler = "geoextent:" + current_version
    bbox = result.get("bbox")
    tbox = result.get("tbox")
    crs = result.get("crs")

    new_row = {
        "filename": filename,
        "format": file_format,
        "handler": handler,
        "bbox": bbox,
        "tbox": tbox,
        "crs": crs,
    }

    df = extract_details(result["details"])
    df = df.append(new_row, ignore_index=True)
    df["bbox"] = df["bbox"].apply(transform_bbox)
    df["tbox"] = df["tbox"].apply(transform_tbox)
    return df


def is_doi(val):
    """
    Function purpose: Returns None if val doesn't match pattern of a DOI.
    http://en.wikipedia.org/wiki/Digital_object_identifier.
    """
    return doi_regexp.match(val)


def normalize_doi(val):
    """
    Function purpose: Return just the DOI (e.g. 10.1234/jshd123)
    from a val that could include a url or doi
    (e.g. https://doi.org/10.1234/jshd123)
    val: DOI or URL (str)
    """
    m = doi_regexp.match(val)
    return m.group(2)


def create_geopackage(df, filename):
    """
    Function purpose: Creates a geopackage file
    df: dataframe from extract_output result
    filename: Name for the Geopackage file
    """
    sr4326 = osr.SpatialReference()
    sr4326.ImportFromEPSG(WGS84_EPSG_ID)

    if os.path.exists(filename):
        os.remove(filename)
        logger.warning("Overwriting {} ".format(filename))

    ds = ogr.GetDriverByName("GPKG").CreateDataSource(filename)
    lyr = ds.CreateLayer("files", geom_type=ogr.wkbPolygon, srs=sr4326)
    lyr.CreateField(ogr.FieldDefn("filename", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("handler", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("format", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("tbox", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("crs", ogr.OFTString))

    for i in range(len(df)):
        feat = ogr.Feature(lyr.GetLayerDefn())
        feat["filename"] = df.loc[i, "filename"]
        feat["format"] = df.loc[i, "format"]
        feat["tbox"] = df.loc[i, "tbox"]
        feat["handler"] = df.loc[i, "handler"]
        feat["crs"] = df.loc[i, "crs"]
        if df.loc[i, "bbox"] is not None:
            feat.SetGeometry(ogr.CreateGeometryFromWkt(df.loc[i, "bbox"]))
        lyr.CreateFeature(feat)

    ds = None


def path_output(path):

    if os.path.isdir(path):
        logger.error("Output must be a file, not a directory ")
        raise ValueError("Output must be a file, not a directory: {}".format(path))

    folder_path = os.path.split(path)[0]
    user_path = Path(folder_path)
    if user_path.exists():
        absolute_file_path = user_path.as_posix() + "/" + os.path.split(path)[1]
    else:
        logger.error("Output target directory does not exist: {}".format(path))
        raise ValueError("Output target directory does not exist: {}".format(path))
    return absolute_file_path


def is_geometry_a_point(bbox, is_convex_hull=False, tolerance=1e-6):
    """
    Determine if a geometry is actually a point (all coordinates are the same within tolerance)

    Args:
        bbox: Bounding box or coordinates in various formats
        is_convex_hull: Whether this is a convex hull geometry
        tolerance: Tolerance for coordinate comparison (default 1e-6)

    Returns:
        tuple: (is_point, point_coords) where is_point is bool and point_coords is [x, y] or None
    """
    if isinstance(bbox, dict) and bbox.get("type") == "Polygon":
        # GeoJSON polygon format - check if all coordinates are the same
        try:
            coords = bbox["coordinates"][0]  # Get outer ring
            if len(coords) < 2:
                return False, None

            # Check if all coordinates are the same within tolerance
            first_coord = coords[0]
            for coord in coords[1:]:
                if abs(coord[0] - first_coord[0]) > tolerance or abs(coord[1] - first_coord[1]) > tolerance:
                    return False, None

            return True, first_coord[:2]  # Return just [x, y]
        except (KeyError, IndexError, TypeError):
            return False, None

    elif is_convex_hull and isinstance(bbox, list) and len(bbox) > 0 and isinstance(bbox[0], list):
        # Convex hull coordinates format - check if all points are the same
        try:
            if len(bbox) < 2:
                return False, None

            first_coord = bbox[0]
            for coord in bbox[1:]:
                if abs(coord[0] - first_coord[0]) > tolerance or abs(coord[1] - first_coord[1]) > tolerance:
                    return False, None

            return True, first_coord[:2]  # Return just [x, y]
        except (IndexError, TypeError):
            return False, None

    elif isinstance(bbox, list) and len(bbox) == 4:
        # Regular bounding box [minx, miny, maxx, maxy]
        try:
            minx, miny, maxx, maxy = bbox
            if abs(minx - maxx) <= tolerance and abs(miny - maxy) <= tolerance:
                # All coordinates are the same within tolerance - it's a point
                return True, [minx, miny]
            return False, None
        except (ValueError, TypeError):
            return False, None

    return False, None


def create_geojson_feature_collection(extent_output):
    """
    Convert geoextent output to a valid GeoJSON FeatureCollection

    Args:
        extent_output: Dict containing the geoextent output

    Returns:
        Dict containing a GeoJSON FeatureCollection with a single Feature
    """
    if not extent_output or not extent_output.get("bbox"):
        return extent_output

    bbox = extent_output.get("bbox")
    is_convex_hull = extent_output.get("convex_hull", False)

    # Check if the geometry is actually a point
    is_point, point_coords = is_geometry_a_point(bbox, is_convex_hull)

    if is_point and point_coords:
        # Log warning that we're creating a point geometry instead of requested polygon
        if is_convex_hull:
            logger.warning(
                f"Geometry at {point_coords} is a single point, creating Point geometry instead of convex hull"
            )
        else:
            logger.warning(
                f"Geometry at {point_coords} is a single point, creating Point geometry instead of bounding box"
            )

        # Create Point geometry
        geom = {"type": "Point", "coordinates": point_coords}
    else:
        # Convert bbox to GeoJSON geometry format (existing logic)
        if isinstance(bbox, dict) and bbox.get("type") == "Polygon":
            # Already in GeoJSON format
            geom = bbox
        elif (
            is_convex_hull
            and isinstance(bbox, list)
            and len(bbox) > 0
            and isinstance(bbox[0], list)
        ):
            # Handle convex hull coordinates (array of [x,y] points)
            geom = convex_hull_coords_to_geojson(bbox)
        elif isinstance(bbox, list) and len(bbox) == 4:
            # Handle regular bounding box [min_x, min_y, max_x, max_y]
            geom = bbox_to_geojson(bbox)
        else:
            # Fallback: return original output if bbox format is not recognized
            return extent_output

    # Create properties from metadata
    properties = {}

    # Add all original properties except bbox and details
    for key, value in extent_output.items():
        if key not in ["bbox", "details"]:
            properties[key] = value

    # Add descriptive properties
    if is_point:
        properties["extent_type"] = "point"
        properties["description"] = "Point geometry extracted by geoextent"
    else:
        properties["extent_type"] = "convex_hull" if is_convex_hull else "bounding_box"
        properties["description"] = (
            f"{'Convex hull' if is_convex_hull else 'Bounding box'} extracted by geoextent"
        )

    # Add placename if available
    if "placename" in extent_output:
        properties["placename"] = extent_output["placename"]

    # Create the Feature
    feature = {"type": "Feature", "geometry": geom, "properties": properties}

    # Create the FeatureCollection
    feature_collection = {"type": "FeatureCollection", "features": [feature]}

    # Add details as a separate property if present (for directory/multiple file processing)
    if "details" in extent_output:
        feature_collection["details"] = extent_output["details"]

    return feature_collection


def format_extent_output(extent_output, output_format="geojson"):
    """
    Convert geoextent output to different formats

    Args:
        extent_output: Dict containing the geoextent output
        output_format: String specifying the output format ("geojson", "wkt", "wkb")

    Returns:
        Dict with formatted output - for GeoJSON format, returns a FeatureCollection
    """
    if not extent_output:
        return extent_output

    # For GeoJSON format, create a proper FeatureCollection
    if output_format.lower() == "geojson" and extent_output.get("bbox"):
        return create_geojson_feature_collection(extent_output)

    # For other formats or when no bbox present, use the original logic
    if not extent_output.get("bbox"):
        return extent_output

    # Work with a copy to avoid modifying the original
    formatted_output = extent_output.copy()

    bbox = extent_output.get("bbox")
    is_convex_hull = extent_output.get("convex_hull", False)

    if bbox:
        if (
            is_convex_hull
            and isinstance(bbox, list)
            and len(bbox) > 0
            and isinstance(bbox[0], list)
        ):
            # Handle convex hull coordinates (array of [x,y] points)
            if output_format.lower() == "wkt":
                formatted_output["bbox"] = convex_hull_coords_to_wkt(bbox)
            elif output_format.lower() == "wkb":
                formatted_output["bbox"] = convex_hull_coords_to_wkb(bbox)
        elif isinstance(bbox, dict) and bbox.get("type") == "Polygon":
            # Handle GeoJSON polygon format (from convex hull)
            if output_format.lower() == "wkt":
                # Convert GeoJSON polygon coordinates to WKT
                coords = bbox["coordinates"][0]
                formatted_output["bbox"] = convex_hull_coords_to_wkt(coords)
            elif output_format.lower() == "wkb":
                # Convert GeoJSON polygon coordinates to WKB
                coords = bbox["coordinates"][0]
                formatted_output["bbox"] = convex_hull_coords_to_wkb(coords)
        elif isinstance(bbox, list) and len(bbox) == 4:
            # Handle regular bounding box [min_x, min_y, max_x, max_y]
            if output_format.lower() == "wkt":
                formatted_output["bbox"] = bbox_to_wkt(bbox)
            elif output_format.lower() == "wkb":
                formatted_output["bbox"] = bbox_to_wkb(bbox)

    # Handle details if present (for directories/multiple files)
    if "details" in formatted_output and isinstance(formatted_output["details"], dict):
        for key, detail in formatted_output["details"].items():
            if isinstance(detail, dict):
                formatted_output["details"][key] = format_extent_output(
                    detail, output_format
                )

    return formatted_output


def bbox_to_wkt(bbox):
    """
    Convert bounding box coordinates to WKT POLYGON format

    Args:
        bbox: List of [minx, miny, maxx, maxy]

    Returns:
        String containing WKT polygon representation
    """
    if not bbox or len(bbox) != 4:
        return None

    minx, miny, maxx, maxy = bbox
    wkt = f"POLYGON(({minx} {miny},{maxx} {miny},{maxx} {maxy},{minx} {maxy},{minx} {miny}))"
    return wkt


def bbox_to_wkb(bbox):
    """
    Convert bounding box coordinates to WKB (Well-Known Binary) format

    Args:
        bbox: List of [minx, miny, maxx, maxy]

    Returns:
        String containing hexadecimal WKB representation
    """
    if not bbox or len(bbox) != 4:
        return None

    # Create WKT first, then convert to WKB using OGR
    wkt = bbox_to_wkt(bbox)
    if wkt:
        geom = ogr.CreateGeometryFromWkt(wkt)
        if geom:
            return geom.ExportToWkb().hex().upper()
    return None


def bbox_to_geojson(bbox):
    """
    Convert bounding box coordinates to GeoJSON Polygon format

    Args:
        bbox: List of [minx, miny, maxx, maxy] (WGS84 coordinates)

    Returns:
        Dict containing GeoJSON polygon representation
    """
    if not bbox or len(bbox) != 4:
        return None

    minx, miny, maxx, maxy = bbox

    # Create a polygon from the bounding box (GeoJSON format: [longitude, latitude])
    coordinates = [
        [[minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny]]
    ]

    return {"type": "Polygon", "coordinates": coordinates}


def geojson_to_bbox(geojson_geom):
    """
    Extract bounding box from GeoJSON geometry

    Args:
        geojson_geom: GeoJSON geometry object

    Returns:
        List of [minx, miny, maxx, maxy] or None
    """
    if not geojson_geom or "coordinates" not in geojson_geom:
        return None

    coords = geojson_geom["coordinates"]

    # Flatten all coordinates to find bounds
    all_coords = []

    def flatten_coords(coord_array):
        if isinstance(coord_array, list):
            if len(coord_array) == 2 and isinstance(coord_array[0], (int, float)):
                # This is a coordinate pair [x, y]
                all_coords.append(coord_array)
            else:
                # This is a nested array, recurse
                for item in coord_array:
                    flatten_coords(item)

    flatten_coords(coords)

    if not all_coords:
        return None

    # Extract x and y coordinates
    x_coords = [coord[0] for coord in all_coords]
    y_coords = [coord[1] for coord in all_coords]

    return [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]


def create_spatial_extent(geometry, crs="4326", extent_type="bounding_box"):
    """
    Create a standardized spatial extent structure

    Args:
        geometry: GeoJSON geometry object
        crs: Coordinate reference system (default "4326")
        extent_type: Type of extent ("bounding_box" or "convex_hull")

    Returns:
        Standardized spatial extent dictionary
    """
    bbox = geojson_to_bbox(geometry)

    return {
        "geometry": geometry,
        "bbox": bbox,
        "crs": crs,
        "extent_type": extent_type
    }


def coords_to_geojson_polygon(coords):
    """
    Convert coordinate array to GeoJSON Polygon

    Args:
        coords: Array of [x, y] coordinate pairs

    Returns:
        GeoJSON Polygon geometry
    """
    if not coords or len(coords) < 3:
        return None

    # Ensure the polygon is closed
    if coords[0] != coords[-1]:
        coords = coords + [coords[0]]

    return {
        "type": "Polygon",
        "coordinates": [coords]
    }


def convex_hull_coords_to_wkt(coords):
    """
    Convert convex hull coordinates to WKT POLYGON format

    Args:
        coords: List of [x,y] coordinate pairs representing convex hull vertices

    Returns:
        String containing WKT polygon representation
    """
    if not coords or len(coords) < 3:
        return None

    # Ensure the polygon is closed (first and last points should be the same)
    if coords[0] != coords[-1]:
        coords = coords + [coords[0]]

    # Format coordinates as "x y" pairs
    coord_strs = [f"{x} {y}" for x, y in coords]
    wkt = f"POLYGON(({','.join(coord_strs)}))"
    return wkt


def convex_hull_coords_to_wkb(coords):
    """
    Convert convex hull coordinates to WKB (Well-Known Binary) format

    Args:
        coords: List of [x,y] coordinate pairs representing convex hull vertices

    Returns:
        String containing hexadecimal WKB representation
    """
    if not coords or len(coords) < 3:
        return None

    try:
        # Create a geometry from the convex hull coordinates
        ring = ogr.Geometry(ogr.wkbLinearRing)

        # Ensure the polygon is closed
        if coords[0] != coords[-1]:
            coords = coords + [coords[0]]

        for x, y in coords:
            ring.AddPoint(x, y)

        # Create polygon
        polygon = ogr.Geometry(ogr.wkbPolygon)
        polygon.AddGeometry(ring)

        # Convert to WKB and then to hex string
        wkb_bytes = polygon.ExportToWkb()
        return wkb_bytes.hex().upper()

    except Exception as e:
        logger.debug(f"Error converting convex hull coords to WKB: {e}")
        return None


def convex_hull_coords_to_geojson(coords):
    """
    Convert convex hull coordinates to GeoJSON Polygon format

    Args:
        coords: List of [x,y] coordinate pairs representing convex hull vertices

    Returns:
        Dict containing GeoJSON polygon representation
    """
    if not coords or len(coords) < 3:
        return None

    # Ensure the polygon is closed (first and last points should be the same)
    coordinates = coords[:]
    if coordinates[0] != coordinates[-1]:
        coordinates.append(coordinates[0])

    return {"type": "Polygon", "coordinates": [coordinates]}


def parse_download_size(size_string):
    """
    Parse a download size string using filesizelib

    Args:
        size_string: Size string like '100MB', '2GB', etc.

    Returns:
        int: Size in bytes, or None if parsing fails
    """
    if size_string is None:
        return None

    try:
        import filesizelib
        storage = filesizelib.Storage.parse(size_string)
        return int(storage.convert_to_bytes())
    except Exception as e:
        logger.warning(f"Failed to parse download size '{size_string}': {e}")
        return None


def _group_shapefile_components(files_info):
    """
    Group shapefile components together so they stay together during selection.

    Args:
        files_info: List of file dicts with 'name' and 'size' keys

    Returns:
        tuple: (shapefile_groups, standalone_files)
            - shapefile_groups: List of lists, each inner list contains related shapefile components
            - standalone_files: List of individual files that are not part of shapefiles
    """
    import os

    # Common shapefile extensions
    shapefile_extensions = {'.shp', '.shx', '.dbf', '.prj', '.sbn', '.sbx', '.cpg', '.shp.xml'}

    # Group files by base name (without extension)
    groups = {}
    standalone_files = []

    for file_info in files_info:
        filename = file_info.get('name', '')

        # Handle .shp.xml extension specially
        if filename.endswith('.shp.xml'):
            base_name = filename[:-8]  # Remove .shp.xml
            extension = '.shp.xml'
        else:
            base_name, extension = os.path.splitext(filename)

        if extension.lower() in shapefile_extensions:
            # This is a shapefile component
            if base_name not in groups:
                groups[base_name] = []
            groups[base_name].append(file_info)
        else:
            # Standalone file
            standalone_files.append(file_info)

    # Convert groups to list of lists, only include groups with multiple components
    shapefile_groups = []
    for base_name, components in groups.items():
        if len(components) > 1:
            # Sort components by extension to have consistent ordering
            components.sort(key=lambda f: f.get('name', ''))
            shapefile_groups.append(components)
        else:
            # Single component, treat as standalone
            standalone_files.extend(components)

    return shapefile_groups, standalone_files


def filter_files_by_size(
    files_info: list,
    max_download_size: int,
    method: str = "ordered",
    seed: int = DEFAULT_DOWNLOAD_SAMPLE_SEED
):
    """
    Filter files based on cumulative download size limit and selection method.

    The max_download_size applies to the total of all files combined, not individual files.
    Files are selected until the cumulative total would exceed the limit.

    Args:
        files_info: List of dicts with 'name' and 'size' keys (size in bytes)
        max_download_size: Maximum cumulative download size in bytes for all files combined
        method: Selection method - 'ordered' or 'random'
        seed: Random seed for reproducible random selection

    Returns:
        tuple: (selected_files, total_size, skipped_files)
    """
    if not files_info or max_download_size is None:
        return files_info, sum(f.get('size', 0) for f in files_info), []

    # Filter out files without size information
    files_with_size = [f for f in files_info if f.get('size') is not None and f.get('size') > 0]
    files_without_size = [f for f in files_info if f.get('size') is None or f.get('size') <= 0]

    # Group shapefile components together to ensure they stay together
    shapefile_groups, standalone_files = _group_shapefile_components(files_with_size)

    # Apply selection method to groups and standalone files
    all_items = shapefile_groups + standalone_files

    if method == "random":
        # Set seed for reproducible results
        random.seed(seed)
        random.shuffle(all_items)
    # For "ordered" method, items are processed in original order

    selected_files = []
    total_size = 0
    skipped_items = []

    # Select items that fit within the cumulative size limit
    # Stop as soon as adding the next item would exceed the limit
    for item in all_items:
        if isinstance(item, list):
            # Shapefile group - all components stay together
            group_size = sum(f.get('size', 0) for f in item)
            if total_size + group_size <= max_download_size:
                selected_files.extend(item)
                total_size += group_size
                group_names = [f.get('name', 'unknown') for f in item]
                logger.debug(f"Selected shapefile group ({', '.join(group_names)}): {group_size:,} bytes")
            else:
                # This group would exceed the cumulative limit, skip it and all remaining items
                skipped_items.extend(item)
                for remaining_item in all_items[all_items.index(item) + 1:]:
                    if isinstance(remaining_item, list):
                        skipped_items.extend(remaining_item)
                    else:
                        skipped_items.append(remaining_item)
                logger.debug(f"Cumulative limit reached. Skipping shapefile group and remaining files.")
                break
        else:
            # Individual file
            file_size = item.get('size', 0)
            if total_size + file_size <= max_download_size:
                selected_files.append(item)
                total_size += file_size
                logger.debug(f"Selected file {item.get('name', 'unknown')}: {file_size:,} bytes")
            else:
                # This file would exceed the cumulative limit, skip it and all remaining items
                skipped_items.append(item)
                for remaining_item in all_items[all_items.index(item) + 1:]:
                    if isinstance(remaining_item, list):
                        skipped_items.extend(remaining_item)
                    else:
                        skipped_items.append(remaining_item)
                logger.debug(f"Cumulative limit reached. Skipping file and remaining files.")
                break

    # Add files without size info (these will be handled by individual providers)
    # Note: These are added to selected files but not counted toward the size limit
    selected_files.extend(files_without_size)

    if skipped_items:
        logger.info(f"Cumulative download size limit reached ({max_download_size:,} bytes).")
        logger.info(f"Selected {len(selected_files)} files totaling {total_size:,} bytes ({total_size / (1024*1024):.1f} MB)")
        logger.info(f"Skipped {len(skipped_items)} files due to cumulative size limit.")

    return selected_files, total_size, skipped_items


def generate_geojsonio_url(extent_output):
    """
    Generate a geojson.io URL for the spatial extent
    Always uses GeoJSON format regardless of the output format requested

    Args:
        extent_output: Dict containing the geoextent output with bbox data

    Returns:
        String containing the geojson.io URL, or None if no spatial extent available
    """

    if not extent_output or not extent_output.get("bbox"):
        return None

    # Force conversion to GeoJSON format for geojsonio URL generation
    # This ensures that regardless of the requested output format (WKT, WKB, etc.),
    # the geojsonio URL will always display proper GeoJSON geometry
    geojson_output = format_extent_output(extent_output, "geojson")

    # The format_extent_output function will return a FeatureCollection for GeoJSON format
    if geojson_output and geojson_output.get("type") == "FeatureCollection":
        try:
            # Generate URL using geojsonio
            geojson_string = json.dumps(geojson_output)
            url = geojsonio.make_url(geojson_string)
            return url
        except Exception as e:
            logger = logging.getLogger("geoextent")
            logger.warning(f"Error generating geojson.io URL: {e}")
            return None

    # Fallback to original logic for cases where format_extent_output doesn't return FeatureCollection
    bbox = extent_output.get("bbox")
    is_convex_hull = extent_output.get("convex_hull", False)

    # Convert bbox to GeoJSON format
    if (
        is_convex_hull
        and isinstance(bbox, list)
        and len(bbox) > 0
        and isinstance(bbox[0], list)
    ):
        # Handle convex hull coordinates
        geojson_geom = convex_hull_coords_to_geojson(bbox)
    elif isinstance(bbox, list) and len(bbox) == 4:
        # Handle regular bounding box
        geojson_geom = bbox_to_geojson(bbox)
    else:
        return None

    if not geojson_geom:
        return None

    try:
        # Create a feature with the geometry
        feature = {
            "type": "Feature",
            "geometry": geojson_geom,
            "properties": {
                "name": "Geoextent Spatial Extent",
                "description": f"{'Convex Hull' if is_convex_hull else 'Bounding Box'} extracted by geoextent",
            },
        }

        # Create a feature collection
        feature_collection = {"type": "FeatureCollection", "features": [feature]}

        # Generate URL using geojsonio
        geojson_string = json.dumps(feature_collection)
        url = geojsonio.make_url(geojson_string)

        return url
    except Exception as e:
        logger = logging.getLogger("geoextent")
        logger.warning(f"Error generating geojson.io URL: {e}")
        return None
