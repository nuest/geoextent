import csv
import logging
import os
import re
from osgeo import gdal, ogr
from . import helpfunctions as hf

logger = logging.getLogger("geoextent")

# Column name patterns for GDAL CSV open options.
# These are comma-separated lists used with X_POSSIBLE_NAMES, Y_POSSIBLE_NAMES,
# and GEOM_POSSIBLE_NAMES to let GDAL auto-detect coordinate/geometry columns.
# See https://gdal.org/drivers/vector/csv.html
_GDAL_X_NAMES = "Longitude,Long,Lon,Lng,X,Easting"
_GDAL_Y_NAMES = "Latitude,Lat,Y,Northing"
_GDAL_GEOM_NAMES = "geometry,geom,the_geom,wkt,WKT,wkb,WKB,coordinates,coords"

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
        # Order matters: more specific patterns first to avoid false matches
        # e.g., "geometry" column should match before "geom_type" column
        "^geometry$",  # Exact match first
        "(.)*geometry(.)*",  # Then "geometry" substring
        "^wkt$",  # Exact WKT
        "(.)*wkt(.)*",  # WKT substring
        "^wkb$",  # Exact WKB
        "(.)*wkb(.)*",  # WKB substring
        "^coordinates$",  # Exact coordinates
        "^coordinates",  # Starts with coordinates
        "coordinates$",  # Ends with coordinates
        "(.)*coordinates(.)*",  # Coordinates substring
        "^coords$",  # Exact coords
        "^coords",  # Starts with coords
        "coords$",  # Ends with coords
        "(.)*coords(.)*",  # Coords substring
        "(.)*geom(.)*",  # Most general pattern last to avoid false positives
    ],
    "time": ["(.)*timestamp(.)*", "(.)*datetime(.)*", "(.)*time(.)*", "date$", "^date"],
}


def get_handler_name():
    return "handleCSV"


def get_handler_display_name():
    """Return human-readable name for this handler"""
    return "CSV (comma-separated values)"


def checkFileSupported(filepath):
    """Checks whether it is valid CSV or not. \n
    input "path": type string, path to file which shall be extracted \n
    raise exception if not valid
    """

    # Quick extension check - reject known vector/raster formats
    # This prevents CSV handler from trying to open XML-based formats
    extension = os.path.splitext(filepath)[1].lower()
    vector_extensions = {".kml", ".gml", ".gpx", ".shp", ".gpkg", ".geojson", ".json"}
    raster_extensions = {".tif", ".tiff", ".asc", ".jp2", ".png", ".jpg", ".jpeg"}

    if extension in vector_extensions or extension in raster_extensions:
        logger.debug(f"File {filepath} has extension {extension}, skipping CSV handler")
        return False

    try:
        # Force CSV driver to avoid GDAL treating coordinate data as gridded dataset
        file = gdal.OpenEx(filepath, allowed_drivers=["CSV"])
        if file:
            driver = file.GetDriver().ShortName
        else:
            logger.debug(
                "File {} is NOT supported by HandleCSV module".format(filepath)
            )
            return False
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


def _open_csv_via_gdal(filepath):
    """Open CSV with GDAL using coordinate column open options.

    Uses X_POSSIBLE_NAMES, Y_POSSIBLE_NAMES, and GEOM_POSSIBLE_NAMES to let
    GDAL auto-detect coordinate and geometry columns. Also picks up CSVT sidecar
    files automatically when present.

    Returns (dataset, layer) tuple, or (None, None) if detection fails.
    The caller is responsible for setting ds = None when done.
    """
    try:
        open_options = [
            "X_POSSIBLE_NAMES={}".format(_GDAL_X_NAMES),
            "Y_POSSIBLE_NAMES={}".format(_GDAL_Y_NAMES),
            "GEOM_POSSIBLE_NAMES={}".format(_GDAL_GEOM_NAMES),
            "KEEP_GEOM_COLUMNS=YES",
            "AUTODETECT_TYPE=YES",
        ]
        ds = gdal.OpenEx(
            filepath,
            gdal.OF_VECTOR,
            allowed_drivers=["CSV"],
            open_options=open_options,
        )
        if not ds:
            return None, None

        layer = ds.GetLayer(0)
        if layer is None or layer.GetGeomType() == ogr.wkbNone:
            ds = None
            return None, None

        if layer.GetFeatureCount() == 0:
            ds = None
            return None, None

        return ds, layer
    except Exception as e:
        logger.debug("GDAL CSV open options failed for {}: {}".format(filepath, e))
        return None, None


def _extract_bbox_via_gdal(filepath):
    """Try to extract bounding box using GDAL's CSV driver with open options.

    Returns dict with bbox and crs, or None if GDAL cannot detect geometry.
    """
    ds, layer = _open_csv_via_gdal(filepath)
    if ds is None:
        return None

    try:
        extent = layer.GetExtent()  # (minX, maxX, minY, maxY)
        bbox = [
            extent[0],
            extent[2],
            extent[1],
            extent[3],
        ]  # [minlon, minlat, maxlon, maxlat]

        crs = "4326"
        srs = layer.GetSpatialRef()
        if srs:
            try:
                srs.AutoIdentifyEPSG()
                code = srs.GetAuthorityCode(None)
                if code:
                    crs = code
            except Exception:
                pass

        ds = None
        logger.debug(
            "GDAL CSV driver extracted bbox {} with CRS {} from {}".format(
                bbox, crs, filepath
            )
        )
        return {"bbox": bbox, "crs": crs}
    except Exception as e:
        logger.debug(
            "GDAL CSV open options extraction failed for {}: {}".format(filepath, e)
        )
        ds = None
        return None


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

        # Find geometry column index - prioritize best match
        # Check all columns and find the one with the most specific pattern match
        geometry_col_idx = None
        best_pattern_priority = len(
            search["geometry"]
        )  # Lower number = higher priority

        for idx, col_name in enumerate(header):
            for pattern_priority, pattern in enumerate(search["geometry"]):
                p = re.compile(pattern, re.IGNORECASE)
                if p.search(col_name) is not None:
                    # Found a match - keep it if it's better (lower priority number) than current best
                    if pattern_priority < best_pattern_priority:
                        geometry_col_idx = idx
                        best_pattern_priority = pattern_priority
                        logger.debug(
                            f"Found geometry column candidate: '{col_name}' (index {idx}) matching pattern '{pattern}' (priority {pattern_priority})"
                        )
                    break  # Stop checking patterns for this column, move to next column

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

    # 1. Try GDAL CSV driver with open options (handles CSVT sidecars, GDAL column
    #    name conventions like X/Y/Easting/Northing, and GEOM_POSSIBLE_NAMES for WKT)
    gdal_extent = _extract_bbox_via_gdal(filePath)
    if gdal_extent:
        return gdal_extent

    # 2. Try extracting from geometry column via manual WKT/WKB parsing
    geometry_extent = _extract_bbox_from_geometry_column(filePath, chunk_size)
    if geometry_extent:
        return geometry_extent

    # 3. Fall back to traditional regex-based coordinate column extraction
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


def _parse_geometry_from_value(geometry_value):
    """Parse a geometry value (WKT or hex-encoded WKB) into an OGR geometry.

    Returns OGR Geometry object, or None if parsing fails.
    """
    if not geometry_value or not geometry_value.strip():
        return None

    try:
        geom = None
        # Try parsing as WKT first
        if (
            geometry_value.strip()
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
            geom = ogr.CreateGeometryFromWkt(geometry_value)
        else:
            # Try parsing as WKB (hex-encoded)
            try:
                geom = ogr.CreateGeometryFromWkb(bytes.fromhex(geometry_value))
            except (ValueError, TypeError):
                # If not hex, might be binary WKB
                try:
                    geom = ogr.CreateGeometryFromWkb(geometry_value.encode())
                except Exception:
                    # Last resort: try as WKT anyway
                    geom = ogr.CreateGeometryFromWkt(geometry_value)
        return geom
    except Exception:
        return None


def _extract_convex_hull_from_geometry_column(filePath):
    """Extract convex hull from geometry column containing WKT/WKB data.

    Similar to _extract_bbox_from_geometry_column but collects all OGR
    geometries and computes a convex hull instead of tracking min/max.

    Returns dict with bbox, crs, convex_hull_coords, convex_hull keys, or None.
    """
    with open(filePath) as csv_file:
        delimiter = hf.getDelimiter(csv_file)
        data = csv.reader(csv_file, delimiter=delimiter)

        header = next(data)

        # Find geometry column index (same logic as _extract_bbox_from_geometry_column)
        geometry_col_idx = None
        best_pattern_priority = len(search["geometry"])

        for idx, col_name in enumerate(header):
            for pattern_priority, pattern in enumerate(search["geometry"]):
                p = re.compile(pattern, re.IGNORECASE)
                if p.search(col_name) is not None:
                    if pattern_priority < best_pattern_priority:
                        geometry_col_idx = idx
                        best_pattern_priority = pattern_priority
                    break

        if geometry_col_idx is None:
            return None

        # Collect all geometries
        geom_collection = ogr.Geometry(ogr.wkbGeometryCollection)
        has_geometries = False

        for row in data:
            if len(row) > geometry_col_idx:
                geom = _parse_geometry_from_value(row[geometry_col_idx])
                if geom:
                    geom_collection.AddGeometry(geom)
                    has_geometries = True

        if not has_geometries:
            return None

        # Compute convex hull
        envelope = geom_collection.GetEnvelope()  # (minX, maxX, minY, maxY)
        min_x, max_x, min_y, max_y = envelope

        is_point = min_x == max_x and min_y == max_y

        if is_point:
            convex_hull_coords = [[min_x, min_y]]
            bbox = [min_x, min_y, max_x, max_y]
        else:
            convex_hull = geom_collection.ConvexHull()
            if convex_hull is None or convex_hull.GetGeometryType() != ogr.wkbPolygon:
                return None

            convex_hull_coords = []
            ring = convex_hull.GetGeometryRef(0)
            if ring is not None:
                for i in range(ring.GetPointCount()):
                    x, y, z = ring.GetPoint(i)
                    convex_hull_coords.append([x, y])

            hull_envelope = convex_hull.GetEnvelope()
            bbox = [
                hull_envelope[0],
                hull_envelope[2],
                hull_envelope[1],
                hull_envelope[3],
            ]

        logger.debug(
            "Extracted convex hull from geometry column: {} coords".format(
                len(convex_hull_coords)
            )
        )
        return {
            "bbox": bbox,
            "crs": "4326",
            "convex_hull_coords": convex_hull_coords,
            "convex_hull": True,
        }


def getConvexHull(filepath):
    """Extract convex hull from CSV file.

    Returns dict with 'bbox', 'crs', 'convex_hull_coords', 'convex_hull' keys,
    or None if convex hull cannot be computed.
    """
    # 1. Try GDAL CSV driver with open options
    ds, layer = _open_csv_via_gdal(filepath)
    if ds is not None:
        try:
            geometries = []
            for feature in layer:
                geom = feature.GetGeometryRef()
                if geom is not None:
                    geometries.append(geom.Clone())

            if not geometries:
                ds = None
                return None

            geom_collection = ogr.Geometry(ogr.wkbGeometryCollection)
            for geom in geometries:
                geom_collection.AddGeometry(geom)

            envelope = geom_collection.GetEnvelope()  # (minX, maxX, minY, maxY)
            min_x, max_x, min_y, max_y = envelope

            is_point = min_x == max_x and min_y == max_y

            if is_point:
                convex_hull_coords = [[min_x, min_y]]
                bbox = [min_x, min_y, max_x, max_y]
            else:
                convex_hull = geom_collection.ConvexHull()
                if (
                    convex_hull is None
                    or convex_hull.GetGeometryType() != ogr.wkbPolygon
                ):
                    ds = None
                    return None

                convex_hull_coords = []
                ring = convex_hull.GetGeometryRef(0)
                if ring is not None:
                    for i in range(ring.GetPointCount()):
                        x, y, z = ring.GetPoint(i)
                        convex_hull_coords.append([x, y])

                hull_envelope = convex_hull.GetEnvelope()
                bbox = [
                    hull_envelope[0],
                    hull_envelope[2],
                    hull_envelope[1],
                    hull_envelope[3],
                ]

            crs = "4326"
            srs = layer.GetSpatialRef()
            if srs:
                try:
                    srs.AutoIdentifyEPSG()
                    code = srs.GetAuthorityCode(None)
                    if code:
                        crs = code
                except Exception:
                    pass

            ds = None
            logger.debug(
                "GDAL CSV driver extracted convex hull with {} coords from {}".format(
                    len(convex_hull_coords), filepath
                )
            )
            return {
                "bbox": bbox,
                "crs": crs,
                "convex_hull_coords": convex_hull_coords,
                "convex_hull": True,
            }
        except Exception as e:
            logger.debug(
                "GDAL CSV convex hull extraction failed for {}: {}".format(filepath, e)
            )
            ds = None

    # 2. Try extracting from geometry column via manual WKT/WKB parsing
    geom_hull = _extract_convex_hull_from_geometry_column(filepath)
    if geom_hull:
        return geom_hull

    # 3. No convex hull possible — caller (compute_convex_hull_wgs84) will fall back
    return None


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
