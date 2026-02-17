# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

geoextent is a Python library for extracting geospatial extent (bounding boxes and temporal extents) from files and directories containing geospatial data. It supports multiple formats including GeoJSON, CSV, Shapefile, and GeoTIFF files.

**Repository:** The main development repository is [nuest/geoextent](https://github.com/nuest/geoextent) (`origin` remote). The [o2r-project/geoextent](https://github.com/o2r-project/geoextent) fork is the deprecated project repository. Current issues are tracked at `nuest/geoextent`, undless specific issued are referenced from the earlier version.

## API Stability

This project is currently in version 0.x, which means:

- **Breaking changes are allowed** between minor versions
- **API is under active development** and improvement
- **Semantic versioning** will be followed starting from version 1.0

### Current API Functions

1. **fromFile()** - Extract extent from individual files
2. **fromDirectory()** - Extract extent from directories
3. **fromRemote()** - Extract extent from remote sources (repositories, journals, preprint servers)

### Function Naming Convention

All main API functions use **camelCase** for consistency:
- `fromFile` (not `from_file`)
- `fromDirectory` (not `from_directory`)
- `fromRemote` (not `from_remote`)

### Recent Breaking Changes

- **v0.8.0**: Removed deprecated `from_repository()` function
- **v0.8.0**: Renamed parameter `repository_identifier` to `remote_identifier`
- **v0.8.0**: Changed format metadata from `"repository"` to `"remote"`
- **v0.8.0**: Standardized internal data structures to use GeoJSON format

### Coordinate Format Standards

geoextent uses two coordinate order modes:

1. **Default (Native EPSG:4326)**: Coordinates follow EPSG:4326 native axis order: **(latitude, longitude)**
   - Bounding Box: `[minlat, minlon, maxlat, maxlon]`
   - Coordinate pairs: `[lat, lon]`
   - GeoJSON geometries: `{"type": "Point", "coordinates": [lat, lon]}`
   - WKT/WKB: Coordinates encoded in `[lat, lon]` order

2. **Legacy Mode** (`--legacy` CLI flag or `legacy=True` API parameter): Traditional GIS order **(longitude, latitude)**
   - Bounding Box: `[minlon, minlat, maxlon, maxlat]`
   - Coordinate pairs: `[lon, lat]`
   - Matches the old geoextent behavior and GeoJSON standard `[lon, lat]` order

3. **CRS**: Default to WGS84 (EPSG:4326) unless otherwise specified

4. **WKB output**: Uses **little-endian** (NDR, byte-order flag `01`) via `ogr.wkbNDR`, matching GDAL/PostGIS/Shapely defaults

### Internal vs Output Coordinate Order

- **Internally**, all processing uses traditional GIS order `[longitude, latitude]` (i.e. `[x, y]`)
- The coordinate swap to native EPSG:4326 `[latitude, longitude]` happens **only at the output boundary** of public API functions (`fromFile`, `fromDirectory`, `fromRemote`)
- OGR's `GetExtent()` returns `(minX, maxX, minY, maxY)` in traditional order; do **not** swap axes internally
- The `_swap_coordinate_order()` function in `extent.py` handles the output swap
- Internal calls between functions use `_internal=True` to prevent double-swapping

### Internal Function Contracts

- `bbox_merge()`: Expects `[minx, miny, maxx, maxy]` format (internal lon/lat order)
- `convex_hull_merge()`: Can handle both bbox format and coordinate arrays (internal lon/lat order)
- All coordinate transformations use `[longitude, latitude]` order internally
- Handler modules should return standardized bbox format in `[minlon, minlat, maxlon, maxlat]` order
- `bbox_to_wkb()` / `convex_hull_coords_to_wkb()`: Always use `ogr.wkbNDR` (little-endian)

## Development Commands

**IMPORTANT: Always use the project's `.venv` virtual environment.** The system Python may have mismatched GDAL bindings. The `.venv` has GDAL Python bindings that match the system GDAL library (both 3.11.4), which is critical for correct behavior. Run all commands via `.venv/bin/python` or activate the venv first:

```bash
# Activate the virtual environment (do this first!)
source .venv/bin/activate

# Or prefix commands explicitly
.venv/bin/python -m pytest ...
```

### Installation and Setup

```bash
# Install in development mode (inside .venv)
pip install -e .
```

### Testing

```bash
# Run fast tests only (default — excludes slow network tests and large downloads)
pytest

# Run provider smoke tests (one real-network test per provider, ~11 tests)
pytest -m provider_sample

# Run all tests except large downloads
pytest -m "not large_download"

# Run only slow network tests
pytest -m slow

# Run large download tests explicitly
pytest -m large_download

# Run ALL tests including large downloads
pytest -m ""

# Run tests with explicit parallelism control
pytest -n auto          # Auto-detect number of CPUs (default)
pytest -n 4             # Use 4 workers
pytest -n 1             # Disable parallelism

# Run specific test files (parallel execution still applies)
pytest tests/test_api.py
pytest tests/test_cli.py

# Run specific test with parallelism disabled (useful for debugging)
pytest -n 0 tests/test_api.py::test_specific_function
```

**Note:** Parallel test execution is enabled by default using `pytest-xdist` with automatic CPU detection. This significantly speeds up the test suite.

**Test markers:**
- **`slow`** — Network-dependent provider tests (auto-applied via `conftest.py`). Excluded by default.
- **`provider_sample`** — One representative real-network test per provider (~11 tests). A subset of `slow`.
- **`large_download`** — Tests that download >100MB of data. Excluded by default.

### Code Formatting

```bash
# Format code with black
black geoextent/ tests/

# Check formatting without making changes
black --check geoextent/ tests/

# Set up pre-commit hooks (run once)
pre-commit install

# Run pre-commit hooks manually
pre-commit run --all-files
```

### Running the CLI

```bash
# Run as module
python -m geoextent --help

# Check version
python -m geoextent --version
```

### Local GitHub Actions Testing with act

The project includes configuration for testing GitHub Actions workflows locally using [act](https://github.com/nektos/act).

#### Installation

Install act on your system:

```bash
# macOS
brew install act

# Linux
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Windows
choco install act-cli
```

#### Configuration Files

- `.actrc` - act configuration with Ubuntu 24.04 image and verbose logging

#### Running Tests Locally

Use the provided script for easy local testing:

```bash
# Run main Python package tests (default)
./scripts/test-local-ci.sh

# Run with specific Python version
./scripts/test-local-ci.sh --python-version 3.11

# List all available jobs
./scripts/test-local-ci.sh --list-jobs

# Show what would be executed (dry run)
./scripts/test-local-ci.sh --dry-run

# Run all workflows
./scripts/test-local-ci.sh --workflow all
```

#### Available Workflows

1. **pythonpackage** - Main test suite: fast tests, provider samples, and test collection verification
2. **documentation** - Documentation build and deployment
3. **codeql** - Security analysis

#### Direct act Commands

```bash
# Run main test workflow
act -W .github/workflows/pythonpackage.yml

# Run with specific Python version
act -W .github/workflows/pythonpackage.yml --matrix python-version:3.11

# List all jobs in a workflow
act -W .github/workflows/pythonpackage.yml --list
```

## Architecture Overview

The project follows a modular handler-based architecture:

### Core Components

1. **Main Entry Points**:
   - `geoextent/__main__.py` - CLI entry point
   - `geoextent/lib/extent.py` - Core extraction functions (`fromFile`, `fromDirectory`, `from_repository`)

2. **Format Handlers** (in `geoextent/lib/`):
   - `handleCSV.py` - CSV file processing with coordinate detection
   - `handleRaster.py` - Raster data (GeoTIFF, world files) processing using GDAL. Temporal extraction supports: NetCDF CF time dimensions, ACDD `time_coverage_start/end`, GeoTIFF `TIFFTAG_DATETIME`, and band-level `ACQUISITIONDATETIME` (IMAGERY domain)
   - `handleVector.py` - Vector data (Shapefile, GeoJSON) processing using OGR
   - `helpfunctions.py` - Utility functions for CRS transformations and validation

3. **Content Providers** (in `geoextent/lib/content_providers/`):
   - Support for extracting data from repositories (Zenodo, InvenioRDM instances, Figshare, 4TU.ResearchData (uses Djehuty platform with Figshare-compatible API, not Figshare itself), Dryad, PANGAEA, OSF, Dataverse, GFZ, Pensoft, Opara, Senckenberg, BGR, BAW, MDI-DE, Mendeley Data, Wikidata, RADAR, Arctic Data Center, DEIMS-SDR (follows external DOIs/URLs to supported providers by default; disable with ``--no-follow``))
   - ``InvenioRDM`` base provider supporting CaltechDATA, TU Wien, Frei-Data, GEO Knowledge Hub, TU Graz, Materials Cloud Archive, FDAT, DataPLANT ARChive, KTH, Prism, NYU Ultraviolet, B2SHARE (EUDAT)
   - Includes abstract ``CKANProvider`` base class for CKAN-based repositories (used by Senckenberg)
   - BGR, BAW, and MDI-DE all use CSW 2.0.2 with ISO 19115/19139 metadata via OWSLib; MDI-DE additionally supports WFS-based data download

### Handler Selection

The system automatically selects appropriate handlers based on file format:
- Files are tested against each handler module's `checkFileSupported()` function
- Each handler provides format-specific `getBoundingBox()` and `getTemporalExtent()` methods
- All spatial extents are transformed to WGS84 (EPSG:4326) for consistency

### World File Support

World files provide geospatial transformation information for raster images without embedded georeferencing:

**Supported Extensions:**
- `.wld` (generic), `.jgw` (JPEG), `.pgw`/`.pngw` (PNG), `.tfw`/`.tifw` (TIFF), `.bpw` (BMP), `.gfw` (GIF)

**Implementation Details:**
- GDAL automatically detects world files when named correctly (e.g., `image.png` + `image.pngw`)
- `handleRaster.py` handles cases where projection reference is empty (world files without .prj)
- When no CRS is specified, assumes WGS84 (EPSG:4326)
- Test data available in `tests/testdata/worldfile/`

**Testing:**
- Test file: `test_api_worldfile.py`
- Example records: Zenodo 820562 (PNG+.pngw), Zenodo 7196949 (TIFF+.tfw)

### Key Functions

- `fromFile()` - Extract extent from single file using threading for bbox/tbox extraction
- `fromDirectory()` - Recursively process directories and archives with timeout support
- `from_repository()` - Download and process data from research repositories
- `compute_bbox_wgs84()` - Transform bounding boxes to WGS84 coordinate system

### Dependencies

Key external dependencies:

- GDAL/OGR for geospatial data processing
- pandas for CSV handling
- pyproj for coordinate transformations
- patool for archive extraction
- requests for repository data downloading
- pangaeapy for PANGAEA data access
- crossref-commons for DOI metadata retrieval
- osfclient for OSF data access

**All packages listed in `setup.cfg` / `pyproject.toml` `install_requires` are required dependencies.** Do not wrap their imports in `try/except ImportError` — if they are missing, the installation is broken and should fail loudly. Only use `try/except ImportError` for genuinely optional dependencies that enable extra functionality (none exist currently).

### Adding New Content Providers or File Formats

When adding a new content provider or file format handler, it must be registered in **all** of the following places:

1. **`geoextent/lib/content_providers/__init__.py`** — import the module and add to `__all__`
2. **`geoextent/lib/extent.py`** — add to `_get_content_providers()` list (ordering matters for provider priority)
3. **Provider class** — add `provider_info()` classmethod (features.py reads it automatically)
4. **`tests/conftest.py`** — add the test file to `_PROVIDER_FILES` and a sample test to `_PROVIDER_SAMPLE_TESTS`
5. **`docs/source/changelog.rst`** — add changelog entry under "Unreleased"
6. **`CLAUDE.md`** — update the content providers list in the Architecture Overview section

### Test Exception Handling

- **Never use broad `except Exception: pytest.skip(...)`** in tests — this silently hides real bugs.
- Use `except NETWORK_SKIP_EXCEPTIONS` (defined in `conftest.py`) for network-dependent tests that should be skipped on transient network failures: `(requests.RequestException, ConnectionError, TimeoutError, OSError)`.
- Only catch exceptions that are expected and specific. If a test fails due to a code bug, it should fail loudly, not be silently skipped.
- Periodically audit tests for overly broad exception catches that may mask regressions.

## File Structure

```
geoextent/
├── __main__.py              # CLI entry point
├── lib/
│   ├── extent.py           # Core extraction logic
│   ├── handleCSV.py        # CSV format handler
│   ├── handleRaster.py     # Raster format handler
│   ├── handleVector.py     # Vector format handler
│   ├── helpfunctions.py    # Utility functions
│   └── content_providers/  # Repository integrations
tests/                      # Test files organized by format
```

## Testing Data

Test data is located in `tests/testdata/` with sample files for each supported format.

## Background Agent Research Reports

Background agent research results are saved in the `.claude/` directory (project-level). When running background research agents, save output reports to `.claude/research_<topic>.md`.
