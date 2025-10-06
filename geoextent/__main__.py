import argparse
import json
import logging
import os
import sys
import warnings
import webbrowser
import zipfile
from .lib import extent
from .lib import helpfunctions as hf

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("geoextent")

from setuptools_scm import get_version

help_description = """
geoextent is a Python library for extracting geospatial and temporal extents of a file
 or a directory of multiple geospatial data formats.
"""

help_epilog = """

Examples:

geoextent -b path/to/directory_with_geospatial_data
geoextent -t path/to/file_with_temporal_extent
geoextent -b -t path/to/geospatial_files
geoextent -b -t --details path/to/zipfile_with_geospatial_data
geoextent -b -t file1.shp file2.csv file3.geopkg
geoextent -t *.geojson
geoextent -b -t https://doi.org/10.1594/PANGAEA.918707 https://doi.pangaea.de/10.1594/PANGAEA.858767
geoextent -b --convex-hull https://zenodo.org/record/4567890 10.1594/PANGAEA.123456
geoextent -b --placename file.geojson
geoextent -b --placename --placename-service nominatim https://zenodo.org/record/123456
geoextent -b --placename --placename-service photon --placename-escape https://doi.org/10.3897/BDJ.13.e159973
"""

supported_formats = """
Supported formats:
- GeoJSON (.geojson)
- Tabular data (.csv)
- GeoTIFF (.geotiff, .tif)
- Shapefile (.shp)
- GeoPackage (.gpkg)
- GPS Exchange Format (.gpx)
- Geography Markup Language (.gml)
- Keyhole Markup Language (.kml)
- FlatGeobuf (.fgb)

Supported data repositories:
- Zenodo (zenodo.org)
- Dryad (datadryad.org)
- Figshare (figshare.com)
- PANGAEA (pangaea.de)
- OSF (osf.io)
- GFZ Data Services (dataservices.gfz-potsdam.de)
- Pensoft Journals (e.g., bdj.pensoft.net)

"""


# custom action, see e.g. https://stackoverflow.com/questions/11415570/directory-path-types-with-argparse


class readable_file_or_dir(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        validated_files = []
        for candidate in values:
            # Check if it's a supported repository URL/DOI by testing against content providers
            is_repository = self._is_supported_repository(candidate)

            if is_repository:
                logger.debug(
                    "The format of the URL or DOI is correct. Geoextent is going to try to download "
                    "this repository from {} ".format(candidate)
                )
                validated_files.append(candidate)
            else:
                if not (
                    os.path.isdir(candidate)
                    or os.path.isfile(candidate)
                    or zipfile.is_zipfile(candidate)
                ):
                    raise argparse.ArgumentTypeError(
                        "{0} is not a valid directory or file".format(candidate)
                    )
                if os.access(candidate, os.R_OK):
                    validated_files.append(candidate)
                else:
                    raise argparse.ArgumentTypeError(
                        "{0} is not a readable directory or file".format(candidate)
                    )
        setattr(namespace, self.dest, validated_files)

    def _is_supported_repository(self, candidate):
        """Check if the candidate is supported by any content provider"""
        # Import content providers
        from .lib.content_providers import (
            Dryad,
            Figshare,
            Zenodo,
            Pangaea,
            OSF,
            GFZ,
            Pensoft,
        )

        # Test against all content providers
        content_providers = [
            Dryad.Dryad,
            Figshare.Figshare,
            Zenodo.Zenodo,
            Pangaea.Pangaea,
            OSF.OSF,
            GFZ.GFZ,
            Pensoft.Pensoft,
        ]

        for provider_class in content_providers:
            provider = provider_class()
            if provider.validate_provider(candidate):
                return True

        # Also check legacy DOI regex pattern for backward compatibility
        if hf.doi_regexp.match(candidate) is not None:
            return True

        return False


def get_arg_parser():
    """Get arguments to extract geoextent"""
    parser = argparse.ArgumentParser(
        add_help=False,
        prog="geoextent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage="geoextent [-h] [--formats] [--list-features] [--version] [--debug] [--details] [--output] [output file] [-b] [-t] [--convex-hull] [--no-download-data] [--no-progress] [--quiet] [--format {geojson,wkt,wkb}] [--no-subdirs] [--geojsonio] [--browse] [--placename] [--placename-service GAZETTEER] [--placename-escape] [--max-download-size SIZE] [--max-download-method {ordered,random,smallest,largest}] [--max-download-method-seed SEED] [--download-skip-nogeo] [--download-skip-nogeo-exts EXTS] [--max-download-workers WORKERS] input1 [input2 ...]",
    )

    parser.add_argument(
        "-h", "--help", action="store_true", help="show help message and exit"
    )

    parser.add_argument("--formats", action="store_true", help="show supported formats")

    parser.add_argument(
        "--list-features",
        action="store_true",
        help="output machine-readable JSON with all supported file formats and content providers"
    )

    parser.add_argument("--version", action="store_true", help="show installed version")

    parser.add_argument(
        "--debug",
        help="turn on debug logging, alternatively set environment variable GEOEXTENT_DEBUG=1",
        action="store_true",
    )

    parser.add_argument(
        "--details",
        action="store_true",
        default=False,
        help="Returns details of folder/zipFiles geoextent extraction",
    )

    parser.add_argument(
        "--output",
        action="store",
        default=None,
        help="Creates geopackage with geoextent output",
    )

    parser.add_argument(
        "-b",
        "--bounding-box",
        action="store_true",
        default=False,
        help="extract spatial extent (bounding box)",
    )

    parser.add_argument(
        "-t",
        "--time-box",
        action="store_true",
        default=False,
        help="extract temporal extent (%%Y-%%m-%%d)",
    )

    parser.add_argument(
        "--convex-hull",
        action="store_true",
        default=False,
        help="extract convex hull instead of bounding box for vector geometries",
    )

    parser.add_argument(
        "--no-download-data",
        action="store_false",
        dest="download_data",
        default=True,
        help="for repositories: disable downloading data files and use metadata only (not recommended for most providers)",
    )

    parser.add_argument(
        "--no-progress",
        action="store_true",
        default=False,
        help="disable progress bars during download and extraction",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="suppress all console messages including warnings and progress bars",
    )

    parser.add_argument(
        "--format",
        choices=["geojson", "wkt", "wkb"],
        default="geojson",
        help="output format for spatial extents (default: geojson)",
    )

    parser.add_argument(
        "--no-subdirs",
        action="store_true",
        default=False,
        help="only process files in the top-level directory, ignore subdirectories",
    )

    parser.add_argument(
        "--geojsonio",
        action="store_true",
        default=False,
        help="generate and print a clickable geojson.io URL for the extracted spatial extent",
    )

    parser.add_argument(
        "--browse",
        action="store_true",
        default=False,
        help="open the geojson.io URL in the default web browser (use with --geojsonio to also print URL)",
    )

    parser.add_argument(
        "--no-metadata",
        action="store_true",
        default=False,
        help="exclude extraction metadata and statistics from GeoJSON output",
    )

    parser.add_argument(
        "--max-download-size",
        action="store",
        default=None,
        help="maximum download size limit (e.g. '100MB', '2GB'). Uses filesizelib for parsing.",
    )

    parser.add_argument(
        "--max-download-method",
        choices=["ordered", "random", "smallest", "largest"],
        default="ordered",
        help="method for selecting files when size limit is exceeded: 'ordered' (as returned by provider), 'random', 'smallest' (smallest files first), 'largest' (largest files first) (default: ordered)",
    )

    parser.add_argument(
        "--max-download-method-seed",
        type=int,
        default=None,  # Will use DEFAULT_DOWNLOAD_SAMPLE_SEED if not specified
        help="seed for random file selection when using --max-download-method random (default: 42)",
    )

    parser.add_argument(
        "--placename",
        action="store_true",
        default=False,
        help="enable placename lookup using default gazetteer (geonames). Use --placename-service to specify a different gazetteer",
    )

    parser.add_argument(
        "--placename-service",
        choices=["geonames", "nominatim", "photon"],
        default=None,
        metavar="GAZETTEER",
        help="specify gazetteer service for placename lookup (requires --placename)",
    )

    parser.add_argument(
        "--placename-escape",
        action="store_true",
        default=False,
        help="escape Unicode characters in placename output (requires --placename)",
    )

    parser.add_argument(
        "--download-skip-nogeo",
        action="store_true",
        default=False,
        help="skip downloading files that don't appear to contain geospatial data (e.g., PDFs, images, plain text)",
    )

    parser.add_argument(
        "--download-skip-nogeo-exts",
        type=str,
        default="",
        help="comma-separated list of additional file extensions to consider as geospatial (e.g., '.xyz,.las,.ply')",
    )

    parser.add_argument(
        "--max-download-workers",
        type=int,
        default=4,
        help="maximum number of parallel downloads (default: 4, set to 1 to disable parallel downloads)",
    )

    parser.add_argument(
        "files",
        action=readable_file_or_dir,
        nargs="+",
        help="input file, directory, DOI, or repository URL (supports multiple inputs including mixed types)",
    )

    return parser


def print_help():
    print(help_description)
    arg_parser.print_help()
    print(help_epilog)
    print_supported_formats()


def print_supported_formats():
    print(supported_formats)


def print_version():
    print(get_version())


def print_features_json():
    """Print machine-readable JSON with supported features."""
    from .lib.features import get_supported_features_json
    print(get_supported_features_json())


arg_parser = get_arg_parser()


def _parse_additional_extensions(ext_string):
    """Parse comma-separated extension string into a set of normalized extensions."""
    if not ext_string.strip():
        return set()

    extensions = set()
    for ext in ext_string.split(","):
        ext = ext.strip()
        if ext:
            # Normalize extension (ensure it starts with a dot and is lowercase)
            if not ext.startswith("."):
                ext = "." + ext
            extensions.add(ext.lower())

    return extensions


def main():
    # Check if there is no arguments, then print help
    if len(sys.argv[1:]) == 0:
        print_help()
        arg_parser.exit()

    # version, help, and formats must be checked before parse, as otherwise files are required
    # but arg parser gives an error if allowed to be parsed first
    if "--help" in sys.argv or "-h" in sys.argv:
        print_help()
        arg_parser.exit()
    if "--version" in sys.argv:
        print_version()
        arg_parser.exit()
    if "--formats" in sys.argv:
        print_supported_formats()
        arg_parser.exit()
    if "--list-features" in sys.argv:
        print_features_json()
        arg_parser.exit()

    args = vars(arg_parser.parse_args())
    files = args["files"]

    # Parse additional file extensions for geospatial detection
    additional_extensions = _parse_additional_extensions(
        args["download_skip_nogeo_exts"]
    )

    if files is None or len(files) == 0:
        raise Exception("Invalid command, input file missing")

    # Validate placename options
    if args["placename_escape"] and not args["placename"]:
        raise ValueError("--placename-escape requires --placename to be specified")

    if args["placename_service"] and not args["placename"]:
        raise ValueError("--placename-service requires --placename to be specified")

    # Determine gazetteer service to use
    placename_service = None
    if args["placename"]:
        placename_service = args["placename_service"] or "geonames"

    logger.debug("Extracting from inputs %s", files)
    # Set logging level and handle conflicting options
    if args["debug"] and args["quiet"]:
        # Conflict detected: debug takes priority, reset quiet to default
        logging.getLogger("geoextent").setLevel(logging.DEBUG)
        logger.critical(
            "Conflicting options --debug and --quiet provided. "
            "Debug mode takes priority, quiet mode disabled."
        )
        args["quiet"] = False
        args["no_progress"] = False
    elif args["quiet"]:
        # Quiet mode: suppress all warnings and enable no-progress
        logging.getLogger("geoextent").setLevel(logging.CRITICAL)
        # Suppress INFO level messages from all loggers (including patool, etc.)
        logging.getLogger().setLevel(logging.WARNING)
        logging.getLogger("patool").setLevel(logging.WARNING)
        # Also suppress Python warnings (including pandas UserWarnings)
        warnings.filterwarnings("ignore")
        args["no_progress"] = True
    elif args["debug"]:
        logging.getLogger("geoextent").setLevel(logging.DEBUG)
    elif os.environ.get("GEOEXTENT_DEBUG", None) == "1":
        logging.getLogger("geoextent").setLevel(logging.DEBUG)

    # Check output path
    export = args["output"] is not None

    try:
        if export:
            filename = hf.path_output(args["output"])
    except ValueError as e:
        raise ValueError(e)

    output = None
    multiple_files = len(files) > 1

    try:
        if len(files) == 1:
            # Single file/directory/URL handling (existing behavior)
            single_input = files[0]

            # Identify local file source
            is_file = os.path.isfile(os.path.join(os.getcwd(), single_input))
            is_zipfile = zipfile.is_zipfile(os.path.join(os.getcwd(), single_input))
            is_directory = os.path.isdir(os.path.join(os.getcwd(), single_input))

            # Identify URL, DOI, or repository identifier
            is_url = hf.https_regexp.match(single_input) is not None
            is_doi = hf.doi_regexp.match(single_input) is not None

            # Check if it's a supported repository identifier (for cases like OSF.IO/9JG2U)
            rfd_instance = readable_file_or_dir(None, None)
            is_repository = rfd_instance._is_supported_repository(single_input)

            if is_file and not is_zipfile:
                output = extent.fromFile(
                    single_input,
                    bbox=args["bounding_box"],
                    tbox=args["time_box"],
                    convex_hull=args["convex_hull"],
                    show_progress=not args["no_progress"],
                    placename=placename_service,
                    placename_escape=args["placename_escape"],
                )
            elif is_directory or is_zipfile:
                output = extent.fromDirectory(
                    single_input,
                    bbox=args["bounding_box"],
                    tbox=args["time_box"],
                    convex_hull=args["convex_hull"],
                    details=True,
                    show_progress=not args["no_progress"],
                    recursive=not args["no_subdirs"],
                    placename=placename_service,
                    placename_escape=args["placename_escape"],
                )
            elif is_url or is_doi or is_repository:
                output = extent.fromRemote(
                    single_input,
                    bbox=args["bounding_box"],
                    tbox=args["time_box"],
                    convex_hull=args["convex_hull"],
                    details=True,
                    download_data=args["download_data"],
                    show_progress=not args["no_progress"],
                    recursive=not args["no_subdirs"],
                    max_download_size=args["max_download_size"],
                    max_download_method=args["max_download_method"],
                    max_download_method_seed=args["max_download_method_seed"]
                    or hf.DEFAULT_DOWNLOAD_SAMPLE_SEED,
                    placename=placename_service,
                    placename_escape=args["placename_escape"],
                    download_skip_nogeo=args["download_skip_nogeo"],
                    download_skip_nogeo_exts=additional_extensions,
                    max_download_workers=args["max_download_workers"],
                )
        else:
            # Multiple files handling
            output = {}
            output["format"] = "multiple_files"
            output["details"] = {}

            # Process each file or repository identifier
            for file_path in files:
                logger.debug("Processing input: %s", file_path)
                try:
                    # Check if it's a repository identifier (URL, DOI, etc.)
                    is_url = hf.https_regexp.match(file_path) is not None
                    is_doi = hf.doi_regexp.match(file_path) is not None
                    rfd_instance = readable_file_or_dir(None, None)
                    is_repository = rfd_instance._is_supported_repository(file_path)

                    if is_url or is_doi or is_repository:
                        # Process repository identifier
                        repo_output = extent.fromRemote(
                            file_path,
                            bbox=args["bounding_box"],
                            tbox=args["time_box"],
                            convex_hull=args["convex_hull"],
                            details=True,
                            download_data=args["download_data"],
                            show_progress=not args["no_progress"],
                            recursive=not args["no_subdirs"],
                            max_download_size=args["max_download_size"],
                            max_download_method=args["max_download_method"],
                            max_download_method_seed=args["max_download_method_seed"]
                            or hf.DEFAULT_DOWNLOAD_SAMPLE_SEED,
                            placename=placename_service,
                            placename_escape=args["placename_escape"],
                            download_skip_nogeo=args["download_skip_nogeo"],
                            download_skip_nogeo_exts=additional_extensions,
                            max_download_workers=args["max_download_workers"],
                        )
                        if repo_output is not None:
                            output["details"][file_path] = repo_output
                    elif os.path.isfile(file_path) and not zipfile.is_zipfile(
                        file_path
                    ):
                        # Process individual file
                        file_output = extent.fromFile(
                            file_path,
                            bbox=args["bounding_box"],
                            tbox=args["time_box"],
                            convex_hull=args["convex_hull"],
                            show_progress=not args["no_progress"],
                            placename=placename_service,
                            placename_escape=args["placename_escape"],
                        )
                        if file_output is not None:
                            output["details"][file_path] = file_output
                    elif os.path.isdir(file_path) or zipfile.is_zipfile(file_path):
                        # Process directory or zip file
                        dir_output = extent.fromDirectory(
                            file_path,
                            bbox=args["bounding_box"],
                            tbox=args["time_box"],
                            convex_hull=args["convex_hull"],
                            details=True,
                            show_progress=not args["no_progress"],
                            recursive=not args["no_subdirs"],
                            placename=placename_service,
                            placename_escape=args["placename_escape"],
                        )
                        if dir_output is not None:
                            output["details"][file_path] = dir_output
                    else:
                        logger.warning("Skipping unsupported input: %s", file_path)
                except Exception as file_error:
                    logger.warning(
                        "Error processing %s: %s", file_path, str(file_error)
                    )
                    continue

            # Merge spatial extents if bbox is requested
            if args["bounding_box"]:
                if args["convex_hull"]:
                    bbox_merge = hf.convex_hull_merge(
                        output["details"], "multiple_files"
                    )
                else:
                    bbox_merge = hf.bbox_merge(output["details"], "multiple_files")

                if bbox_merge is not None and len(bbox_merge) != 0:
                    output["crs"] = bbox_merge["crs"]
                    output["bbox"] = bbox_merge["bbox"]
                    # Mark if this is from convex hull calculation
                    if args["convex_hull"] and "convex_hull" in bbox_merge:
                        output["convex_hull"] = bbox_merge["convex_hull"]

            # Merge temporal extents if tbox is requested
            if args["time_box"]:
                tbox_merge = hf.tbox_merge(output["details"], "multiple_files")
                if tbox_merge is not None:
                    output["tbox"] = tbox_merge

    except Exception as e:
        if logger.getEffectiveLevel() >= logging.DEBUG:
            logger.exception(e)
        sys.exit(1)

    if output is None:
        raise Exception("Did not find supported files at {}".format(files))
    else:

        if export and not multiple_files:
            logger.warning("Exporting result does not apply to single files")
        elif export and multiple_files:
            logger.warning("Exporting result into: {}".format(args["output"]))
            df = hf.extract_output(output, files, get_version())
            hf.create_geopackage(df, filename)

        # Create extraction metadata before removing details (unless --no-metadata is set)
        extraction_metadata = None
        if not args["no_metadata"]:
            extraction_metadata = hf.create_extraction_metadata(
                files, get_version(), output
            )

        if not args["details"]:
            output.pop("details", None)

        # Generate geojson.io URL if --geojsonio or --browse is requested (before format conversion)
        geojsonio_url = None
        if (args["geojsonio"] or args["browse"]) and output and "bbox" in output:
            geojsonio_url = hf.generate_geojsonio_url(output)

        # Apply output format conversion
        output = hf.format_extent_output(output, args["format"], extraction_metadata)

    # For WKT and WKB formats, output only the bbox value
    if args["format"].lower() in ["wkt", "wkb"] and output and "bbox" in output:
        print(output["bbox"])
    elif type(output) == list or type(output) == dict:
        print(json.dumps(output, ensure_ascii=False))
    else:
        print(output)

    # Print geojson.io URL if --geojsonio was requested
    if args["geojsonio"]:
        if geojsonio_url:
            print(f"\n🌍 View spatial extent at: {geojsonio_url}")
        elif not args["quiet"]:
            print(
                "\ngeojson.io URL could not be generated (no spatial extent found or geojsonio not available)"
            )

    # Open in browser if --browse flag is set
    if args["browse"]:
        if geojsonio_url:
            try:
                webbrowser.open(geojsonio_url)
                if not args["quiet"]:
                    print("Opening URL in default web browser...")
            except Exception as e:
                if not args["quiet"]:
                    print(f"Could not open browser: {e}")
        elif not args["quiet"]:
            print(
                "\ngeojson.io URL could not be generated (no spatial extent found or geojsonio not available)"
            )


if __name__ == "__main__":
    main()
