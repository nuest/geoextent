# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

geoextent is a Python library for extracting geospatial extent (bounding boxes and temporal extents) from files and directories containing geospatial data. It supports multiple formats including GeoJSON, CSV, Shapefile, and GeoTIFF files.

## Development Commands

### Installation and Setup

```bash
# Install pygdal first (required dependency)
pip install pygdal=="`gdal-config --version`.*"

# Install in development mode
pip install -e .
```

### Testing

```bash
# Run tests using pytest
pytest

# Run specific test files
pytest tests/test_api.py
pytest tests/test_cli.py
```

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
   - Support for extracting data from repositories (Zenodo, Figshare, Dryad)

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