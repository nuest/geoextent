import logging
import osgeo
from osgeo import ogr
from osgeo import gdal
from . import helpfunctions as hf
import re

null_island = [0] * 4
search = {
    "time": [
        "(.)*timestamp(.)*",
        "(.)*datetime(.)*",
        "(.)*time(.)*",
        "date$",
        "^date",
        "^begin",
    ]
}
logger = logging.getLogger("geoextent")


def get_handler_name():
    return "handleVector"


def get_handler_display_name():
    """Return human-readable name for this handler"""
    return "Vector data"


def _extract_crs_from_layer(layer, layer_name, operation="extraction"):
    """Extract CRS information from a layer, with fallback to WKT if EPSG unavailable.

    Args:
        layer: OGR layer object
        layer_name: Name of the layer (for logging)
        operation: Description of the operation (for logging, e.g., "extraction", "convex hull transformation")

    Returns:
        tuple: (crs, crs_wkt) where:
            - crs: EPSG code as string, or None if not available
            - crs_wkt: WKT definition as string, or None if not available
    """
    crs = None
    crs_wkt = None

    try:
        spatial_ref = layer.GetSpatialRef()
        if spatial_ref:
            # Try to auto-identify EPSG code
            try:
                spatial_ref.AutoIdentifyEPSG()
                crs = spatial_ref.GetAuthorityCode(None)
            except Exception as epsg_error:
                logger.debug(
                    "Could not auto-identify EPSG for layer {}: {}".format(
                        layer_name, epsg_error
                    )
                )
                crs = None

            # If no EPSG code, try to use WKT definition
            if crs is None:
                try:
                    crs_wkt = spatial_ref.ExportToWkt()
                    if crs_wkt:
                        logger.debug(
                            "Layer {} has no EPSG code, using WKT definition for {}".format(
                                layer_name, operation
                            )
                        )
                except Exception as wkt_error:
                    logger.debug(
                        "Could not export WKT for layer {}: {}".format(
                            layer_name, wkt_error
                        )
                    )
                    crs_wkt = None
    except Exception as e:
        logger.debug("Error extracting CRS from layer {}: \n {}".format(layer_name, e))
        crs = None
        crs_wkt = None

    return crs, crs_wkt


def checkFileSupported(filepath):
    """Checks whether it is valid vector file or not. \n
    input "path": type string, path to file which shall be extracted \n
    """

    logger.debug(filepath)
    try:
        file = gdal.OpenEx(filepath)
        driver = file.GetDriver().ShortName
    except:
        logger.debug("File {} is NOT supported by HandleVector module".format(filepath))
        return False
    logger.debug("Layer count: {} ".format(file.GetLayerCount()))
    if file.GetLayerCount() > 0:
        if driver != "CSV":
            logger.debug("File {} is supported by HandleVector module".format(filepath))
            return True
    else:
        logger.debug("File {} is NOT supported by HandleVector module".format(filepath))
        return False


def getTemporalExtent(filepath):
    """extracts temporal extent of the vector file \n
    input "path": type string, file path to vector file
    """

    datasource = ogr.Open(filepath)
    layer_count = datasource.GetLayerCount()
    logger.debug("{} contains {} layers".format(filepath, layer_count))
    datetime_list = []

    for layer in datasource:

        logger.debug(
            "{} : Extracting temporal extent from layer {} ".format(filepath, layer)
        )
        layerDefinition = layer.GetLayerDefn()
        field_names = []

        for i in range(layerDefinition.GetFieldCount()):
            field_names.append(layerDefinition.GetFieldDefn(i).GetName())

        logger.debug(
            "Found {} fields : {}".format(
                layerDefinition.GetFieldCount(), str(field_names)
            )
        )

        match_list = []
        for x in search["time"]:
            term = re.compile(x, re.IGNORECASE)
            for j in field_names:
                match = term.search(j)
                if match is not None:
                    match_list.append(j)

        logger.debug("Features name match: {}".format(match_list))

        if len(match_list) == 0:
            logger.debug(
                "File:{} /Layer: {}: No matched fields for temporal extent".format(
                    filepath, layer
                )
            )
            pass
        else:
            datetime_list = []
            for time_feature in match_list:
                time_list = []
                for feat in layer:
                    time = feat.GetField(time_feature)
                    if time is not None:
                        time_list.append(time)
                layer.ResetReading()

                if len(time_list) != 0:
                    parsed_time = hf.date_parser(time_list)
                    if parsed_time is not None:
                        datetime_list.extend(parsed_time)
                    else:
                        logger.debug(
                            "File {} / Layer {}  \n"
                            "  {} feature do not have recognizable time format".format(
                                filepath, layer, time_feature
                            )
                        )
                        pass
                else:
                    logger.debug(
                        "File {} / Layer {} \n"
                        " No values found in {} field".format(
                            filepath, layer, time_feature
                        )
                    )
                    pass

    if len(datetime_list) == 0:
        logger.debug(
            "File {} do not have recognizable temporal extent".format(filepath)
        )
        return None
    else:
        tbox = [
            min(datetime_list).strftime(hf.output_time_format),
            max(datetime_list).strftime(hf.output_time_format),
        ]

    return tbox


def getBoundingBox(filepath):
    """extracts bounding box from vector file \n
    input "filepath": type string, file path to vector \n
    returns bounding box of the file: type list, length = 4
    """
    datasource = ogr.Open(filepath)
    geo_dict = {}

    for layer in datasource:
        layer_name = layer.GetDescription()
        ext = layer.GetExtent()
        bbox = [ext[0], ext[2], ext[1], ext[3]]

        # Extract CRS information using shared function
        crs, crs_wkt = _extract_crs_from_layer(layer, layer_name, "transformation")

        # Patch GDAL >= 3.2 for GML  https://github.com/OSGeo/gdal/issues/2195
        # GML files in GDAL 3.2+ return extent in (minLat, maxLat, minLon, maxLon) format
        # but we need (minLon, minLat, maxLon, maxLat), so we swap the coordinates
        if (
            int(osgeo.__version__[0]) >= 3
            and int(osgeo.__version__[2]) >= 2
            and datasource.GetDriver().GetName() == "GML"
        ):
            bbox = [ext[2], ext[0], ext[3], ext[1]]

        geo_dict[layer_name] = {"bbox": bbox}

        if crs:
            geo_dict[layer_name]["crs"] = crs
        elif crs_wkt:
            geo_dict[layer_name]["crs_wkt"] = crs_wkt

        if bbox == null_island or (crs is None and crs_wkt is None):
            logger.debug(
                "Layer {} does not have identifiable geographic extent. CRS may be missing.".format(
                    layer_name
                )
            )

    bbox_merge = hf.bbox_merge(geo_dict, filepath)

    spatial_extent = None

    if bbox_merge is not None:
        if len(bbox_merge) != 0:
            spatial_extent = bbox_merge

    return spatial_extent


def getConvexHull(filepath):
    """extracts convex hull from vector file \n
    input "filepath": type string, file path to vector \n
    returns convex hull as a bounding box: type dict with keys 'bbox' and 'crs'
    """
    datasource = ogr.Open(filepath)
    geo_dict = {}

    for layer in datasource:
        layer_name = layer.GetDescription()

        # Collect all geometries from the layer
        geometries = []
        for feature in layer:
            geom = feature.GetGeometryRef()
            if geom is not None:
                geometries.append(geom.Clone())

        if not geometries:
            logger.debug(
                "Layer {} does not contain any geometries for convex hull calculation".format(
                    layer_name
                )
            )
            continue

        # Create a geometry collection
        geom_collection = ogr.Geometry(ogr.wkbGeometryCollection)
        for geom in geometries:
            geom_collection.AddGeometry(geom)

        # Calculate convex hull
        try:
            # Check if we have enough distinct points for a meaningful convex hull
            # Get the envelope to check if we have a degenerate geometry
            envelope = geom_collection.GetEnvelope()
            # OGR envelope format: (min_x, max_x, min_y, max_y)
            min_x, max_x, min_y, max_y = envelope

            # Check if this is a degenerate geometry (point or line)
            is_point = min_x == max_x and min_y == max_y
            is_line = min_x == max_x or min_y == max_y

            if is_point:
                logger.debug(
                    "Layer {} contains only a single point, using point as convex hull".format(
                        layer_name
                    )
                )
                # For point data, create a minimal convex hull as the point itself
                convex_hull_coords = [[min_x, min_y]]
                bbox = [min_x, min_y, max_x, max_y]
                convex_hull = None  # No geometry object for point data
            else:
                # Try to calculate actual convex hull
                convex_hull = geom_collection.ConvexHull()
                if convex_hull is None:
                    logger.debug(
                        "Could not calculate convex hull for layer {}, falling back to bounding box".format(
                            layer_name
                        )
                    )
                    # Fall back to regular bounding box
                    envelope = geom_collection.GetEnvelope()
                    bbox = [envelope[0], envelope[2], envelope[1], envelope[3]]
                    convex_hull_coords = [
                        [envelope[0], envelope[2]],  # min_x, min_y
                        [envelope[1], envelope[2]],  # max_x, min_y
                        [envelope[1], envelope[3]],  # max_x, max_y
                        [envelope[0], envelope[3]],  # min_x, max_y
                        [envelope[0], envelope[2]],  # close the ring
                    ]
                else:
                    # Convert convex hull geometry to coordinate points
                    convex_hull_coords = []
                    if convex_hull.GetGeometryType() == ogr.wkbPolygon:
                        # Get the exterior ring
                        ring = convex_hull.GetGeometryRef(0)
                        if ring is not None:
                            point_count = ring.GetPointCount()
                            for i in range(point_count):
                                x, y, z = ring.GetPoint(i)
                                convex_hull_coords.append([x, y])

                    # For compatibility with existing transformation logic, we still need a bbox
                    # But we'll store the convex hull coordinates separately
                    envelope = convex_hull.GetEnvelope()
                    # OGR envelope format: (min_x, max_x, min_y, max_y)
                    bbox = [envelope[0], envelope[2], envelope[1], envelope[3]]

            # Extract CRS information using shared function
            crs, crs_wkt = _extract_crs_from_layer(
                layer, layer_name, "convex hull transformation"
            )

            # Store the convex hull geometry and its bbox
            geo_dict[layer_name] = {
                "bbox": bbox,
                "convex_hull_coords": convex_hull_coords,  # Store convex hull coordinates
                "convex_hull": convex_hull,  # Store the actual geometry for merging
            }

            if crs:
                geo_dict[layer_name]["crs"] = crs
            elif crs_wkt:
                geo_dict[layer_name]["crs_wkt"] = crs_wkt

            if bbox == null_island or (crs is None and crs_wkt is None):
                logger.debug(
                    "Layer {} convex hull does not have identifiable geographic extent. CRS may be missing.".format(
                        layer_name
                    )
                )

        except Exception as e:
            logger.debug(
                "Error calculating convex hull for layer {}: {}".format(layer_name, e)
            )
            continue

    # For convex hull with single file, we don't need to merge - just return the first result
    if len(geo_dict) == 1:
        # Single layer case - return the convex hull directly
        for layer_name, layer_data in geo_dict.items():
            # Check if we have CRS information (EPSG or WKT)
            if "crs" not in layer_data and "crs_wkt" not in layer_data:
                logger.debug(
                    "Layer {} has no CRS information, cannot extract convex hull".format(
                        layer_name
                    )
                )
                return None

            # For single layer, transform to WGS84 if needed
            bbox = layer_data["bbox"]
            convex_hull_coords = layer_data.get("convex_hull_coords", [])

            # Transform coordinates if not in WGS84
            if "crs" in layer_data and layer_data["crs"] != "4326":
                # Has EPSG code, use bbox_merge to transform
                temp_dict = {layer_name: layer_data}
                merged = hf.bbox_merge(temp_dict, filepath)
                if merged:
                    bbox = merged["bbox"]
                    # Also transform convex hull coords
                    if convex_hull_coords:
                        from osgeo import osr

                        source = osr.SpatialReference()
                        source.ImportFromEPSG(int(layer_data["crs"]))
                        source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
                        dest = osr.SpatialReference()
                        dest.ImportFromEPSG(4326)
                        dest.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
                        transform = osr.CoordinateTransformation(source, dest)
                        convex_hull_coords = [
                            list(transform.TransformPoint(x, y)[:2])
                            for x, y in convex_hull_coords
                        ]
            elif "crs_wkt" in layer_data:
                # Has WKT, use bbox_merge to transform
                temp_dict = {layer_name: layer_data}
                merged = hf.bbox_merge(temp_dict, filepath)
                if merged:
                    bbox = merged["bbox"]
                    # Also transform convex hull coords
                    if convex_hull_coords:
                        from osgeo import osr

                        source = osr.SpatialReference()
                        source.ImportFromWkt(layer_data["crs_wkt"])
                        source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
                        dest = osr.SpatialReference()
                        dest.ImportFromEPSG(4326)
                        dest.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
                        transform = osr.CoordinateTransformation(source, dest)
                        convex_hull_coords = [
                            list(transform.TransformPoint(x, y)[:2])
                            for x, y in convex_hull_coords
                        ]

            spatial_extent = {
                "bbox": bbox,
                "crs": "4326",
                "convex_hull": True,
            }
            if convex_hull_coords:
                spatial_extent["convex_hull_coords"] = convex_hull_coords
            return spatial_extent
    else:
        # Multiple layers - need to merge using convex hull merge logic
        bbox_merge = hf.convex_hull_merge(geo_dict, filepath)
        spatial_extent = None
        if bbox_merge is not None:
            if len(bbox_merge) != 0:
                spatial_extent = bbox_merge

        return spatial_extent
