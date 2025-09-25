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

        try:
            spatial_ref = layer.GetSpatialRef()
            spatial_ref.AutoIdentifyEPSG()
            crs = spatial_ref.GetAuthorityCode(None)
        except Exception as e:
            logger.debug(
                "Error extracting EPSG CODE from layer {}: \n {}".format(layer_name, e)
            )
            crs = None

        # Patch GDAL > 3.2 for GML  https://github.com/OSGeo/gdal/issues/2195
        if (
            int(osgeo.__version__[0]) >= 3
            and int(osgeo.__version__[2]) < 2
            and datasource.GetDriver().GetName() == "GML"
        ):
            bbox = [ext[2], ext[0], ext[3], ext[1]]

        geo_dict[layer_name] = {"bbox": bbox, "crs": crs}

        if bbox == null_island or crs is None:
            logger.debug(
                "Layer {} does not have identifiable geographic extent. CRS may be missing.".format(
                    layer_name
                )
            )
            del geo_dict[layer_name]["crs"]

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
            convex_hull = geom_collection.ConvexHull()
            if convex_hull is None:
                logger.debug(
                    "Could not calculate convex hull for layer {}".format(layer_name)
                )
                continue

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

            # Get CRS information
            try:
                spatial_ref = layer.GetSpatialRef()
                spatial_ref.AutoIdentifyEPSG()
                crs = spatial_ref.GetAuthorityCode(None)
            except Exception as e:
                logger.debug(
                    "Error extracting EPSG CODE from layer {}: \n {}".format(
                        layer_name, e
                    )
                )
                crs = None

            # Store the convex hull geometry and its bbox
            geo_dict[layer_name] = {
                "bbox": bbox,
                "crs": crs,
                "convex_hull_coords": convex_hull_coords,  # Store convex hull coordinates
                "convex_hull": convex_hull,  # Store the actual geometry for merging
            }

            if bbox == null_island or crs is None:
                logger.debug(
                    "Layer {} convex hull does not have identifiable geographic extent. CRS may be missing.".format(
                        layer_name
                    )
                )
                if crs is None:
                    del geo_dict[layer_name]["crs"]

        except Exception as e:
            logger.debug(
                "Error calculating convex hull for layer {}: {}".format(layer_name, e)
            )
            continue

    # For convex hull with single file, we don't need to merge - just return the first result
    if len(geo_dict) == 1:
        # Single layer case - return the convex hull directly
        for layer_name, layer_data in geo_dict.items():
            spatial_extent = {
                "bbox": layer_data["bbox"],
                "crs": layer_data["crs"],
                "convex_hull": True,
            }
            if "convex_hull_coords" in layer_data:
                spatial_extent["convex_hull_coords"] = layer_data["convex_hull_coords"]
            return spatial_extent
    else:
        # Multiple layers - need to merge using convex hull merge logic
        bbox_merge = hf.convex_hull_merge(geo_dict, filepath)
        spatial_extent = None
        if bbox_merge is not None:
            if len(bbox_merge) != 0:
                spatial_extent = bbox_merge

        return spatial_extent
