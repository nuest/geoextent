import filesizelib
import logging
import os
import patoolib
import random
import threading
import time
import tempfile
from .content_providers import Dryad
from .content_providers import Figshare
from .content_providers import Zenodo
from .content_providers import InvenioRDM
from .content_providers import Pangaea
from .content_providers import OSF
from .content_providers import Dataverse
from .content_providers import GFZ
from .content_providers import Pensoft
from .content_providers import Opara
from .content_providers import Senckenberg
from .content_providers import BGR
from .content_providers import MendeleyData
from .content_providers import Wikidata
from .content_providers import FourTU
from .content_providers import RADAR
from .content_providers import ArcticDataCenter
from . import handleCSV
from . import handleRaster
from . import handleVector
from . import helpfunctions as hf
from . import external_metadata

logger = logging.getLogger("geoextent")
handle_modules = {"CSV": handleCSV, "raster": handleRaster, "vector": handleVector}


def _get_content_providers():
    """Return the ordered list of content provider classes."""
    return [
        Wikidata.Wikidata,  # Wikidata first: Q-numbers won't match DOI providers
        Dryad.Dryad,
        FourTU.FourTU,  # Before Figshare: 4TU uses Djehuty with Figshare-compatible API
        Figshare.Figshare,
        Zenodo.Zenodo,
        InvenioRDM.InvenioRDM,  # After Zenodo: catches other InvenioRDM instances
        Pangaea.Pangaea,
        OSF.OSF,
        Dataverse.Dataverse,
        GFZ.GFZ,
        RADAR.RADAR,
        ArcticDataCenter.ArcticDataCenter,
        Pensoft.Pensoft,
        BGR.BGR,  # BGR before Opara because both accept UUIDs
        Opara.Opara,
        Senckenberg.Senckenberg,
        MendeleyData.MendeleyData,
    ]


def _swap_coordinate_order(metadata):
    """Swap coordinate order from internal [lon, lat] to EPSG:4326 native [lat, lon].

    Transforms bbox [minlon, minlat, maxlon, maxlat] → [minlat, minlon, maxlat, maxlon]
    and convex hull coords [[lon, lat], ...] → [[lat, lon], ...].

    Recursively processes 'details' dicts for directory/remote results.
    """
    if not isinstance(metadata, dict):
        return metadata

    result = dict(metadata)

    if "bbox" in result and result["bbox"] is not None:
        bbox = result["bbox"]
        if isinstance(bbox, dict) and bbox.get("type") == "Polygon":
            # GeoJSON Polygon format: swap each coordinate pair in the ring(s)
            new_coords = []
            for ring in bbox.get("coordinates", []):
                new_coords.append([[coord[1], coord[0]] for coord in ring])
            result["bbox"] = {"type": "Polygon", "coordinates": new_coords}
        elif isinstance(bbox, list) and len(bbox) > 0:
            if isinstance(bbox[0], list):
                # Convex hull coords: [[lon, lat], ...] → [[lat, lon], ...]
                result["bbox"] = [[coord[1], coord[0]] for coord in bbox]
            elif len(bbox) == 4:
                # Bbox: [minlon, minlat, maxlon, maxlat] → [minlat, minlon, maxlat, maxlon]
                result["bbox"] = [bbox[1], bbox[0], bbox[3], bbox[2]]

    if "details" in result and isinstance(result["details"], dict):
        result["details"] = {
            k: _swap_coordinate_order(v) for k, v in result["details"].items()
        }

    return result


def compute_bbox_wgs84(module, path, assume_wgs84=False):
    """
    Extract and transform bounding box to WGS84.

    Trusts GDAL/OGR coordinate order from transformations. For data already in WGS84,
    uses coordinates as provided by the handler without modification.

    Args:
        module: Handler module (handleCSV, handleVector, handleRaster)
        path: File path
        assume_wgs84: If True, assume WGS84 for ungeoreferenced rasters (default False)

    Returns:
        dict: {"bbox": [minlon, minlat, maxlon, maxlat], "crs": "4326"}
              Coordinates are always in [longitude, latitude] order per GeoJSON spec.
    """
    logger.debug("compute_bbox_wgs84: {}".format(path))
    if module.get_handler_name() == "handleRaster":
        spatial_extent_origin = module.getBoundingBox(path, assume_wgs84=assume_wgs84)
    else:
        spatial_extent_origin = module.getBoundingBox(path)

    if spatial_extent_origin is None:
        return None

    try:
        if spatial_extent_origin["crs"] == str(hf.WGS84_EPSG_ID):
            # Data claims to be in WGS84 - check for clearly projected coordinates
            bbox = spatial_extent_origin["bbox"]
            if any(abs(c) > 360 for c in bbox):
                logger.warning(
                    "{}: Reported CRS is WGS84 but coordinates {} are clearly outside "
                    "geographic range (values > 360). This typically indicates a file "
                    "with projected coordinates but no CRS declaration. Skipping.".format(
                        path, bbox
                    )
                )
                return None
            spatial_extent = spatial_extent_origin
            logger.debug(
                "Bbox already in WGS84, using coordinates as-is: {}".format(
                    spatial_extent["bbox"]
                )
            )
        else:
            # Transform to WGS84 - trust GDAL transformation result
            logger.debug(
                "Transforming bbox from EPSG:{} to WGS84".format(
                    spatial_extent_origin["crs"]
                )
            )
            spatial_extent = {
                "bbox": hf.transformingArrayIntoWGS84(
                    spatial_extent_origin["crs"], spatial_extent_origin["bbox"]
                ),
                "crs": str(hf.WGS84_EPSG_ID),
            }
            logger.debug(
                "Transformation complete, bbox in WGS84: {}".format(
                    spatial_extent["bbox"]
                )
            )
    except Exception as e:
        raise Exception(
            "The bounding box could not be transformed to the target CRS epsg:{} \n error {}".format(
                hf.WGS84_EPSG_ID, e
            )
        )

    return spatial_extent


def compute_convex_hull_wgs84(module, path, assume_wgs84=False):
    """
    Extract and transform convex hull to WGS84.

    Trusts GDAL/OGR coordinate order from transformations. For data already in WGS84,
    uses coordinates as provided by the handler without modification.

    Args:
        module: Handler module (handleCSV, handleVector, handleRaster)
        path: File path
        assume_wgs84: If True, assume WGS84 for ungeoreferenced rasters (default False)

    Returns:
        dict: {"bbox": [minlon, minlat, maxlon, maxlat], "crs": "4326",
               "convex_hull_coords": [[lon1, lat1], [lon2, lat2], ...]}
              Coordinates are always in [longitude, latitude] order per GeoJSON spec.
    """
    logger.debug("compute_convex_hull_wgs84: {}".format(path))

    # Check if module has convex hull support
    if not hasattr(module, "getConvexHull"):
        logger.debug(
            "Module {} does not support convex hull calculation, falling back to bounding box".format(
                module.get_handler_name()
            )
        )
        return compute_bbox_wgs84(module, path, assume_wgs84=assume_wgs84)

    spatial_extent_origin = module.getConvexHull(path)

    if spatial_extent_origin is None:
        return None

    try:
        if spatial_extent_origin["crs"] == str(hf.WGS84_EPSG_ID):
            # Data claims to be in WGS84 - check for clearly projected coordinates
            bbox = spatial_extent_origin["bbox"]
            # For convex hull, bbox may be a list of coordinate pairs — extract the envelope
            if isinstance(bbox, list) and len(bbox) > 0 and isinstance(bbox[0], list):
                all_coords = [c for p in bbox for c in p]
            else:
                all_coords = bbox
            if any(abs(c) > 360 for c in all_coords):
                logger.warning(
                    "{}: Reported CRS is WGS84 but coordinates are clearly outside "
                    "geographic range (values > 360). This typically indicates a file "
                    "with projected coordinates but no CRS declaration. Skipping.".format(
                        path
                    )
                )
                return None
            spatial_extent = spatial_extent_origin
            logger.debug(
                "Convex hull already in WGS84, using coordinates as-is: {}".format(
                    spatial_extent["bbox"]
                )
            )
        else:
            # Transform to WGS84 - trust GDAL transformation result
            logger.debug(
                "Transforming convex hull from EPSG:{} to WGS84".format(
                    spatial_extent_origin["crs"]
                )
            )
            spatial_extent = {
                "bbox": hf.transformingArrayIntoWGS84(
                    spatial_extent_origin["crs"], spatial_extent_origin["bbox"]
                ),
                "crs": str(hf.WGS84_EPSG_ID),
            }

            # Transform convex hull coordinates if they exist
            if (
                "convex_hull_coords" in spatial_extent_origin
                and spatial_extent_origin["convex_hull_coords"]
            ):
                transformed_coords = []
                for coord in spatial_extent_origin["convex_hull_coords"]:
                    # Transform each coordinate point
                    transformed_point = hf.transformingArrayIntoWGS84(
                        spatial_extent_origin["crs"],
                        [coord[0], coord[1], coord[0], coord[1]],
                    )
                    # Take the first two values (x, y)
                    transformed_coords.append(
                        [transformed_point[0], transformed_point[1]]
                    )
                spatial_extent["convex_hull_coords"] = transformed_coords

            # Preserve convex hull flag and geometry
            if "convex_hull" in spatial_extent_origin:
                spatial_extent["convex_hull"] = spatial_extent_origin["convex_hull"]
            if "convex_hull" in spatial_extent_origin:  # Geometry reference
                spatial_extent["convex_hull_geom"] = spatial_extent_origin[
                    "convex_hull"
                ]

            logger.debug(
                "Transformation complete, convex hull bbox in WGS84: {}".format(
                    spatial_extent["bbox"]
                )
            )
    except Exception as e:
        raise Exception(
            "The convex hull could not be transformed to the target CRS epsg:{} \n error {}".format(
                hf.WGS84_EPSG_ID, e
            )
        )

    return spatial_extent


# Set of auxiliary file extensions to skip (defined at module level for efficiency)
_AUXILIARY_EXTENSIONS = {
    ".ovr",  # Overview/pyramid files (reduced resolution versions)
    ".aux.xml",  # GDAL auxiliary metadata
    ".tif.xml",  # Metadata for TIFF files
    ".tiff.xml",  # Metadata for TIFF files (alternative extension)
    ".msk",  # Mask files
}


def _is_auxiliary_file(filename: str) -> bool:
    """Check if a file is a GDAL/geospatial auxiliary file that should be skipped.

    GDAL and other geospatial tools create auxiliary files alongside the main data files.
    These files should not be processed independently as they lack proper georeferencing
    or are already represented in the main file.

    Uses hash-based set lookup for O(1) performance.

    Args:
        filename: The filename to check

    Returns:
        True if the file is an auxiliary file and should be skipped, False otherwise
    """
    filename_lower = filename.lower()

    # Check if filename ends with any auxiliary extension (O(n) where n is number of extensions)
    for ext in _AUXILIARY_EXTENSIONS:
        if filename_lower.endswith(ext):
            return True

    return False


def fromDirectory(
    path: str,
    bbox: bool = False,
    tbox: bool = False,
    convex_hull: bool = False,
    details: bool = False,
    timeout: None | int | float = None,
    level: int = 0,
    show_progress: bool = True,
    recursive: bool = True,
    include_geojsonio: bool = False,
    placename: str | None = None,
    placename_escape: bool = False,
    legacy: bool = False,
    assume_wgs84: bool = False,
    time_format: str | None = None,
    _internal: bool = False,
):
    """Extracts geoextent from a directory/archive
    Keyword arguments:
    path -- directory/archive path
    bbox -- True if bounding box is requested (default False)
    tbox -- True if time box is requested (default False)
    convex_hull -- True if convex hull should be calculated instead of bounding box (default False)
    timeout -- maximal allowed run time in seconds (default None)
    recursive -- True to process subdirectories recursively (default True)
    include_geojsonio -- True if geojson.io URL should be included in output (default False)
    placename -- gazetteer to use for placename lookup (geonames, nominatim, photon) (default None)
    assume_wgs84 -- True to assume WGS84 for ungeoreferenced rasters (default False)
    """

    from tqdm import tqdm

    logger.info(
        "Extracting bbox={} tbox={} convex_hull={} from Directory {}".format(
            bbox, tbox, convex_hull, path
        )
    )

    if not bbox and not tbox:
        logger.error(
            "Require at least one of extraction options, but bbox is {} and tbox is {}".format(
                bbox, tbox
            )
        )
        raise Exception("No extraction options enabled!")
    metadata = {}
    # initialization of later output dict
    metadata_directory = {}

    timeout_flag = False
    start_time = time.time()

    # TODO: eventually delete all extracted content

    is_archive = patoolib.is_archive(path)

    if is_archive:
        logger.info("Inspecting archive {}".format(path))
        extract_folder = hf.extract_archive(path)
        logger.info("Extract_folder archive {}".format(extract_folder))
        path = extract_folder

    files = os.listdir(path)
    if timeout:
        random.seed(0)
        random.shuffle(files)

    # Create progress bar for directory processing (only at top level)
    dir_name = os.path.basename(path) or "root"
    show_progress_bar = (
        show_progress and level == 0
    )  # Only show progress bar at top level to avoid nested bars

    if show_progress_bar:
        pbar = tqdm(
            total=len(files), desc=f"Processing directory: {dir_name}", unit="item"
        )

    for i, filename in enumerate(files):
        elapsed_time = time.time() - start_time
        if timeout and elapsed_time > timeout:
            if level == 0:
                logger.warning(
                    f"Timeout reached after {timeout} seconds, returning partial results."
                )
                timeout_flag = True
            break

        if show_progress_bar:
            pbar.set_postfix_str(f"Processing {filename}")

        logger.info("path {}, folder/archive {}".format(path, filename))

        # Skip GDAL auxiliary files
        if _is_auxiliary_file(filename):
            logger.debug(f"Skipping auxiliary file: {filename}")
            continue

        absolute_path = os.path.join(path, filename)
        is_archive = patoolib.is_archive(absolute_path)

        remaining_time = timeout - elapsed_time if timeout else None

        if is_archive:
            logger.info(
                "**Inspecting folder {}, is archive ? {}**".format(
                    filename, str(is_archive)
                )
            )
            if recursive:
                metadata_directory[filename] = fromDirectory(
                    absolute_path,
                    bbox,
                    tbox,
                    convex_hull,
                    details=True,
                    timeout=remaining_time,
                    level=level + 1,
                    show_progress=show_progress,
                    recursive=recursive,
                    include_geojsonio=include_geojsonio,
                    placename=placename,
                    placename_escape=placename_escape,
                    time_format=time_format,
                    _internal=True,
                )
            else:
                logger.info("Skipping archive {} (recursive=False)".format(filename))
        else:
            logger.info(
                "Inspecting folder {}, is archive ? {}".format(
                    filename, str(is_archive)
                )
            )
            if os.path.isdir(absolute_path):
                if absolute_path.rstrip(os.sep).endswith(".gdb"):
                    # ESRI File Geodatabase — treat as a dataset, not a directory
                    metadata_file = fromFile(
                        absolute_path,
                        bbox,
                        tbox,
                        convex_hull,
                        show_progress=show_progress,
                        include_geojsonio=include_geojsonio,
                        placename=placename,
                        placename_escape=placename_escape,
                        assume_wgs84=assume_wgs84,
                        time_format=time_format,
                        _internal=True,
                    )
                    metadata_directory[str(filename)] = metadata_file
                elif recursive:
                    metadata_directory[filename] = fromDirectory(
                        absolute_path,
                        bbox,
                        tbox,
                        convex_hull,
                        details=True,
                        timeout=remaining_time,
                        level=level + 1,
                        show_progress=show_progress,
                        recursive=recursive,
                        include_geojsonio=include_geojsonio,
                        placename=placename,
                        placename_escape=placename_escape,
                        assume_wgs84=assume_wgs84,
                        time_format=time_format,
                        _internal=True,
                    )
                else:
                    logger.info(
                        "Skipping subdirectory {} (recursive=False)".format(filename)
                    )
            else:
                metadata_file = fromFile(
                    absolute_path,
                    bbox,
                    tbox,
                    convex_hull,
                    show_progress=show_progress,
                    include_geojsonio=include_geojsonio,
                    placename=placename,
                    placename_escape=placename_escape,
                    assume_wgs84=assume_wgs84,
                    time_format=time_format,
                    _internal=True,
                )
                metadata_directory[str(filename)] = metadata_file

        # Update progress bar
        if show_progress_bar:
            pbar.update(1)

    # Close progress bar at top level
    if show_progress_bar:
        pbar.close()

    file_format = "archive" if is_archive else "folder"
    metadata["format"] = file_format

    if bbox:
        if convex_hull:
            bbox_ext = hf.convex_hull_merge(metadata_directory, path)
            # If convex hull fails, fall back to regular bounding box
            if bbox_ext is None:
                logger.warning(
                    "Convex hull calculation failed for {} {} - insufficient data points or geometric constraints. Falling back to bounding box.".format(
                        file_format, path
                    )
                )
                # Recompute metadata with regular bbox format for fallback
                fallback_metadata = {}
                for filename, file_metadata in metadata_directory.items():
                    if isinstance(file_metadata, dict) and "bbox" in file_metadata:
                        fallback_file_metadata = file_metadata.copy()

                        # Convert convex hull coordinates back to [W,S,E,N] format if needed
                        bbox = file_metadata["bbox"]
                        if (
                            isinstance(bbox, list)
                            and len(bbox) >= 3
                            and isinstance(bbox[0], list)
                        ):
                            # This is coordinate array format, convert to envelope
                            x_coords = [coord[0] for coord in bbox if len(coord) >= 2]
                            y_coords = [coord[1] for coord in bbox if len(coord) >= 2]
                            if x_coords and y_coords:
                                fallback_file_metadata["bbox"] = [
                                    min(x_coords),
                                    min(y_coords),
                                    max(x_coords),
                                    max(y_coords),
                                ]

                        # Remove convex hull flag for fallback
                        if "convex_hull" in fallback_file_metadata:
                            del fallback_file_metadata["convex_hull"]

                        fallback_metadata[filename] = fallback_file_metadata

                bbox_ext = hf.bbox_merge(fallback_metadata, path)
                # If fallback succeeds, we still have a valid spatial extent, just not convex hull
                if bbox_ext is not None:
                    logger.info(
                        "Successfully generated bounding box as fallback for {} {}".format(
                            file_format, path
                        )
                    )
        else:
            bbox_ext = hf.bbox_merge(metadata_directory, path)

        if bbox_ext is not None:
            if len(bbox_ext) != 0:
                metadata["crs"] = bbox_ext["crs"]
                metadata["bbox"] = bbox_ext["bbox"]
                # Mark if this is from convex hull calculation
                if convex_hull and "convex_hull" in bbox_ext:
                    metadata["convex_hull"] = bbox_ext["convex_hull"]
        else:
            hull_type = "convex hull" if convex_hull else "bbox"
            logger.warning(
                "The {} {} has no identifiable {} - Coordinate reference system (CRS) may be missing".format(
                    file_format, path, hull_type
                )
            )

    if tbox:
        tbox_ext = hf.tbox_merge(metadata_directory, path, time_format=time_format)
        if tbox_ext is not None:
            metadata["tbox"] = tbox_ext
        else:
            logger.debug(
                "The {} {} has no identifiable time extent".format(file_format, path)
            )

    if details:
        metadata["details"] = metadata_directory

    if timeout and timeout_flag:
        metadata["timeout"] = timeout

    # Add placename if requested and spatial extent is available
    if placename and metadata.get("bbox"):
        try:
            from .gazetteer import get_placename_for_geometry

            # Determine if we have convex hull coordinates
            convex_hull_coords = None
            bbox_coords = metadata.get("bbox")
            is_convex_hull = metadata.get("convex_hull", False)

            if (
                is_convex_hull
                and isinstance(bbox_coords, list)
                and len(bbox_coords) > 0
                and isinstance(bbox_coords[0], list)
            ):
                convex_hull_coords = bbox_coords
                bbox_coords = None

            placename_result = get_placename_for_geometry(
                bbox=bbox_coords if not is_convex_hull else None,
                convex_hull_coords=convex_hull_coords,
                service_name=placename,
                escape_unicode=placename_escape,
            )

            if placename_result:
                metadata["placename"] = placename_result
                logger.info(f"Found placename: {placename_result}")
            else:
                logger.warning("No placename found for the extracted geometry")

        except Exception as e:
            logger.warning(f"Failed to extract placename: {e}")

    # Calculate total size for directory (sum of all processed files in details)
    if details and "details" in metadata:
        total_size = 0
        for file_path, file_metadata in metadata["details"].items():
            if isinstance(file_metadata, dict) and "file_size_bytes" in file_metadata:
                total_size += file_metadata["file_size_bytes"]
        if total_size > 0:
            metadata["file_size_bytes"] = total_size

    # Add geojson.io URL if requested and spatial extent is available
    if include_geojsonio and metadata.get("bbox"):
        geojsonio_url = hf.generate_geojsonio_url(metadata)
        if geojsonio_url:
            metadata["geojsonio_url"] = geojsonio_url

    # Apply EPSG:4326 native axis order (lat, lon) unless legacy mode or internal call
    if not legacy and not _internal:
        metadata = _swap_coordinate_order(metadata)

    return metadata


def fromFile(
    filepath,
    bbox=True,
    tbox=True,
    convex_hull=False,
    num_sample=None,
    show_progress=True,
    include_geojsonio=False,
    placename=None,
    placename_escape=False,
    legacy=False,
    assume_wgs84=False,
    time_format=None,
    _internal=False,
):
    """Extracts geoextent from a file
    Keyword arguments:
    path -- filepath
    bbox -- True if bounding box is requested (default False)
    tbox -- True if time box is requested (default False)
    convex_hull -- True if convex hull should be calculated instead of bounding box (default False)
    num_sample -- sample size to determine time format (Only required for csv files)
    include_geojsonio -- True if geojson.io URL should be included in output (default False)
    placename -- gazetteer to use for placename lookup (geonames, nominatim, photon) (default None)
    assume_wgs84 -- True to assume WGS84 for ungeoreferenced rasters (default False)
    """
    from tqdm import tqdm

    logger.info(
        "Extracting bbox={} tbox={} convex_hull={} from file {}".format(
            bbox, tbox, convex_hull, filepath
        )
    )

    if not bbox and not tbox:
        logger.error(
            "Require at least one of extraction options, but bbox is {} and tbox is {}".format(
                bbox, tbox
            )
        )
        raise Exception("No extraction options enabled!")

    if os.path.isdir(filepath) and not filepath.rstrip(os.sep).endswith(".gdb"):
        logger.info("{} is a directory, not a file".format(filepath))
        return None

    file_format = os.path.splitext(filepath)[1][1:]

    usedModule = None

    # initialization of later output dict
    metadata = {}

    # get the module that will be called (depending on the format of the file)

    for i in handle_modules:
        valid = handle_modules[i].checkFileSupported(filepath)
        if valid:
            usedModule = handle_modules[i]
            logger.info(
                "{} is being used to inspect {} file".format(
                    usedModule.get_handler_name(), filepath
                )
            )
            break

    # If file format is not supported
    if not usedModule:
        logger.info(
            "Did not find a compatible module for file format {} of file {}".format(
                file_format, filepath
            )
        )
        return None

    # get Bbox, Temporal Extent, Vector representation and crs parallel with threads
    class thread(threading.Thread):
        def __init__(self, task):
            threading.Thread.__init__(self)
            self.task = task
            self.warning_msg = None

        def run(self):

            metadata["format"] = file_format
            metadata["geoextent_handler"] = usedModule.get_handler_name()

            # with lock:

            logger.debug("Starting  thread {} on file {}".format(self.task, filepath))
            if self.task == "bbox":
                try:
                    if bbox:
                        if convex_hull:
                            spatial_extent = compute_convex_hull_wgs84(
                                usedModule, filepath, assume_wgs84=assume_wgs84
                            )
                        else:
                            spatial_extent = compute_bbox_wgs84(
                                usedModule, filepath, assume_wgs84=assume_wgs84
                            )

                        if spatial_extent is not None:
                            # For convex hull, use the actual convex hull coordinates, not the envelope
                            if convex_hull and "convex_hull_coords" in spatial_extent:
                                metadata["bbox"] = spatial_extent["convex_hull_coords"]
                                metadata["convex_hull"] = True
                            else:
                                metadata["bbox"] = spatial_extent["bbox"]

                            metadata["crs"] = spatial_extent["crs"]
                except Exception as e:
                    self.warning_msg = "Error for {} extracting bbox:\n{}".format(
                        filepath, str(e)
                    )
            elif self.task == "tbox":
                try:
                    if tbox:
                        if usedModule.get_handler_name() == "handleCSV":
                            extract_tbox = usedModule.getTemporalExtent(
                                filepath, num_sample, time_format=time_format
                            )
                        else:
                            if num_sample is not None:
                                logger.warning(
                                    "num_sample parameter is ignored, only applies to CSV files"
                                )
                            extract_tbox = usedModule.getTemporalExtent(
                                filepath, time_format=time_format
                            )
                        if extract_tbox is not None:
                            metadata["tbox"] = extract_tbox
                except Exception as e:
                    self.warning_msg = (
                        "Error extracting tbox, time format not found \n {}:".format(
                            str(e)
                        )
                    )
            else:
                raise Exception("Unsupported thread task {}".format(self.task))
            logger.debug("Completed thread {} on file {}".format(self.task, filepath))

    thread_bbox_except = thread("bbox")
    thread_temp_except = thread("tbox")

    logger.debug("Starting 2 threads for extraction.")

    # Calculate total tasks for progress bar
    total_tasks = (1 if bbox else 0) + (1 if tbox else 0)
    filename = os.path.basename(filepath)

    if show_progress:
        with tqdm(
            total=total_tasks, desc=f"Processing {filename}", unit="task", leave=False
        ) as pbar:
            thread_bbox_except.start()
            thread_temp_except.start()

            # Wait for threads to complete while updating progress
            if bbox:
                thread_bbox_except.join()
                pbar.set_postfix_str("Spatial extent extracted")
                pbar.update(1)

            if tbox:
                thread_temp_except.join()
                pbar.set_postfix_str("Temporal extent extracted")
                pbar.update(1)
    else:
        # Run threads without progress bar
        thread_bbox_except.start()
        thread_temp_except.start()

        if bbox:
            thread_bbox_except.join()
        if tbox:
            thread_temp_except.join()

    # Emit deferred warnings after progress bar is closed
    for t in [thread_bbox_except, thread_temp_except]:
        if t.warning_msg:
            logger.warning(t.warning_msg)

    logger.debug("Extraction finished: {}".format(str(metadata)))

    # Add file size to metadata
    try:
        if os.path.isfile(filepath):
            metadata["file_size_bytes"] = os.path.getsize(filepath)
    except (OSError, FileNotFoundError):
        pass

    # Add placename if requested and spatial extent is available
    if placename and metadata.get("bbox"):
        try:
            from .gazetteer import get_placename_for_geometry

            # Determine if we have convex hull coordinates
            convex_hull_coords = None
            bbox_coords = metadata.get("bbox")
            is_convex_hull = metadata.get("convex_hull", False)

            if (
                is_convex_hull
                and isinstance(bbox_coords, list)
                and len(bbox_coords) > 0
                and isinstance(bbox_coords[0], list)
            ):
                convex_hull_coords = bbox_coords
                bbox_coords = None

            placename_result = get_placename_for_geometry(
                bbox=bbox_coords if not is_convex_hull else None,
                convex_hull_coords=convex_hull_coords,
                service_name=placename,
                escape_unicode=placename_escape,
            )

            if placename_result:
                metadata["placename"] = placename_result
                logger.info(f"Found placename: {placename_result}")
            else:
                logger.warning("No placename found for the extracted geometry")

        except Exception as e:
            logger.warning(f"Failed to extract placename: {e}")

    # Add geojson.io URL if requested and spatial extent is available
    if include_geojsonio and metadata.get("bbox"):
        geojsonio_url = hf.generate_geojsonio_url(metadata)
        if geojsonio_url:
            metadata["geojsonio_url"] = geojsonio_url

    # Apply EPSG:4326 native axis order (lat, lon) unless legacy mode or internal call
    if not legacy and not _internal:
        metadata = _swap_coordinate_order(metadata)

    return metadata


def fromRemote(
    remote_identifier: str | list[str],
    bbox: bool = False,
    tbox: bool = False,
    convex_hull: bool = False,
    details: bool = False,
    throttle: bool = False,
    timeout: None | int | float = None,
    download_data: bool = True,
    show_progress: bool = True,
    recursive: bool = True,
    include_geojsonio: bool = False,
    max_download_size: str | None = None,
    max_download_method: str = "ordered",
    max_download_method_seed: int = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED,
    placename: str | None = None,
    placename_escape: bool = False,
    download_skip_nogeo: bool = False,
    download_skip_nogeo_exts: set = None,
    max_download_workers: int = 4,
    ext_metadata: bool = False,
    ext_metadata_method: str = "auto",
    keep_files: bool = False,
    legacy: bool = False,
    assume_wgs84: bool = False,
    metadata_first: bool = False,
    metadata_fallback: bool = True,
    time_format: str | None = None,
):
    """
    Extract geospatial and temporal extent from one or more remote resources.

    This function processes remote identifiers (DOIs, URLs) and returns extracted
    extents. It accepts either a single identifier (string) or multiple identifiers (list).

    Parameters
    ----------
    remote_identifier : str or list of str
        Single identifier (str) or list of identifiers (DOIs, URLs, or repository-specific identifiers)
    bbox : bool, optional
        Extract bounding box (default: False)
    tbox : bool, optional
        Extract temporal extent (default: False)
    convex_hull : bool, optional
        Extract convex hull instead of bounding box (default: False)
    details : bool, optional
        Include detailed extraction information (default: False)
    throttle : bool, optional
        Enable API rate limiting (default: False)
    timeout : int or float, optional
        Timeout in seconds for operations (default: None)
    download_data : bool, optional
        Download actual data files (default: True)
    show_progress : bool, optional
        Show progress bars (default: True)
    recursive : bool, optional
        Process archives recursively (default: True)
    include_geojsonio : bool, optional
        Include geojson.io URL (default: False)
    max_download_size : str, optional
        Maximum download size (e.g., '100MB') (default: None)
    max_download_method : str, optional
        File selection method when size limited (default: 'ordered')
    max_download_method_seed : int, optional
        Random seed for reproducible sampling (default: DEFAULT_DOWNLOAD_SAMPLE_SEED)
    placename : str, optional
        Gazetteer service for placename lookup (default: None)
    placename_escape : bool, optional
        Escape placenames for use in URLs (default: False)
    download_skip_nogeo : bool, optional
        Skip non-geospatial files (default: False)
    download_skip_nogeo_exts : set, optional
        Additional file extensions to consider geospatial (default: None)
    max_download_workers : int, optional
        Number of parallel download workers (default: 4)
    ext_metadata : bool, optional
        Retrieve external metadata from CrossRef/DataCite for DOIs (default: False)
    ext_metadata_method : str, optional
        Method for retrieving metadata: "auto", "all", "crossref", "datacite" (default: "auto")
    keep_files : bool, optional
        Keep downloaded and extracted files instead of cleaning them up (default: False)
    metadata_first : bool, optional
        Try metadata-only extraction first, fall back to data download if metadata
        yields no results. Mutually exclusive with download_data=False. (default: False)
    metadata_fallback : bool, optional
        Automatically fall back to metadata-only extraction when data download yields
        no files and the provider supports metadata extraction. Disable with
        ``metadata_fallback=False`` or ``--no-metadata-fallback``. (default: True)

    Returns
    -------
    dict
        For single identifier (str input): Metadata dict with format='remote'
        For multiple identifiers (list input): Metadata dict with format='remote_bulk' and details for each

    Raises
    ------
    ValueError
        If remote_identifier is an empty list
    Exception
        If errors occur during extraction

    Examples
    --------
    >>> from geoextent.lib import extent
    >>> # Single resource
    >>> result = extent.fromRemote('10.5281/zenodo.4593540', bbox=True)
    >>> print(result['bbox'])
    >>>
    >>> # Multiple resources
    >>> identifiers = ['10.5281/zenodo.4593540', 'https://doi.org/10.25532/OPARA-581']
    >>> result = extent.fromRemote(identifiers, bbox=True, tbox=True)
    >>> print(result['bbox'])  # Combined bounding box
    >>> print(result['extraction_metadata'])  # Processing statistics
    """

    # Normalize input to list
    is_single_resource = isinstance(remote_identifier, str)
    remote_identifiers = (
        [remote_identifier] if is_single_resource else remote_identifier
    )

    # Validate input
    if not isinstance(remote_identifiers, list):
        raise ValueError(
            f"remote_identifier must be a string or list, got {type(remote_identifier).__name__}"
        )

    if len(remote_identifiers) == 0:
        raise ValueError("remote_identifier list cannot be empty")

    # Validate mutual exclusion: metadata_first implies download_data=True
    if metadata_first and not download_data:
        raise ValueError(
            "--metadata-first and --no-download-data are mutually exclusive. "
            "metadata-first tries metadata first, then falls back to data download."
        )

    logger.info(
        f"Processing extraction from {len(remote_identifiers)} remote resource(s)"
    )

    # Initialize output structure
    output = {
        "format": "remote_bulk" if not is_single_resource else "remote",
        "details": {},
        "extraction_metadata": {
            "total_resources": len(remote_identifiers),
            "successful": 0,
            "failed": 0,
        },
    }

    # Process each remote identifier
    for identifier in remote_identifiers:
        logger.debug(f"Processing remote resource: {identifier}")
        try:
            # Call the actual extraction method directly
            resource_output = _extract_from_remote(
                identifier,
                bbox=bbox,
                tbox=tbox,
                convex_hull=convex_hull,
                details=details,
                throttle=throttle,
                timeout=timeout,
                download_data=download_data,
                show_progress=show_progress,
                recursive=recursive,
                include_geojsonio=include_geojsonio,
                max_download_size=max_download_size,
                max_download_method=max_download_method,
                max_download_method_seed=max_download_method_seed,
                placename=placename,
                placename_escape=placename_escape,
                download_skip_nogeo=download_skip_nogeo,
                download_skip_nogeo_exts=download_skip_nogeo_exts,
                max_download_workers=max_download_workers,
                keep_files=keep_files,
                assume_wgs84=assume_wgs84,
                metadata_first=metadata_first,
                metadata_fallback=metadata_fallback,
                time_format=time_format,
            )
            if resource_output is not None:
                resource_output["format"] = "remote"
                output["details"][identifier] = resource_output
                output["extraction_metadata"]["successful"] += 1
        except Exception as e:
            logger.warning(f"Error processing {identifier}: {str(e)}")
            output["details"][identifier] = {"error": str(e)}
            output["extraction_metadata"]["failed"] += 1
            continue

    # Merge spatial extents if bbox is requested
    if bbox:
        if convex_hull:
            merged_extent = hf.convex_hull_merge(output["details"], "remote")
        else:
            merged_extent = hf.bbox_merge(output["details"], "remote")

        if merged_extent:
            output["bbox"] = merged_extent.get("bbox")
            output["crs"] = merged_extent.get("crs")

    # Merge temporal extents if tbox is requested
    if tbox:
        merged_tbox = hf.tbox_merge(
            output["details"], "remote", time_format=time_format
        )
        if merged_tbox:
            output["tbox"] = merged_tbox

    # Add geojson.io URL if requested
    if include_geojsonio and bbox:
        geojsonio_url = hf.create_geojsonio_url(output)
        if geojsonio_url:
            output["geojsonio_url"] = geojsonio_url

    # Retrieve external metadata for all resources if requested
    if ext_metadata:
        for identifier in remote_identifiers:
            if (
                identifier in output["details"]
                and "error" not in output["details"][identifier]
            ):
                metadata = external_metadata.get_external_metadata(
                    identifier, method=ext_metadata_method
                )
                # Always include external_metadata as an array (even if empty)
                output["details"][identifier]["external_metadata"] = metadata

    logger.info(
        f"Extraction complete: {output['extraction_metadata']['successful']} successful, "
        f"{output['extraction_metadata']['failed']} failed"
    )

    # For single resource, return simplified structure for backward compatibility
    if is_single_resource:
        identifier = remote_identifiers[0]
        if identifier in output["details"]:
            result = output["details"][identifier]

            # If there was an error, raise it
            if "error" in result:
                raise Exception(result["error"])

            # Add merged extents
            if "bbox" in output:
                result["bbox"] = output["bbox"]
            if "crs" in output:
                result["crs"] = output["crs"]
            if "tbox" in output:
                result["tbox"] = output["tbox"]
            if "geojsonio_url" in output:
                result["geojsonio_url"] = output["geojsonio_url"]

            # Retrieve external metadata if requested
            if ext_metadata:
                metadata = external_metadata.get_external_metadata(
                    identifier, method=ext_metadata_method
                )
                # Always include external_metadata as an array (even if empty)
                result["external_metadata"] = metadata

            # Apply EPSG:4326 native axis order (lat, lon) unless legacy mode
            if not legacy:
                result = _swap_coordinate_order(result)

            return result
        else:
            raise Exception(f"Failed to extract from {identifier}")

    # Apply EPSG:4326 native axis order (lat, lon) unless legacy mode
    if not legacy:
        output = _swap_coordinate_order(output)

    # For multiple resources, return full structure
    return output


def _process_remote_download(
    repository,
    tmp,
    throttle,
    download_data,
    show_progress,
    max_download_size,
    max_download_method,
    max_download_method_seed,
    download_skip_nogeo,
    download_skip_nogeo_exts,
    max_download_workers,
    bbox,
    tbox,
    convex_hull,
    details,
    timeout,
    recursive,
    include_geojsonio,
    placename,
    placename_escape,
    assume_wgs84=False,
    metadata_fallback=True,
    time_format=None,
):
    """
    Shared logic for processing remote downloads and extracting metadata.

    This function handles:
    - Parsing and validating download size limits
    - Downloading files from the repository
    - Automatic metadata fallback when download yields no files
    - Extracting metadata from downloaded files

    Args:
        repository: Content provider instance
        tmp: Temporary directory path for downloads
        metadata_fallback: If True and download_data is True, automatically fall back
            to metadata-only extraction when download yields no files and the provider
            supports metadata extraction. (default True)
        (other parameters as documented in _extract_from_remote)

    Returns:
        dict: Extracted metadata

    Raises:
        ValueError: If download size format is invalid
    """
    # Parse download size if provided
    max_size_bytes = None
    if max_download_size:
        # Validate size string format before parsing
        max_download_size = max_download_size.strip()
        if not max_download_size:
            error_msg = "Download size cannot be empty. Please use format like '100MB', '2GB', etc."
            logger.error(error_msg)
            raise ValueError(error_msg)

        max_size_bytes = hf.parse_download_size(max_download_size)
        if max_size_bytes is None:
            # Invalid format error
            error_msg = (
                f"Invalid download size format: '{max_download_size}'. "
                f"Please use format like '100MB', '2GB', '500KB', '1.5TB', etc. "
                f"Supported units: B, KB, MB, GB, TB, PB."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        elif max_size_bytes <= 0:
            error_msg = f"Download size must be positive, got: {max_download_size}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        else:
            logger.debug(
                f"Parsed download size limit: {max_download_size} = {max_size_bytes:,} bytes"
            )

    _used_metadata_fallback = False

    # Download files from repository
    repository.download(
        tmp,
        throttle,
        download_data,
        show_progress,
        max_size_bytes=max_size_bytes,
        max_download_method=max_download_method,
        max_download_method_seed=max_download_method_seed,
        download_skip_nogeo=download_skip_nogeo,
        download_skip_nogeo_exts=download_skip_nogeo_exts,
        max_download_workers=max_download_workers,
    )

    # Automatic metadata fallback: if data download yielded no files and the
    # provider supports metadata extraction, re-download with metadata only.
    if (
        download_data
        and metadata_fallback
        and repository.supports_metadata_extraction
        and not os.listdir(tmp)
    ):
        logger.info(
            "No data files found after download. Falling back to metadata-only "
            "extraction from %s. Use --no-metadata-fallback to disable.",
            repository.name,
        )
        repository.download(
            tmp,
            throttle,
            False,  # download_data=False
            show_progress,
            max_size_bytes=max_size_bytes,
            max_download_method=max_download_method,
            max_download_method_seed=max_download_method_seed,
            download_skip_nogeo=download_skip_nogeo,
            download_skip_nogeo_exts=download_skip_nogeo_exts,
            max_download_workers=max_download_workers,
        )
        _used_metadata_fallback = True

    # Extract metadata from downloaded files
    metadata = fromDirectory(
        tmp,
        bbox,
        tbox,
        convex_hull,
        details,
        timeout,
        show_progress=show_progress,
        recursive=recursive,
        include_geojsonio=include_geojsonio,
        placename=placename,
        placename_escape=placename_escape,
        assume_wgs84=assume_wgs84,
        time_format=time_format,
        _internal=True,
    )

    if _used_metadata_fallback:
        metadata["extraction_method"] = "metadata_fallback"

    return metadata


def _metadata_first_extract(
    repository,
    bbox,
    tbox,
    convex_hull,
    details,
    throttle,
    timeout,
    download_data,
    show_progress,
    recursive,
    include_geojsonio,
    max_download_size,
    max_download_method,
    max_download_method_seed,
    placename,
    placename_escape,
    download_skip_nogeo,
    download_skip_nogeo_exts,
    max_download_workers,
    keep_files,
    assume_wgs84,
    time_format=None,
):
    """Try metadata-only extraction first, fall back to data download if needed.

    Phase 1: If the provider supports metadata extraction, try with download_data=False.
    Phase 2: If metadata didn't yield the requested extents, fall back to download_data=True.

    Returns:
        dict: Extracted metadata with 'extraction_method' field ('metadata' or 'download').
    """
    import shutil

    _common_kwargs = dict(
        repository=repository,
        throttle=throttle,
        show_progress=show_progress,
        max_download_size=max_download_size,
        max_download_method=max_download_method,
        max_download_method_seed=max_download_method_seed,
        download_skip_nogeo=download_skip_nogeo,
        download_skip_nogeo_exts=download_skip_nogeo_exts,
        max_download_workers=max_download_workers,
        bbox=bbox,
        tbox=tbox,
        convex_hull=convex_hull,
        details=details,
        timeout=timeout,
        recursive=recursive,
        include_geojsonio=include_geojsonio,
        placename=placename,
        placename_escape=placename_escape,
        assume_wgs84=assume_wgs84,
        metadata_fallback=False,  # metadata_first has its own two-phase strategy
        time_format=time_format,
    )

    # Phase 1: Try metadata-only extraction if the provider supports it
    if repository.supports_metadata_extraction:
        logger.info(
            f"Metadata-first: trying metadata-only extraction from {repository.name}"
        )
        try:
            with tempfile.TemporaryDirectory() as tmp:
                metadata = _process_remote_download(
                    tmp=tmp, download_data=False, **_common_kwargs
                )

                # Check whether metadata extraction yielded the requested extents
                has_bbox = metadata and metadata.get("bbox") is not None
                has_tbox = metadata and metadata.get("tbox") is not None
                has_requested = (has_bbox if bbox else True) and (
                    has_tbox if tbox else True
                )

                if has_requested:
                    logger.info(
                        f"Metadata-first: extraction succeeded for {repository.name}"
                    )
                    metadata["extraction_method"] = "metadata"
                    return metadata
                else:
                    logger.info(
                        f"Metadata-first: incomplete results from {repository.name}, "
                        f"falling back to data download"
                    )
        except Exception as e:
            logger.warning(
                f"Metadata-first: metadata extraction failed for {repository.name}: {e}, "
                f"falling back to data download"
            )
    else:
        logger.debug(
            f"{repository.name} does not support metadata extraction, "
            f"proceeding directly with data download"
        )

    # Phase 2: Fall back to data download
    if not keep_files:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                logger.debug(f"Created temporary directory: {tmp}")
                metadata = _process_remote_download(
                    tmp=tmp, download_data=True, **_common_kwargs
                )
                metadata["extraction_method"] = "download"

                logger.debug(f"Cleaning up temporary directory: {tmp}")
                try:
                    shutil.rmtree(tmp)
                except Exception as cleanup_error:
                    logger.warning(
                        f"Failed to explicitly clean up {tmp}: {cleanup_error}. "
                        f"TemporaryDirectory context manager will attempt cleanup."
                    )
            return metadata
        except ValueError as e:
            raise Exception(e)
    else:
        tmp = tempfile.mkdtemp(prefix="geoextent_keep_")
        logger.info(f"Created persistent directory (will NOT be cleaned up): {tmp}")
        try:
            metadata = _process_remote_download(
                tmp=tmp, download_data=True, **_common_kwargs
            )
            metadata["extraction_method"] = "download"
            logger.info(f"Files kept in: {tmp}")
            return metadata
        except Exception as e:
            logger.debug(f"Error occurred, cleaning up directory: {tmp}")
            try:
                shutil.rmtree(tmp)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up directory {tmp}: {cleanup_error}")
            raise


def _extract_from_remote(
    remote_identifier,
    bbox=False,
    tbox=False,
    convex_hull=False,
    details=False,
    throttle=False,
    timeout=None,
    download_data=True,
    show_progress=True,
    recursive=True,
    include_geojsonio=False,
    max_download_size=None,
    max_download_method="ordered",
    max_download_method_seed=hf.DEFAULT_DOWNLOAD_SAMPLE_SEED,
    placename=None,
    placename_escape=False,
    download_skip_nogeo=False,
    download_skip_nogeo_exts=None,
    max_download_workers=4,
    keep_files=False,
    assume_wgs84=False,
    metadata_first=False,
    metadata_fallback=True,
    time_format=None,
):
    """
    Internal method to extract extent from a single remote identifier.

    This method handles the download, extraction, and cleanup logic.
    """
    import shutil
    from pathlib import Path

    if bbox + tbox == 0:
        logger.error(
            "Require at least one of extraction options, but bbox is {} and tbox is {}".format(
                bbox, tbox
            )
        )
        raise Exception("No extraction options enabled!")

    from .content_providers.providers import find_provider

    repository = find_provider(remote_identifier, _get_content_providers())
    supported_by_geoextent = repository is not None

    if supported_by_geoextent:
        logger.debug(
            "Using {} to extract {}".format(repository.name, remote_identifier)
        )

        # Metadata-first strategy: try metadata-only extraction, then fall back
        if metadata_first:
            metadata = _metadata_first_extract(
                repository=repository,
                bbox=bbox,
                tbox=tbox,
                convex_hull=convex_hull,
                details=details,
                throttle=throttle,
                timeout=timeout,
                download_data=download_data,
                show_progress=show_progress,
                recursive=recursive,
                include_geojsonio=include_geojsonio,
                max_download_size=max_download_size,
                max_download_method=max_download_method,
                max_download_method_seed=max_download_method_seed,
                placename=placename,
                placename_escape=placename_escape,
                download_skip_nogeo=download_skip_nogeo,
                download_skip_nogeo_exts=download_skip_nogeo_exts,
                max_download_workers=max_download_workers,
                keep_files=keep_files,
                assume_wgs84=assume_wgs84,
                time_format=time_format,
            )
            return metadata

        # Determine directory strategy based on keep_files setting
        if not keep_files:
            # Use context manager for automatic cleanup
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    logger.debug(f"Created temporary directory: {tmp}")

                    # Process the download and extraction (shared logic)
                    metadata = _process_remote_download(
                        repository=repository,
                        tmp=tmp,
                        throttle=throttle,
                        download_data=download_data,
                        show_progress=show_progress,
                        max_download_size=max_download_size,
                        max_download_method=max_download_method,
                        max_download_method_seed=max_download_method_seed,
                        download_skip_nogeo=download_skip_nogeo,
                        download_skip_nogeo_exts=download_skip_nogeo_exts,
                        max_download_workers=max_download_workers,
                        bbox=bbox,
                        tbox=tbox,
                        convex_hull=convex_hull,
                        details=details,
                        timeout=timeout,
                        recursive=recursive,
                        include_geojsonio=include_geojsonio,
                        placename=placename,
                        placename_escape=placename_escape,
                        assume_wgs84=assume_wgs84,
                        metadata_fallback=metadata_fallback,
                        time_format=time_format,
                    )

                    # Explicitly clean up temporary directory
                    logger.debug(f"Cleaning up temporary directory: {tmp}")
                    try:
                        shutil.rmtree(tmp)
                        logger.debug(f"Successfully removed temporary directory: {tmp}")
                    except Exception as cleanup_error:
                        logger.warning(
                            f"Failed to explicitly clean up {tmp}: {cleanup_error}. "
                            f"TemporaryDirectory context manager will attempt cleanup."
                        )
                return metadata
            except ValueError as e:
                raise Exception(e)
        else:
            # Create persistent directory for keep_files mode
            tmp = tempfile.mkdtemp(prefix="geoextent_keep_")
            logger.info(f"Created persistent directory (will NOT be cleaned up): {tmp}")

            try:
                # Process the download and extraction (shared logic)
                metadata = _process_remote_download(
                    repository=repository,
                    tmp=tmp,
                    throttle=throttle,
                    download_data=download_data,
                    show_progress=show_progress,
                    max_download_size=max_download_size,
                    max_download_method=max_download_method,
                    max_download_method_seed=max_download_method_seed,
                    download_skip_nogeo=download_skip_nogeo,
                    download_skip_nogeo_exts=download_skip_nogeo_exts,
                    max_download_workers=max_download_workers,
                    bbox=bbox,
                    tbox=tbox,
                    convex_hull=convex_hull,
                    details=details,
                    timeout=timeout,
                    recursive=recursive,
                    include_geojsonio=include_geojsonio,
                    placename=placename,
                    placename_escape=placename_escape,
                    metadata_fallback=metadata_fallback,
                    time_format=time_format,
                )

                logger.info(f"Files kept in: {tmp}")
                return metadata
            except Exception as e:
                # Even with keep_files, clean up on error
                logger.debug(f"Error occurred, cleaning up directory: {tmp}")
                try:
                    shutil.rmtree(tmp)
                    logger.debug(
                        f"Successfully cleaned up directory after error: {tmp}"
                    )
                except Exception as cleanup_error:
                    logger.warning(
                        f"Failed to clean up directory {tmp}: {cleanup_error}"
                    )
                raise
    else:
        logger.error(
            "Geoextent can not handle this repository identifier {}"
            "\n Check for typos or if the repository exists. ".format(remote_identifier)
        )
