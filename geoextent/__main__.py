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
from .lib.exceptions import DownloadSizeExceeded

logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("geoextent")

from . import __version__

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
geoextent -b -t --geojsonio --no-download-data 10.25928/HK1000
geoextent -t *.geojson
geoextent -b -t https://doi.org/10.1594/PANGAEA.918707 https://doi.pangaea.de/10.1594/PANGAEA.858767
geoextent -b --convex-hull https://zenodo.org/record/4567890 10.1594/PANGAEA.123456
geoextent -b --placename file.geojson
geoextent -b --placename --placename-service nominatim https://zenodo.org/record/123456
geoextent -b --placename --placename-service photon --placename-escape https://doi.org/10.3897/BDJ.13.e159973
"""


def get_supported_formats_text():
    """Generate supported formats text dynamically from features API."""
    from .lib.features import get_supported_features

    features = get_supported_features()

    lines = ["", "Supported formats:"]

    # Add file formats
    for fmt in features.get("file_formats", []):
        display_name = fmt.get("display_name", "")
        extensions = fmt.get("file_extensions", [])
        ext_str = ", ".join(extensions) if extensions else ""
        lines.append(f"- {display_name} ({ext_str})")

    lines.append("")
    lines.append("Supported data repositories:")

    # Add content providers
    for provider in features.get("content_providers", []):
        name = provider.get("name", "")
        website = provider.get("website", "")
        # Extract domain from website
        domain = (
            website.replace("https://", "")
            .replace("http://", "")
            .replace("www.", "")
            .rstrip("/")
        )
        lines.append(f"- {name} ({domain})")

    lines.append("")
    return "\n".join(lines)


# Note: supported_formats is now generated on-demand in print_supported_formats()


# custom action, see e.g. https://stackoverflow.com/questions/11415570/directory-path-types-with-argparse


class readable_file_or_dir(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        validated_files = []
        for candidate in values:
            # Stdin sentinel for text input (issue #112)
            if candidate == "-":
                validated_files.append(candidate)
                continue
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
        from .lib.content_providers.providers import find_provider
        from .lib.extent import _get_content_providers

        provider = find_provider(candidate, _get_content_providers())
        if provider is not None:
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
        usage="geoextent [-h] [--formats] [--list-features] [--version] [--debug] [--details] [--output] [output file] [--join] [-b] [-t] [--convex-hull] [--no-download-data] [--no-metadata-fallback] [--no-progress] [--quiet] [--format {geojson,wkt,wkb}] [--no-subdirs] [--geojsonio] [--browse] [--placename] [--placename-service GAZETTEER] [--placename-escape] [--max-download-size SIZE] [--max-download-method {ordered,random,smallest,largest}] [--max-download-method-seed SEED] [--download-skip-nogeo] [--download-skip-nogeo-exts EXTS] [--max-download-workers WORKERS] [--keep-files] [--assume-wgs84] input1 [input2 ...]",
    )

    parser.add_argument(
        "-h", "--help", action="store_true", help="show help message and exit"
    )

    parser.add_argument("--formats", action="store_true", help="show supported formats")

    parser.add_argument(
        "--list-features",
        action="store_true",
        help="output machine-readable JSON with all supported file formats and content providers",
    )

    parser.add_argument(
        "--list-periods",
        action="store_true",
        help="output the bundled named-time-period gazetteer (ICS GTS2020) "
        "with licensing and provenance metadata. Useful for downstream UIs "
        "and autocomplete widgets. Default format is JSON; use "
        "--list-periods-format to switch to a plain-text table.",
    )

    parser.add_argument(
        "--list-periods-format",
        choices=["json", "text"],
        default="json",
        help="output format for --list-periods (default: json)",
    )

    parser.add_argument(
        "--list-periods-filter",
        default=None,
        metavar="SUBSTR",
        help="case-insensitive substring match on period name or alias; "
        "only matching periods are listed",
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
        help="Export results to a file. Format is auto-detected from extension: "
        ".gpkg (GeoPackage), .geojson/.json (GeoJSON), .csv (CSV). "
        "Works with single files, directories, and remote sources.",
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
        "--time-format",
        default=None,
        metavar="FORMAT",
        help="output format for temporal extents. Presets: 'date' (%%Y-%%m-%%d, default), "
        "'iso8601' (%%Y-%%m-%%dT%%H:%%M:%%SZ). "
        "Also accepts strftime format strings (e.g. '%%Y/%%m/%%d %%H:%%M').",
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
        "--metadata-first",
        action="store_true",
        default=False,
        help="try metadata-only extraction first, fall back to data download if metadata yields no results (mutually exclusive with --no-download-data)",
    )

    parser.add_argument(
        "--no-metadata-fallback",
        action="store_false",
        dest="metadata_fallback",
        default=True,
        help="disable automatic metadata fallback when data download yields no files (by default, geoextent falls back to metadata-only extraction if data files are unavailable and the provider supports metadata)",
    )

    parser.add_argument(
        "--no-follow",
        action="store_false",
        dest="follow",
        default=True,
        help="disable following external DOIs/URLs to other providers "
        "(e.g., DEIMS-SDR datasets referencing Zenodo). By default, "
        "geoextent follows these references to extract actual data extents.",
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
        help="suppress all console messages including warnings, progress bars, "
        "map preview messages, and terminal display (--map FILE still saves the image silently)",
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
        help=(
            "generate and print a clickable geojson.io URL for the extracted "
            "spatial extent. GeoJSON payloads up to ~150 KB are embedded in "
            "the URL fragment; larger payloads attempt an anonymous GitHub "
            "Gist upload which now requires auth (geojsonio limitation, not "
            "geojson.io). Pair with --convex-hull to keep the payload small."
        ),
    )

    parser.add_argument(
        "--browse",
        action="store_true",
        default=False,
        help="open the geojson.io URL in the default web browser (use with --geojsonio to also print URL)",
    )

    parser.add_argument(
        "--map",
        nargs="?",
        const=True,
        default=None,
        metavar="FILE",
        help="save a map preview image of the spatial extent as PNG. "
        "If FILE is given, saves to that path; otherwise saves to a temporary file. "
        "(requires: pip install geoextent[preview])",
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        default=False,
        help="display a map preview of the spatial extent in the terminal (requires: pip install geoextent[preview])",
    )

    parser.add_argument(
        "--map-dim",
        action="store",
        default="600x400",
        metavar="WxH",
        help="dimensions of the map preview image in pixels (default: 600x400)",
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
        help="enable placename lookup using default gazetteer (nominatim — no API key required). Use --placename-service to specify a different gazetteer (geonames requires GEONAMES_USERNAME)",
    )

    parser.add_argument(
        "--placename-service",
        choices=["geonames", "nominatim", "photon"],
        default=None,
        metavar="GAZETTEER",
        help="specify gazetteer service for placename lookup (default: nominatim; requires --placename)",
    )

    parser.add_argument(
        "--placename-escape",
        action="store_true",
        default=False,
        help="escape Unicode characters in placename output (requires --placename)",
    )

    # --- Text / NER extraction (issue #112) ---------------------------------
    parser.add_argument(
        "--text-method",
        choices=["ner", "none"],
        default="ner",
        help="text-extraction method for plain-text files (.txt, .md, ...) "
        "and the --text/stdin inputs. 'ner' (default) uses spaCy NER to "
        "detect place names, calendar dates, and named time periods, "
        "resolving them via the configured place and period gazetteers. "
        "'none' disables text extraction (text files fall back to other "
        "handlers or are skipped). Requires: pip install geoextent[nlp] "
        "for any value other than 'none'; if spaCy is not installed, the "
        "text handler silently declines so existing workflows that happen "
        "to include text files keep working.",
    )

    parser.add_argument(
        "--text",
        action="store",
        default=None,
        metavar="STRING",
        help="run text extraction on this literal string (requires --text-method)",
    )

    parser.add_argument(
        "--ner-model",
        action="store",
        default=None,
        metavar="MODEL",
        help="spaCy model name for NER (default: en_core_web_sm). The model is "
        "auto-downloaded on first use unless --no-auto-download is set.",
    )

    parser.add_argument(
        "--ner-labels",
        action="store",
        default=None,
        metavar="LABELS",
        help="comma-separated entity labels to keep as places (default: LOC,GPE)",
    )

    parser.add_argument(
        "--ner-score-threshold",
        action="store",
        type=float,
        default=None,
        metavar="FLOAT",
        help="drop NER mentions with score below FLOAT (only used if the model "
        "emits per-entity scores; otherwise ignored)",
    )

    parser.add_argument(
        "--ner-gazetteer",
        choices=["geonames", "nominatim", "photon"],
        default=None,
        metavar="GAZETTEER",
        help="gazetteer used to forward-geocode detected place names "
        "(default: same as --placename-service if set, else nominatim, "
        "which works without an API key or login). Use 'geonames' for "
        "the GeoNames service (requires GEONAMES_USERNAME env var or .env).",
    )

    parser.add_argument(
        "--ner-ambiguity",
        choices=["drop", "top"],
        default="drop",
        help="how to handle ambiguous gazetteer hits: 'drop' (skip mentions "
        "with multiple candidates, default, defensive) or 'top' (keep the "
        "highest-ranked candidate)",
    )

    parser.add_argument(
        "--no-auto-download",
        action="store_false",
        dest="ner_auto_download",
        default=True,
        help="disable automatic spaCy model download on first use",
    )

    parser.add_argument(
        "--period-gazetteer",
        choices=["bundled", "none"],
        default="bundled",
        help="gazetteer used to resolve named time periods (e.g. 'Holocene', "
        "'Mesozoic Era') to signed ISO date ranges. 'bundled' uses the "
        "ICS GTS2020 chronostratigraphic chart shipped with geoextent "
        "(default). 'none' disables period matching.",
    )

    parser.add_argument(
        "--period-ambiguity",
        choices=["drop", "top"],
        default="drop",
        help="how to handle ambiguous period gazetteer hits: 'drop' (default, "
        "defensive) or 'top' (keep the highest-ranked candidate)",
    )

    parser.add_argument(
        "--no-period-resolution",
        action="store_false",
        dest="period_resolution",
        default=True,
        help="disable named time-period matching entirely (still parses "
        "DATE/TIME entities via dateutil)",
    )

    parser.add_argument(
        "--no-source-text",
        action="store_false",
        dest="include_source_text",
        default=True,
        help="omit the NFC-normalised source string from text/NER results "
        "(opt-out for privacy or to shrink output size; offsets in "
        "place_names and date_entities still index into the normalised "
        "source the extractor used internally)",
    )

    parser.add_argument(
        "--place-geometry",
        choices=["auto", "boundary", "point"],
        default="auto",
        help="how to use the gazetteer geometry for matched place names "
        "in the spatial extent. 'auto' (default) uses the administrative "
        "boundary or other areal polygon when the gazetteer provides one "
        "(Nominatim does for administrative regions; GeoNames and Photon "
        "are point-only), and falls back to the centroid point otherwise. "
        "'boundary' is the same but logs a debug message on point-only "
        "fallback. 'point' forces the centroid lat/lon even when a "
        "boundary is available.",
    )

    parser.add_argument(
        "--annotate",
        choices=["auto", "ansi", "brackets", "off"],
        default="auto",
        help="when text/NER inputs are processed, print the source text after "
        "the JSON result with matched place names and dates highlighted. "
        "'ansi' uses terminal colour, 'brackets' uses textual markers "
        "(``[[Berlin|place]]``), 'auto' picks based on TTY, 'off' disables. "
        "Default: auto.",
    )

    parser.add_argument(
        "--annotate-classes",
        default=None,
        metavar="MAP",
        help="comma-separated overrides for --annotate colours/markers. "
        "Example: 'place=cyan,date=yellow,period=magenta'. Recognised "
        "ANSI names: black, red, green, yellow, blue, magenta, cyan, white "
        "(bright_* prefix for bold variants).",
    )

    parser.add_argument(
        "--ext-metadata",
        action="store_true",
        default=False,
        help="retrieve external metadata for DOIs (title, authors, publisher, publication year, URL, license) from CrossRef and DataCite",
    )

    parser.add_argument(
        "--ext-metadata-method",
        choices=["auto", "all", "crossref", "datacite"],
        default="auto",
        help="method for retrieving external metadata: 'auto' (try CrossRef first, then DataCite), 'all' (query all sources), 'crossref' (CrossRef only), 'datacite' (DataCite only) (default: auto)",
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
        "--keep-files",
        action="store_true",
        default=False,
        help="keep downloaded and extracted files instead of cleaning them up (for debugging purposes)",
    )

    parser.add_argument(
        "--legacy",
        action="store_true",
        default=False,
        help="use traditional GIS coordinate order (longitude, latitude) instead of EPSG:4326 native order (latitude, longitude)",
    )

    parser.add_argument(
        "--assume-wgs84",
        action="store_true",
        default=False,
        help="assume WGS84 (EPSG:4326) for raster files without projection information (e.g., world files without .prj). By default, ungeoreferenced rasters are skipped.",
    )

    parser.add_argument(
        "-p",
        "--parallel",
        type=int,
        nargs="?",
        const=0,
        default=1,
        metavar="WORKERS",
        help="enable parallel file extraction within directories. "
        "Without a number, uses all available CPU cores. "
        "Specify a number (e.g., -p 4) to set worker count. "
        "Default: sequential processing.",
    )

    parser.add_argument(
        "--join",
        action="store_true",
        default=False,
        help="Join multiple exported files (from --output) into a single file. "
        "Requires --output to specify the destination.",
    )

    parser.add_argument(
        "files",
        action=readable_file_or_dir,
        nargs="*",
        help="input file, directory, DOI, or repository URL (supports multiple "
        "inputs including mixed types). Use '-' to read text from stdin "
        "(requires --text-method). May be empty when --text STRING is used.",
    )

    return parser


def print_help():
    print(help_description)
    arg_parser.print_help()
    print(help_epilog)
    print_supported_formats()


def print_supported_formats():
    """Print supported formats (generated dynamically from features API)."""
    print(get_supported_formats_text())


def print_version():
    print(__version__)


def print_features_json():
    """Print machine-readable JSON with supported features."""
    from .lib.features import get_supported_features_json

    print(get_supported_features_json())


def print_periods(fmt: str = "json", name_filter: str = None):
    """Print the bundled named-time-period gazetteer for downstream tools.

    ``fmt="json"`` emits the same metadata + periods list returned by
    :func:`geoextent.lib.period_gazetteer.list_periods`; ``fmt="text"``
    prints a human-friendly tab-separated table prefixed by a short
    attribution comment.
    """
    from .lib.period_gazetteer import list_periods

    data = list_periods(name_filter=name_filter)
    if fmt == "json":
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    # Plain-text table.
    print(f"# {data.get('name')}")
    print(f"# Source: {data.get('source')} ({data.get('source_url')})")
    print(f"# Revision: {data.get('source_revision')!s}")
    print(f"# Built at: {data.get('built_at')}")
    print(f"# License: {data.get('license')} — {data.get('license_url')}")
    print(f"# Periods: {data.get('period_count')}")
    print("#")
    print("# name\trank\tstart\tend\tid")
    for rec in data.get("periods", []):
        print(
            "\t".join(
                str(rec.get(k, "")) for k in ("name", "rank", "start", "end", "id")
            )
        )


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


def _collect_annotate_payload(output):
    """Pull source_text + standoff spans from a pre-conversion result dict.

    Looks at the top-level keys first (single text input), then walks
    ``details`` (multi-input runs) and returns a list of payloads so the
    CLI can emit one annotated block per source.
    """
    if not isinstance(output, dict):
        return None
    payloads = []
    if "source_text" in output:
        payloads.append(
            {
                "label": None,
                "source_text": output.get("source_text"),
                "place_names": output.get("place_names") or [],
                "date_entities": output.get("date_entities") or [],
            }
        )
    details = output.get("details") or {}
    if isinstance(details, dict):
        for label, entry in details.items():
            if isinstance(entry, dict) and entry.get("source_text"):
                payloads.append(
                    {
                        "label": label,
                        "source_text": entry.get("source_text"),
                        "place_names": entry.get("place_names") or [],
                        "date_entities": entry.get("date_entities") or [],
                    }
                )
    return payloads or None


def _parse_map_dimensions(dim_str):
    """Parse 'WxH' string to (width, height) tuple."""
    try:
        w, h = dim_str.lower().split("x")
        return (int(w), int(h))
    except (ValueError, AttributeError):
        raise argparse.ArgumentTypeError(
            f"Invalid map dimensions '{dim_str}'. Expected format: WxH (e.g., 800x600)"
        )


def _call_from_remote_with_size_prompt(kwargs):
    """Call ``extent.from_remote()`` with interactive size-limit prompting.

    If the provider raises :class:`DownloadSizeExceeded` and stdin is a TTY,
    the user is prompted to confirm the large download.  In non-interactive
    mode the exception propagates.
    """
    try:
        return extent.from_remote(**kwargs)
    except DownloadSizeExceeded as exc:
        if not sys.stdin.isatty():
            raise

        mb = exc.estimated_size / (1024 * 1024)
        print(
            f"\n{exc.provider}: the download is approximately {mb:,.1f} MB "
            f"(limit is {exc.max_size / (1024 * 1024):,.0f} MB).",
            file=sys.stderr,
        )
        answer = input("Proceed with download? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            logger.info("Download cancelled by user")
            return None

        # Retry with an increased limit (format as bytes string for filesizelib)
        kwargs["max_download_size"] = f"{exc.estimated_size + 1}B"
        return extent.from_remote(**kwargs)


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
    if "--list-periods" in sys.argv:
        # Parse early to honour --list-periods-format / --list-periods-filter
        # without forcing the rest of the argparse contract (which requires
        # positional inputs or --text).
        fmt = "json"
        name_filter = None
        argv = sys.argv[1:]
        for i, tok in enumerate(argv):
            if tok == "--list-periods-format" and i + 1 < len(argv):
                fmt = argv[i + 1]
            elif tok.startswith("--list-periods-format="):
                fmt = tok.split("=", 1)[1]
            elif tok == "--list-periods-filter" and i + 1 < len(argv):
                name_filter = argv[i + 1]
            elif tok.startswith("--list-periods-filter="):
                name_filter = tok.split("=", 1)[1]
        print_periods(fmt=fmt, name_filter=name_filter)
        arg_parser.exit()

    args = vars(arg_parser.parse_args())
    files = args["files"] or []

    # Parse additional file extensions for geospatial detection
    additional_extensions = _parse_additional_extensions(
        args["download_skip_nogeo_exts"]
    )

    # Resolve workers: 0 means auto-detect, pass through to API functions
    workers = args["parallel"]

    # Validate text/NER inputs (issue #112). ``--text-method`` defaults to
    # ``"ner"``; ``"none"`` (or missing spaCy) disables the text handler.
    text_method = args.get("text_method")
    if text_method in (None, "none"):
        text_method = None
    inline_text = args.get("text")
    has_stdin_sentinel = "-" in files

    if (inline_text or has_stdin_sentinel) and text_method is None:
        arg_parser.error(
            "--text and stdin (-) require --text-method ner "
            "(currently disabled via --text-method none)"
        )

    # Resolve --ner-gazetteer default: fall back to --placename-service if set,
    # then to nominatim (no API key required, works out of the box).
    ner_gazetteer = args.get("ner_gazetteer")
    if text_method and not ner_gazetteer:
        ner_gazetteer = args.get("placename_service") or "nominatim"

    # Parse --ner-labels CSV
    ner_labels = None
    if args.get("ner_labels"):
        ner_labels = [s.strip() for s in args["ner_labels"].split(",") if s.strip()]

    # Bundle NER kwargs for the API calls below; pass an empty dict when
    # text extraction is disabled so the existing call sites remain clean.
    ner_kwargs = {}
    if text_method:
        ner_kwargs = {
            "text_method": text_method,
            "ner_model": args.get("ner_model"),
            "ner_labels": ner_labels,
            "ner_score_threshold": args.get("ner_score_threshold"),
            "ner_gazetteer": ner_gazetteer,
            "ner_ambiguity": args.get("ner_ambiguity") or "drop",
            "ner_auto_download": args.get("ner_auto_download", True),
            "period_gazetteer": args.get("period_gazetteer") or "bundled",
            "period_ambiguity": args.get("period_ambiguity") or "drop",
            "period_resolution": args.get("period_resolution", True),
            "include_source_text": args.get("include_source_text", True),
            "place_geometry": args.get("place_geometry") or "auto",
        }

    if files is None or (len(files) == 0 and not (inline_text or has_stdin_sentinel)):
        raise Exception("Invalid command, input file missing")

    # Validate placename options
    if args["placename_escape"] and not args["placename"]:
        raise ValueError("--placename-escape requires --placename to be specified")

    if args["placename_service"] and not args["placename"]:
        raise ValueError("--placename-service requires --placename to be specified")

    # Determine gazetteer service to use. Default to nominatim because it
    # works without an API key. geonames is still available via
    # --placename-service geonames but requires GEONAMES_USERNAME.
    placename_service = None
    if args["placename"]:
        placename_service = args["placename_service"] or "nominatim"

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

    # Validate mutually exclusive options
    if args["metadata_first"] and not args["download_data"]:
        arg_parser.error(
            "--metadata-first and --no-download-data are mutually exclusive"
        )

    # Validate time format early
    if args["time_format"] is not None:
        try:
            hf.resolve_time_format(args["time_format"])
        except ValueError as e:
            arg_parser.error(str(e))

    # Handle --join early — bypasses extraction pipeline entirely
    if args["join"]:
        if not args["output"]:
            arg_parser.error("--join requires --output to specify the destination file")
        from geoextent.lib.export import join_files

        csv_geom_fmt = "wkb" if args["format"].lower() == "wkb" else "wkt"
        join_files(files, args["output"], geometry_format=csv_geom_fmt)
        if not args.get("quiet"):
            logger.info("Joined %d file(s) into: %s", len(files), args["output"])
        sys.exit(0)

    # Validate that at least one extraction option is enabled
    if not args["bounding_box"] and not args["time_box"]:
        arg_parser.error(
            "one of extraction options must be selected (-b/--bounding-box or -t/--time-box)"
        )

    # Collect inline/stdin text inputs (issue #112). Each becomes a
    # separate source labelled "<text>" or "<stdin>" in the details.
    text_inputs = []  # list of (label, text_string)
    if inline_text is not None:
        text_inputs.append(("<text>", inline_text))
    if has_stdin_sentinel:
        stdin_text = sys.stdin if isinstance(sys.stdin, str) else sys.stdin.read()
        text_inputs.append(("<stdin>", stdin_text))
        # Remove '-' from positional file list before regular dispatch.
        files = [f for f in files if f != "-"]

    output = None
    multiple_files = (len(files) + len(text_inputs)) > 1

    try:
        # Single text-only input fast path (no positional files).
        if len(files) == 0 and len(text_inputs) == 1:
            _, text_str = text_inputs[0]
            output = extent.from_text(
                text_str,
                bbox=args["bounding_box"],
                tbox=args["time_box"],
                convex_hull=args["convex_hull"],
                legacy=args["legacy"],
                time_format=args["time_format"],
                **ner_kwargs,
            )
        elif (len(files) + len(text_inputs)) == 1 and len(files) == 1:
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

            if (is_file and not is_zipfile) or (
                is_directory and single_input.rstrip(os.sep).endswith(".zarr")
            ):
                output = extent.from_file(
                    single_input,
                    bbox=args["bounding_box"],
                    tbox=args["time_box"],
                    convex_hull=args["convex_hull"],
                    show_progress=not args["no_progress"],
                    placename=placename_service,
                    placename_escape=args["placename_escape"],
                    legacy=args["legacy"],
                    assume_wgs84=args["assume_wgs84"],
                    time_format=args["time_format"],
                    **ner_kwargs,
                )
            elif is_directory or is_zipfile:
                output = extent.from_directory(
                    single_input,
                    bbox=args["bounding_box"],
                    tbox=args["time_box"],
                    convex_hull=args["convex_hull"],
                    details=True,
                    show_progress=not args["no_progress"],
                    recursive=not args["no_subdirs"],
                    placename=placename_service,
                    placename_escape=args["placename_escape"],
                    legacy=args["legacy"],
                    assume_wgs84=args["assume_wgs84"],
                    time_format=args["time_format"],
                    workers=workers,
                    **ner_kwargs,
                )
            elif is_url or is_doi or is_repository:
                output = _call_from_remote_with_size_prompt(
                    {
                        "remote_identifier": single_input,
                        "bbox": args["bounding_box"],
                        "tbox": args["time_box"],
                        "convex_hull": args["convex_hull"],
                        "details": True,
                        "download_data": args["download_data"],
                        "show_progress": not args["no_progress"],
                        "recursive": not args["no_subdirs"],
                        "max_download_size": args["max_download_size"],
                        "max_download_method": args["max_download_method"],
                        "max_download_method_seed": args["max_download_method_seed"]
                        or hf.DEFAULT_DOWNLOAD_SAMPLE_SEED,
                        "placename": placename_service,
                        "placename_escape": args["placename_escape"],
                        "download_skip_nogeo": args["download_skip_nogeo"],
                        "download_skip_nogeo_exts": additional_extensions,
                        "max_download_workers": args["max_download_workers"],
                        "ext_metadata": args["ext_metadata"],
                        "ext_metadata_method": args["ext_metadata_method"],
                        "keep_files": args["keep_files"],
                        "legacy": args["legacy"],
                        "assume_wgs84": args["assume_wgs84"],
                        "metadata_first": args["metadata_first"],
                        "metadata_fallback": args["metadata_fallback"],
                        "time_format": args["time_format"],
                        "follow": args["follow"],
                        "download_size_soft_limit": True,
                        "workers": workers,
                    }
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
                        repo_output = _call_from_remote_with_size_prompt(
                            {
                                "remote_identifier": file_path,
                                "bbox": args["bounding_box"],
                                "tbox": args["time_box"],
                                "convex_hull": args["convex_hull"],
                                "details": True,
                                "download_data": args["download_data"],
                                "show_progress": not args["no_progress"],
                                "recursive": not args["no_subdirs"],
                                "max_download_size": args["max_download_size"],
                                "max_download_method": args["max_download_method"],
                                "max_download_method_seed": args[
                                    "max_download_method_seed"
                                ]
                                or hf.DEFAULT_DOWNLOAD_SAMPLE_SEED,
                                "placename": placename_service,
                                "placename_escape": args["placename_escape"],
                                "download_skip_nogeo": args["download_skip_nogeo"],
                                "download_skip_nogeo_exts": additional_extensions,
                                "max_download_workers": args["max_download_workers"],
                                "ext_metadata": args["ext_metadata"],
                                "ext_metadata_method": args["ext_metadata_method"],
                                "keep_files": args["keep_files"],
                                "legacy": args["legacy"],
                                "assume_wgs84": args["assume_wgs84"],
                                "metadata_first": args["metadata_first"],
                                "metadata_fallback": args["metadata_fallback"],
                                "time_format": args["time_format"],
                                "follow": args["follow"],
                                "download_size_soft_limit": True,
                                "workers": workers,
                            }
                        )
                        if repo_output is not None:
                            output["details"][file_path] = repo_output
                    elif os.path.isfile(file_path) and not zipfile.is_zipfile(
                        file_path
                    ):
                        # Process individual file
                        file_output = extent.from_file(
                            file_path,
                            bbox=args["bounding_box"],
                            tbox=args["time_box"],
                            convex_hull=args["convex_hull"],
                            show_progress=not args["no_progress"],
                            placename=placename_service,
                            placename_escape=args["placename_escape"],
                            legacy=args["legacy"],
                            assume_wgs84=args["assume_wgs84"],
                            time_format=args["time_format"],
                            **ner_kwargs,
                        )
                        if file_output is not None:
                            output["details"][file_path] = file_output
                    elif os.path.isdir(file_path) or zipfile.is_zipfile(file_path):
                        # Process directory or zip file
                        dir_output = extent.from_directory(
                            file_path,
                            bbox=args["bounding_box"],
                            tbox=args["time_box"],
                            convex_hull=args["convex_hull"],
                            details=True,
                            show_progress=not args["no_progress"],
                            recursive=not args["no_subdirs"],
                            placename=placename_service,
                            placename_escape=args["placename_escape"],
                            legacy=args["legacy"],
                            assume_wgs84=args["assume_wgs84"],
                            time_format=args["time_format"],
                            workers=workers,
                            **ner_kwargs,
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

            # Process inline/stdin text inputs (issue #112)
            for label, text_str in text_inputs:
                try:
                    text_output = extent.from_text(
                        text_str,
                        bbox=args["bounding_box"],
                        tbox=args["time_box"],
                        convex_hull=args["convex_hull"],
                        legacy=args["legacy"],
                        time_format=args["time_format"],
                        **ner_kwargs,
                    )
                    if text_output is not None:
                        output["details"][label] = text_output
                except Exception as text_error:
                    logger.warning("Error processing %s: %s", label, str(text_error))
                    continue

            # Merge spatial extents if bbox is requested. Multiple positional
            # inputs and ``--text`` / ``-`` stdin inputs are all treated as
            # peer sources and merged into a single envelope / convex hull.
            # Use ``--details`` to also inspect per-source results.
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
                tbox_merge = hf.tbox_merge(
                    output["details"], "multiple_files", time_format=args["time_format"]
                )
                if tbox_merge is not None:
                    output["tbox"] = tbox_merge

    except Exception as e:
        if logger.getEffectiveLevel() >= logging.DEBUG:
            logger.exception(e)
        sys.exit(1)

    if output is None:
        raise Exception("Did not find supported files at {}".format(files))
    else:

        if export:
            if not args.get("quiet"):
                logger.info("Exporting result into: %s", args["output"])
            # --format affects CSV geometry column
            csv_geom_fmt = "wkb" if args["format"].lower() == "wkb" else "wkt"
            # Warn if --format is set for fixed-format outputs
            out_ext = os.path.splitext(filename)[1].lower()
            if args["format"].lower() != "geojson" and out_ext in (
                ".gpkg",
                ".geojson",
                ".json",
            ):
                logger.warning(
                    "--format %s is ignored for %s output (geometry is stored natively)",
                    args["format"],
                    out_ext,
                )
            from geoextent.lib.export import export_results

            export_results(
                output,
                filename,
                inputs=files,
                version=__version__,
                geometry_format=csv_geom_fmt,
                native_order=not args["legacy"],
            )

        # Create extraction metadata before removing details (unless --no-metadata is set)
        extraction_metadata = None
        if not args["no_metadata"]:
            extraction_metadata = hf.create_extraction_metadata(
                files, __version__, output
            )

        if not args["details"]:
            output.pop("details", None)

        # Generate geojson.io URL if --geojsonio or --browse is requested (before format conversion)
        # Track failure reason separately so the CLI can emit a precise
        # message instead of the older lumped "no extent OR not available".
        geojsonio_url = None
        geojsonio_failure_reason = None
        native_order = not args["legacy"]
        if args["geojsonio"] or args["browse"]:
            if not output:
                geojsonio_failure_reason = "extraction returned no output"
            elif "bbox" not in output:
                geojsonio_failure_reason = (
                    "no spatial extent in output (re-run with -b to extract a bbox)"
                )
            else:
                try:
                    geojsonio_url = hf.generate_geojsonio_url(
                        output,
                        native_order=native_order,
                        inputs=files,
                        raise_on_error=True,
                    )
                except hf.GeojsonioUrlError as e:
                    # geojsonio.make_url failed (commonly 401 from the
                    # anonymous-gist fallback used for GeoJSON > ~27 KB).
                    geojsonio_failure_reason = f"geojson.io service call failed: {e}"

        # Generate map preview if --map or --preview was requested (before format conversion)
        # args["map"] is None (not given), True (--map without path), or a string (--map PATH)
        quiet = args.get("quiet")
        map_requested = args.get("map") is not None
        map_path_explicit = isinstance(args.get("map"), str)
        # --quiet suppresses --preview display entirely; --map with an explicit
        # path still saves the file silently, but --map without a path (temp
        # file) is skipped since the user won't see the path.
        preview_wanted = args.get("preview") and not quiet
        map_wanted = map_path_explicit or (map_requested and not quiet)
        if (map_wanted or preview_wanted) and output and "bbox" in output:
            try:
                from geoextent.lib.preview import (
                    save_map,
                    display_in_terminal,
                    format_map_saved_message,
                )

                dim = _parse_map_dimensions(args["map_dim"])
                map_path = args["map"] if map_path_explicit else None
                saved_path = save_map(output, map_path, dim, native_order=native_order)
                if not quiet:
                    print(
                        format_map_saved_message(saved_path, stream=sys.stderr),
                        file=sys.stderr,
                    )
                if preview_wanted:
                    display_in_terminal(saved_path)
            except ImportError as e:
                if not quiet:
                    print(f"Map preview unavailable: {e}", file=sys.stderr)
            except argparse.ArgumentTypeError as e:
                if not quiet:
                    print(str(e), file=sys.stderr)
            except Exception as e:
                logger.warning("Failed to generate map preview: %s", e)
            else:
                if not quiet:
                    print(file=sys.stderr)

        # Snapshot the pre-conversion data needed for --annotate so the
        # GeoJSON/WKT/WKB transformation does not strip the standoff fields.
        # --quiet suppresses the auto default but honours explicit modes:
        # users who pass --annotate brackets/ansi/html under --quiet still get
        # the rendering they asked for.
        _annotate_payload = None
        _annotate_mode_arg = args.get("annotate") or "off"
        if args.get("quiet") and _annotate_mode_arg == "auto":
            _annotate_mode_arg = "off"
        if _annotate_mode_arg != "off" and text_method:
            _annotate_payload = _collect_annotate_payload(output)

        # Apply output format conversion
        output = hf.format_extent_output(
            output, args["format"], extraction_metadata, native_order=native_order
        )

    # For WKT and WKB formats, output only the bbox value
    if args["format"].lower() in ["wkt", "wkb"] and output and "bbox" in output:
        print(output["bbox"])
    elif type(output) == list or type(output) == dict:
        print(json.dumps(output, ensure_ascii=False))
    else:
        print(output)

    # Annotated source rendering (issue #112).
    if _annotate_payload:
        from geoextent.lib.annotate import (
            parse_classes,
            render_annotated_text,
            resolve_mode,
        )

        mode = resolve_mode(_annotate_mode_arg)
        classes = parse_classes(args.get("annotate_classes"))
        for payload in _annotate_payload:
            rendered = render_annotated_text(payload, mode=mode, classes=classes)
            if rendered is None:
                continue
            header = f"---annotated source ({mode})"
            if payload["label"]:
                header += f" — {payload['label']}"
            header += "---"
            print(header)
            print(rendered)

    # Print geojson.io URL if --geojsonio was requested
    if args["geojsonio"]:
        if geojsonio_url:
            print(f"\n🌍 View spatial extent at: {geojsonio_url}")
        elif not args["quiet"]:
            reason = geojsonio_failure_reason or "unknown error"
            print(f"\ngeojson.io URL could not be generated — {reason}")

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
            reason = geojsonio_failure_reason or "unknown error"
            print(f"\ngeojson.io URL could not be generated — {reason}")


if __name__ == "__main__":
    main()
