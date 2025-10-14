# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

geoextent is a Python library for extracting geospatial extent (bounding boxes and temporal extents) from files and directories containing geospatial data. It supports multiple formats including GeoJSON, CSV, Shapefile, and GeoTIFF files.

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

All spatial data in geoextent follows these conventions:

1. **Coordinate Order**: Always `[longitude, latitude]` (GeoJSON standard)
   - NOT `[latitude, longitude]`
   - X-coordinate (longitude) comes first, Y-coordinate (latitude) second

2. **Bounding Box Format**: `[minx, miny, maxx, maxy]`
   - `minx` = westernmost longitude
   - `miny` = southernmost latitude
   - `maxx` = easternmost longitude
   - `maxy` = northernmost latitude

3. **GeoJSON Geometries**: Standard GeoJSON format
   - Points: `{"type": "Point", "coordinates": [lon, lat]}`
   - Polygons: `{"type": "Polygon", "coordinates": [[[lon1, lat1], [lon2, lat2], ...]]}`

4. **CRS**: Default to WGS84 (EPSG:4326) unless otherwise specified

### Internal Function Contracts

- `bbox_merge()`: Expects `[minx, miny, maxx, maxy]` format from each file
- `convex_hull_merge()`: Can handle both bbox format and coordinate arrays
- All coordinate transformations use `[longitude, latitude]` order
- Handler modules should return standardized bbox format

## Development Commands

### Installation and Setup

```bash
# Install in development mode
pip install -e .
```

### Testing

```bash
# Run tests using pytest (automatically uses parallel execution with -n auto)
pytest

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

# Run specific workflow
./scripts/test-local-ci.sh --workflow comprehensive-tests

# Run specific test category
./scripts/test-local-ci.sh --workflow comprehensive-tests --test-category api-core

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

1. **pythonpackage** - Main test suite with code formatting and comprehensive tests
2. **comprehensive-tests** - Category-based testing (api-core, api-repositories, api-formats, cli, integration)
3. **documentation** - Documentation build and deployment
4. **codeql** - Security analysis

#### Test Categories

- `api-core` - Core API functionality tests
- `api-repositories` - Remote repository provider tests (Zenodo, Figshare, Dryad, PANGAEA, OSF, GFZ, Pensoft, Dataverse, Opara, Senckenberg)
- `api-formats` - Format handler tests (CSV, GeoJSON, GeoTIFF, Shapefile, FlatGeobuf)
- `cli` - Command-line interface tests
- `integration` - Integration and special feature tests

#### Direct act Commands

```bash
# Run main test workflow
act -W .github/workflows/pythonpackage.yml

# Run comprehensive tests for api-core category
act -W .github/workflows/comprehensive-tests.yml --matrix test-category:api-core

# Run with specific Python version
act -W .github/workflows/pythonpackage.yml --matrix python-version:3.11

# List all jobs in a workflow
act -W .github/workflows/comprehensive-tests.yml --list
```

## Architecture Overview

The project follows a modular handler-based architecture:

### Core Components

1. **Main Entry Points**:
   - `geoextent/__main__.py` - CLI entry point
   - `geoextent/lib/extent.py` - Core extraction functions (`fromFile`, `fromDirectory`, `from_repository`)

2. **Format Handlers** (in `geoextent/lib/`):
   - `handleCSV.py` - CSV file processing with coordinate detection
   - `handleRaster.py` - Raster data (GeoTIFF) processing using GDAL
   - `handleVector.py` - Vector data (Shapefile, GeoJSON) processing using OGR
   - `helpfunctions.py` - Utility functions for CRS transformations and validation

3. **Content Providers** (in `geoextent/lib/content_providers/`):
   - Support for extracting data from repositories (Zenodo, Figshare, Dryad, PANGAEA, OSF, Dataverse, GFZ, Pensoft, Opara, Senckenberg)
   - Includes abstract ``CKANProvider`` base class for CKAN-based repositories (used by Senckenberg)

### Handler Selection

The system automatically selects appropriate handlers based on file format:
- Files are tested against each handler module's `checkFileSupported()` function
- Each handler provides format-specific `getBoundingBox()` and `getTemporalExtent()` methods
- All spatial extents are transformed to WGS84 (EPSG:4326) for consistency

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
