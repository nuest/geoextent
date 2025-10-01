import csv
import logging
import re
from osgeo import gdal, ogr
from . import helpfunctions as hf

logger = logging.getLogger("geoextent")

search = {
    "longitude": [
        "(.)*longitude",
        "(.)*long(.)*",
        "^lon",
        "lon$",
        "(.)*lng(.)*",
        "^x",
        "x$",
    ],
    "latitude": ["(.)*latitude(.)*", "^lat", "lat$", "^y", "y$"],
    "geometry": [
        "(.)*geometry(.)*",
        "(.)*geom(.)*",
        "^wkt",
        "wkt$",
        "(.)*wkt(.)*",
        "^wkb",
        "wkb$",
        "(.)*wkb(.)*",
        "(.)*coordinates(.)*",
        "(.)*coords(.)*",
        "^coords",
        "coords$",
        "^coordinates",
        "coordinates$",
    ],
    "time": ["(.)*timestamp(.)*", "(.)*datetime(.)*", "(.)*time(.)*", "date$", "^date"],
}


def get_handler_name():
    return "handleCSV"


def checkFileSupported(filepath):
    """Checks whether it is valid CSV or not. \n
    input "path": type string, path to file which shall be extracted \n
    raise exception if not valid
    """

    try:
        file = gdal.OpenEx(filepath)
        driver = file.GetDriver().ShortName
    except Exception:
        logger.debug("File {} is NOT supported by HandleCSV module".format(filepath))
        return False

    if driver == "CSV":
        with open(filepath) as csv_file:
            try:
                delimiter = hf.getDelimiter(csv_file)
                data = csv.reader(csv_file.readlines(10000), delimiter=delimiter)
            except UnicodeDecodeError:
                # exception to prevent this error:
                # UnicodeDecodeError: 'utf-8' codec can't decode byte 0x8a in position 187: invalid start byte
                data = None
            except ValueError:
                # exception to prevent this error:
                # ValueError: bad delimiter or quotechar value
                data = None
            except csv.Error:
                # exception to prevent this error:
                # _csv.Error: Could not determine delimiter
                data = None
            except Exception:
                data = None
            if data is None:
                logger.debug(
                    "File {} is NOT supported by HandleCSV module".format(filepath)
                )
                return False
            else:
                logger.debug(
                    "File {} is supported by HandleCSV module".format(filepath)
                )
                return True
    else:
        return False


def _extract_bbox_from_geometry_column(filePath, chunk_size=50000):
    """
    Extract bounding box from geometry column containing WKT data.
    input "filePath": type string, file path to csv file
    returns spatialExtent: type dict, contains bbox and crs
    """

    with open(filePath) as csv_file:
        delimiter = hf.getDelimiter(csv_file)
        data = csv.reader(csv_file, delimiter=delimiter)

        header = next(data)
        chunk = [header]

        # Find geometry column index
        geometry_col_idx = None
        for idx, col_name in enumerate(header):
            for pattern in search["geometry"]:
                p = re.compile(pattern, re.IGNORECASE)
                if p.search(col_name) is not None:
                    geometry_col_idx = idx
                    break
            if geometry_col_idx is not None:
                break

        if geometry_col_idx is None:
            return None

        min_x, min_y, max_x, max_y = (
            float("inf"),
            float("inf"),
            float("-inf"),
            float("-inf"),
        )

        for row in data:
            chunk.append(row)
            if len(chunk) >= chunk_size:
                # Process chunk
                for data_row in chunk[1:]:  # Skip header
                    if len(data_row) > geometry_col_idx:
                        geometry_wkt = data_row[geometry_col_idx]
                        if geometry_wkt and geometry_wkt.strip():
                            try:
                                geom = None
                                # Try parsing as WKT first
                                if (
                                    geometry_wkt.strip()
                                    .upper()
                                    .startswith(
                                        (
                                            "POINT",
                                            "LINESTRING",
                                            "POLYGON",
                                            "MULTIPOINT",
                                            "MULTILINESTRING",
                                            "MULTIPOLYGON",
                                            "GEOMETRYCOLLECTION",
                                        )
                                    )
                                ):
                                    geom = ogr.CreateGeometryFromWkt(geometry_wkt)
                                else:
                                    # Try parsing as WKB (hex-encoded)
                                    try:
                                        geom = ogr.CreateGeometryFromWkb(
                                            bytes.fromhex(geometry_wkt)
                                        )
                                    except (ValueError, TypeError):
                                        # If not hex, might be binary WKB
                                        try:
                                            geom = ogr.CreateGeometryFromWkb(
                                                geometry_wkt.encode()
                                            )
                                        except:
                                            # Last resort: try as WKT anyway
                                            geom = ogr.CreateGeometryFromWkt(
                                                geometry_wkt
                                            )

                                if geom:
                                    envelope = geom.GetEnvelope()
                                    # envelope returns (minX, maxX, minY, maxY)
                                    min_x = min(min_x, envelope[0])
                                    max_x = max(max_x, envelope[1])
                                    min_y = min(min_y, envelope[2])
                                    max_y = max(max_y, envelope[3])
                            except Exception as e:
                                logger.debug(
                                    f"Failed to parse geometry: {geometry_wkt}, error: {e}"
                                )
                                continue

                chunk = [header]

        # Process remaining chunk
        if len(chunk) > 1:
            for data_row in chunk[1:]:  # Skip header
                if len(data_row) > geometry_col_idx:
                    geometry_wkt = data_row[geometry_col_idx]
                    if geometry_wkt and geometry_wkt.strip():
                        try:
                            geom = None
                            # Try parsing as WKT first
                            if (
                                geometry_wkt.strip()
                                .upper()
                                .startswith(
                                    (
                                        "POINT",
                                        "LINESTRING",
                                        "POLYGON",
                                        "MULTIPOINT",
                                        "MULTILINESTRING",
                                        "MULTIPOLYGON",
                                        "GEOMETRYCOLLECTION",
                                    )
                                )
                            ):
                                geom = ogr.CreateGeometryFromWkt(geometry_wkt)
                            else:
                                # Try parsing as WKB (hex-encoded)
                                try:
                                    geom = ogr.CreateGeometryFromWkb(
                                        bytes.fromhex(geometry_wkt)
                                    )
                                except (ValueError, TypeError):
                                    # If not hex, might be binary WKB
                                    try:
                                        geom = ogr.CreateGeometryFromWkb(
                                            geometry_wkt.encode()
                                        )
                                    except:
                                        # Last resort: try as WKT anyway
                                        geom = ogr.CreateGeometryFromWkt(geometry_wkt)

                            if geom:
                                envelope = geom.GetEnvelope()
                                min_x = min(min_x, envelope[0])
                                max_x = max(max_x, envelope[1])
                                min_y = min(min_y, envelope[2])
                                max_y = max(max_y, envelope[3])
                        except Exception as e:
                            logger.debug(
                                f"Failed to parse geometry: {geometry_wkt}, error: {e}"
                            )
                            continue

        if min_x != float("inf") and min_y != float("inf"):
            bbox = [min_x, min_y, max_x, max_y]
            logger.debug("Extracted Bounding box from geometry column: {}".format(bbox))
            return {"bbox": bbox, "crs": "4326"}  # Assume WGS84 for WKT data
        else:
            return None


def getBoundingBox(filePath, chunk_size=50000):
    """
    Function purpose: extracts the spatial extent (bounding box) from a csv-file \n
    input "filepath": type string, file path to csv file \n
    returns spatialExtent: type list, length = 4 , type = float, schema = [min(longs), min(lats), max(longs), max(lats)]
    """

    # First, try to extract from geometry column (WKT data)
    geometry_extent = _extract_bbox_from_geometry_column(filePath, chunk_size)
    if geometry_extent:
        return geometry_extent

    # Fall back to traditional coordinate column extraction
    with open(filePath) as csv_file:
        delimiter = hf.getDelimiter(csv_file)
        data = csv.reader(csv_file, delimiter=delimiter)

        header = next(data)
        chunk = [header]

        spatial_extent = {
            "min_lat": [],
            "max_lat": [],
            "min_lon": [],
            "max_lon": [],
        }

        for x in data:
            chunk.append(x)
            if len(chunk) >= chunk_size:
                spatial_lat_extent = hf.searchForParameters(
                    chunk, search["latitude"], exp_data="numeric"
                )
                spatial_lon_extent = hf.searchForParameters(
                    chunk, search["longitude"], exp_data="numeric"
                )

                if not spatial_lat_extent and not spatial_lon_extent:
                    raise Exception(
                        "The csv file from " + filePath + " has no BoundingBox"
                    )
                else:
                    spatial_extent["min_lat"].append(min(spatial_lat_extent))
                    spatial_extent["max_lat"].append(max(spatial_lat_extent))
                    spatial_extent["min_lon"].append(min(spatial_lon_extent))
                    spatial_extent["max_lon"].append(max(spatial_lon_extent))

                chunk = [header]

        if len(chunk) > 1:
            spatial_lat_extent = hf.searchForParameters(
                chunk, search["latitude"], exp_data="numeric"
            )
            spatial_lon_extent = hf.searchForParameters(
                chunk, search["longitude"], exp_data="numeric"
            )

            if not spatial_lat_extent and not spatial_lon_extent:
                raise Exception("The csv file from " + filePath + " has no BoundingBox")
            else:
                spatial_extent["min_lat"].append(min(spatial_lat_extent))
                spatial_extent["max_lat"].append(max(spatial_lat_extent))
                spatial_extent["min_lon"].append(min(spatial_lon_extent))
                spatial_extent["max_lon"].append(max(spatial_lon_extent))

        bbox = [
            min(spatial_extent["min_lon"]),
            min(spatial_extent["min_lat"]),
            max(spatial_extent["max_lon"]),
            max(spatial_extent["max_lat"]),
        ]

        logger.debug("Extracted Bounding box (without projection): {}".format(bbox))
        crs = getCRS(filePath, chunk_size)
        logger.debug("Extracted CRS: {}".format(crs))
        spatialExtent = {"bbox": bbox, "crs": crs}
        if not bbox or not crs:
            raise Exception("Bounding box could not be extracted")

    return spatialExtent


def getTemporalExtent(filepath, num_sample):
    """extract time extent from csv string \n
    input "filePath": type string, file path to csv File \n
    returns temporal extent of the file: type list, length = 2, both entries have the type str, temporalExtent[0] <= temporalExtent[1]
    """

    with open(filepath) as csv_file:
        delimiter = hf.getDelimiter(csv_file)
        data = csv.reader(csv_file, delimiter=delimiter)

        elements = []
        for x in data:
            elements.append(x)

        all_temporal_extent = hf.searchForParameters(
            elements, search["time"], exp_data="time"
        )
        if all_temporal_extent is None:
            raise Exception("The csv file from " + filepath + " has no TemporalExtent")
        else:
            tbox = []
            parsed_time = hf.date_parser(all_temporal_extent, num_sample=num_sample)

            if parsed_time is not None:
                # Min and max into ISO8601 format ('%Y-%m-%d')
                tbox.append(min(parsed_time).strftime("%Y-%m-%d"))
                tbox.append(max(parsed_time).strftime("%Y-%m-%d"))
            else:
                raise Exception(
                    "The csv file from "
                    + filepath
                    + " has no recognizable TemporalExtent"
                )
            return tbox


def getCRS(filepath, chunk_size=50000):
    """extracts coordinatesystem from csv File \n
    input "filepath": type string, file path to csv file \n
    returns the epsg code of the used coordinate reference system, type list, contains extracted coordinate system of content from csv file
    """

    with open(filepath) as csv_file:
        delimiter = hf.getDelimiter(csv_file)
        data = csv.reader(csv_file, delimiter=delimiter)

        header = next(data)
        chunk = [header]

        crs = []

        for x in data:
            chunk.append(x)
            if len(chunk) >= chunk_size:
                param = hf.searchForParameters(chunk, ["crs", "srsID", "EPSG"])
                if param:
                    crs.extend(param)

                chunk = [header]

        if len(chunk) > 1:
            param = hf.searchForParameters(chunk, ["crs", "srsID", "EPSG"])
            if param:
                crs.extend(param)

        if not crs:
            logger.debug(
                "{} : There is no identifiable coordinate reference system. We will try to use EPSG: 4326".format(
                    filepath
                )
            )
            crs = "4326"
        elif len(list(set(crs))) > 1:
            logger.debug(
                "{} : Coordinate reference system of the file is ambiguous. Extraction is not possible.".format(
                    filepath
                )
            )
            raise Exception("The csv file from " + filepath + " has no CRS")
        else:
            crs = str(list(set(crs))[0])

        return crs
