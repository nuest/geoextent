import logging
import os
import patoolib
import random
import threading
import time
import tempfile
from traitlets import List
from traitlets.config import Application
from .content_providers import Dryad
from .content_providers import Figshare
from .content_providers import Zenodo
from .content_providers import Pangaea
from .content_providers import OSF
from .content_providers import Dataverse
from .content_providers import GFZ
from .content_providers import Pensoft
from . import handleCSV
from . import handleRaster
from . import handleVector
from . import helpfunctions as hf

logger = logging.getLogger("geoextent")
handle_modules = {"CSV": handleCSV, "raster": handleRaster, "vector": handleVector}


def compute_bbox_wgs84(module, path):
    """
    input "module": type module, module from which methods shall be used \n
    input "path": type string, path to file \n
    returns a bounding box, type list, length = 4 , type = float,
        schema = [min(longs), min(lats), max(longs), max(lats)],
        the bounding box has either its original crs or WGS84(transformed).
    """
    logger.debug("compute_bbox_wgs84: {}".format(path))
    spatial_extent_origin = module.getBoundingBox(path)

    try:
        if spatial_extent_origin["crs"] == str(hf.WGS84_EPSG_ID):
            spatial_extent = spatial_extent_origin
        else:
            spatial_extent = {
                "bbox": hf.transformingArrayIntoWGS84(
                    spatial_extent_origin["crs"], spatial_extent_origin["bbox"]
                ),
                "crs": str(hf.WGS84_EPSG_ID),
            }
    except Exception as e:
        raise Exception(
            "The bounding box could not be transformed to the target CRS epsg:{} \n error {}".format(
                hf.WGS84_EPSG_ID, e
            )
        )

    validate = hf.validate_bbox_wgs84(spatial_extent["bbox"])
    logger.debug("Validate: {}".format(validate))

    if not hf.validate_bbox_wgs84(spatial_extent["bbox"]):
        try:
            flip_bbox = hf.flip_bbox(spatial_extent["bbox"])
            spatial_extent["bbox"] = flip_bbox

        except Exception as e:
            raise Exception(
                "The bounding box could not be transformed to the target CRS epsg:{} \n error {}".format(
                    hf.WGS84_EPSG_ID, e
                )
            )

    return spatial_extent


def compute_convex_hull_wgs84(module, path):
    """
    input "module": type module, module from which methods shall be used \n
    input "path": type string, path to file \n
    returns a convex hull as bounding box, type dict with keys 'bbox' and 'crs',
        the bounding box has either its original crs or WGS84(transformed).
    """
    logger.debug("compute_convex_hull_wgs84: {}".format(path))

    # Check if module has convex hull support
    if not hasattr(module, "getConvexHull"):
        logger.warning(
            "Module {} does not support convex hull calculation, falling back to bounding box".format(
                module.get_handler_name()
            )
        )
        return compute_bbox_wgs84(module, path)

    spatial_extent_origin = module.getConvexHull(path)

    if spatial_extent_origin is None:
        return None

    try:
        if spatial_extent_origin["crs"] == str(hf.WGS84_EPSG_ID):
            spatial_extent = spatial_extent_origin
        else:
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
    except Exception as e:
        raise Exception(
            "The convex hull could not be transformed to the target CRS epsg:{} \n error {}".format(
                hf.WGS84_EPSG_ID, e
            )
        )

    validate = hf.validate_bbox_wgs84(spatial_extent["bbox"])
    logger.debug("Validate convex hull: {}".format(validate))

    if not hf.validate_bbox_wgs84(spatial_extent["bbox"]):
        try:
            flip_bbox = hf.flip_bbox(spatial_extent["bbox"])
            spatial_extent["bbox"] = flip_bbox

        except Exception as e:
            raise Exception(
                "The convex hull could not be transformed to the target CRS epsg:{} \n error {}".format(
                    hf.WGS84_EPSG_ID, e
                )
            )

    return spatial_extent


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
                        if isinstance(bbox, list) and len(bbox) >= 3 and isinstance(bbox[0], list):
                            # This is coordinate array format, convert to envelope
                            x_coords = [coord[0] for coord in bbox if len(coord) >= 2]
                            y_coords = [coord[1] for coord in bbox if len(coord) >= 2]
                            if x_coords and y_coords:
                                fallback_file_metadata["bbox"] = [
                                    min(x_coords), min(y_coords), max(x_coords), max(y_coords)
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
        tbox_ext = hf.tbox_merge(metadata_directory, path)
        if tbox_ext is not None:
            metadata["tbox"] = tbox_ext
        else:
            logger.warning(
                "The {} {} has no identifiable time extent".format(file_format, path)
            )

    if details:
        metadata["details"] = metadata_directory

    if timeout and timeout_flag:
        metadata["timeout"] = timeout

    # Add geojson.io URL if requested and spatial extent is available
    if include_geojsonio and metadata.get("bbox"):
        geojsonio_url = hf.generate_geojsonio_url(metadata)
        if geojsonio_url:
            metadata["geojsonio_url"] = geojsonio_url

    return metadata


def fromFile(
    filepath,
    bbox=True,
    tbox=True,
    convex_hull=False,
    num_sample=None,
    show_progress=True,
    include_geojsonio=False,
):
    """Extracts geoextent from a file
    Keyword arguments:
    path -- filepath
    bbox -- True if bounding box is requested (default False)
    tbox -- True if time box is requested (default False)
    convex_hull -- True if convex hull should be calculated instead of bounding box (default False)
    num_sample -- sample size to determine time format (Only required for csv files)
    include_geojsonio -- True if geojson.io URL should be included in output (default False)
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
                                usedModule, filepath
                            )
                        else:
                            spatial_extent = compute_bbox_wgs84(usedModule, filepath)

                        if spatial_extent is not None:
                            # For convex hull, use the actual convex hull coordinates, not the envelope
                            if convex_hull and "convex_hull_coords" in spatial_extent:
                                metadata["bbox"] = spatial_extent["convex_hull_coords"]
                                metadata["convex_hull"] = True
                            else:
                                metadata["bbox"] = spatial_extent["bbox"]

                            metadata["crs"] = spatial_extent["crs"]
                except Exception as e:
                    logger.warning(
                        "Error for {} extracting bbox:\n{}".format(filepath, str(e))
                    )
            elif self.task == "tbox":
                try:
                    if tbox:
                        if usedModule.get_handler_name() == "handleCSV":
                            extract_tbox = usedModule.getTemporalExtent(
                                filepath, num_sample
                            )
                        else:
                            if num_sample is not None:
                                logger.warning(
                                    "num_sample parameter is ignored, only applies to CSV files"
                                )
                            extract_tbox = usedModule.getTemporalExtent(filepath)
                        if extract_tbox is not None:
                            metadata["tbox"] = extract_tbox
                except Exception as e:
                    logger.warning(
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

    logger.debug("Extraction finished: {}".format(str(metadata)))

    # Add geojson.io URL if requested and spatial extent is available
    if include_geojsonio and metadata.get("bbox"):
        geojsonio_url = hf.generate_geojsonio_url(metadata)
        if geojsonio_url:
            metadata["geojsonio_url"] = geojsonio_url

    return metadata


def fromRemote(
    remote_identifier: str,
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
):
    try:
        geoextent = geoextent_from_repository()
        metadata = geoextent.fromRemote(
            remote_identifier,
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
        )
        metadata["format"] = "remote"
    except ValueError as e:
        logger.debug(
            "Error while inspecting remote source {}: {}".format(remote_identifier, e)
        )
        raise Exception(e)

    return metadata


# Backward compatibility alias
def from_repository(
    repository_identifier: str,
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
):
    """
    DEPRECATED: Use fromRemote() instead.
    Extract geospatial extent from remote sources (repositories, journals, preprint servers).

    This function is maintained for backward compatibility.
    """
    import warnings
    warnings.warn(
        "from_repository() is deprecated. Use fromRemote() instead to better reflect "
        "support for journals and preprint servers in addition to repositories.",
        DeprecationWarning,
        stacklevel=2
    )
    return fromRemote(
        repository_identifier,
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
    )


class geoextent_from_repository(Application):
    content_providers = List(
        [
            Dryad.Dryad,
            Figshare.Figshare,
            Zenodo.Zenodo,
            Pangaea.Pangaea,
            OSF.OSF,
            Dataverse.Dataverse,
            GFZ.GFZ,
            Pensoft.Pensoft,
        ],
        config=True,
        help="""
        Ordered list by priority of ContentProviders to try in turn to fetch
        the contents specified by the user.
        """,
    )

    def fromRemote(
        self,
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
    ):

        if bbox + tbox == 0:
            logger.error(
                "Require at least one of extraction options, but bbox is {} and tbox is {}".format(
                    bbox, tbox
                )
            )
            raise Exception("No extraction options enabled!")

        supported_by_geoextent = False
        for h in self.content_providers:
            repository = h()
            if repository.validate_provider(reference=remote_identifier):
                logger.debug(
                    "Using {} to extract {}".format(
                        repository.name, remote_identifier
                    )
                )
                supported_by_geoextent = True
                try:
                    with tempfile.TemporaryDirectory() as tmp:
                        # Parse download size if provided
                        max_size_bytes = None
                        if max_download_size:
                            max_size_bytes = hf.parse_download_size(max_download_size)
                            if max_size_bytes is None:
                                logger.warning(f"Invalid download size format: {max_download_size}")

                        repository.download(
                            tmp,
                            throttle,
                            download_data,
                            show_progress,
                            max_size_bytes=max_size_bytes,
                            max_download_method=max_download_method,
                            max_download_method_seed=max_download_method_seed,
                        )
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
                        )
                    return metadata
                except ValueError as e:
                    raise Exception(e)

        # Only show error if no provider could handle the identifier
        if not supported_by_geoextent:
            logger.error(
                "Geoextent can not handle this repository identifier {}"
                "\n Check for typos or if the repository exists. ".format(
                    remote_identifier
                )
            )
