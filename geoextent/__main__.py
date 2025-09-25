import argparse
import json
import logging
import os
import sys
import warnings
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
        from .lib.content_providers import Dryad, Figshare, Zenodo, Pangaea, OSF, GFZ

        # Test against all content providers
        content_providers = [
            Dryad.Dryad,
            Figshare.Figshare,
            Zenodo.Zenodo,
            Pangaea.Pangaea,
            OSF.OSF,
            GFZ.GFZ,
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
        usage="geoextent [-h] [--formats] [--version] [--debug] [--details] [--output] [output file] [-b] [-t] [--convex-hull] [--no-download-data] [--no-progress] [--quiet] [--format {geojson,wkt,wkb}] [--no-subdirs] [--geojsonio] file1 [file2 ...]",
    )

    parser.add_argument(
        "-h", "--help", action="store_true", help="show help message and exit"
    )

    parser.add_argument("--formats", action="store_true", help="show supported formats")

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
        "files",
        action=readable_file_or_dir,
        nargs="+",
        help="input file or path (supports multiple files)",
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


arg_parser = get_arg_parser()


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

    args = vars(arg_parser.parse_args())
    files = args["files"]

    if files is None or len(files) == 0:
        raise Exception("Invalid command, input file missing")

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
                )
            elif is_url or is_doi or is_repository:
                output = extent.from_repository(
                    single_input,
                    bbox=args["bounding_box"],
                    tbox=args["time_box"],
                    convex_hull=args["convex_hull"],
                    details=True,
                    download_data=args["download_data"],
                    show_progress=not args["no_progress"],
                    recursive=not args["no_subdirs"],
                )
        else:
            # Multiple files handling
            output = {}
            output["format"] = "multiple_files"
            output["details"] = {}

            # Process each file
            for file_path in files:
                logger.debug("Processing file: %s", file_path)
                try:
                    # Only process individual files (not directories or URLs for multiple mode)
                    if os.path.isfile(file_path) and not zipfile.is_zipfile(file_path):
                        file_output = extent.fromFile(
                            file_path,
                            bbox=args["bounding_box"],
                            tbox=args["time_box"],
                            convex_hull=args["convex_hull"],
                            show_progress=not args["no_progress"],
                        )
                        if file_output is not None:
                            output["details"][file_path] = file_output
                    elif os.path.isdir(file_path) or zipfile.is_zipfile(file_path):
                        dir_output = extent.fromDirectory(
                            file_path,
                            bbox=args["bounding_box"],
                            tbox=args["time_box"],
                            convex_hull=args["convex_hull"],
                            details=True,
                            show_progress=not args["no_progress"],
                            recursive=not args["no_subdirs"],
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
        if not args["details"]:
            output.pop("details", None)

        # Generate and print geojson.io URL if requested (before format conversion)
        geojsonio_url = None
        if args["geojsonio"] and output and "bbox" in output:
            geojsonio_url = hf.generate_geojsonio_url(output)

        # Apply output format conversion
        output = hf.format_extent_output(output, args["format"])

    # For WKT and WKB formats, output only the bbox value
    if args["format"].lower() in ["wkt", "wkb"] and output and "bbox" in output:
        print(output["bbox"])
    elif type(output) == list or type(output) == dict:
        print(json.dumps(output))
    else:
        print(output)

    # Print geojson.io URL if it was generated
    if args["geojsonio"]:
        if geojsonio_url:
            print(f"\n🌍 View spatial extent at: {geojsonio_url}")
        elif not args["quiet"]:
            print(
                "\ngeojson.io URL could not be generated (no spatial extent found or geojsonio not available)"
            )


if __name__ == "__main__":
    main()
