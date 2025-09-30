# geoextent

![Python package](https://github.com/nuest/geoextent/workflows/Python%20package/badge.svg?branch=main) [![PyPI version](https://badge.fury.io/py/geoextent.svg)](https://pypi.org/project/geoextent/0.1.0/)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/nuest/main) [![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.3925694.svg)](https://doi.org/10.5281/zenodo.3925694) [![SWH](https://archive.softwareheritage.org/badge/origin/https://github.com/nuest/geoextent.git/)](https://archive.softwareheritage.org/browse/origin/?origin_url=https://github.com/nuest/geoextent.git) [![SWH](https://archive.softwareheritage.org/badge/swh:1:dir:ff1e19d884833b2bc2c1ef7d9265ba45b5314332/)](https://archive.softwareheritage.org/swh:1:dir:ff1e19d884833b2bc2c1ef7d9265ba45b5314332;origin=https://github.com/nuest/geoextent.git;visit=swh:1:snp:609428a8b466b7877f2ca39921d69a5f6a11df9f;anchor=swh:1:rev:6aca93956d5cd6742318fd3ab27bb176b5f8c24b;path=//)

Python library for extracting geospatial extent of files and directories with multiple data formats.
[Read a notebook-based article about the library published at EarthCube 2021](https://earthcube2021.github.io/ec21_book/notebooks/ec21_garzon_etal/showcase/SG_01_Exploring_Research_Data_Repositories_with_geoextent.html).

This project was originally developed as part of the [DFG-funded](https://o2r.info/about/#funding) research project Opening Reproducible Research (o2r, [https://o2r.info](https://o2r.info)).

## API Stability

**Version 0.x (Current)**: Breaking changes may occur between minor versions. The API is under active development and improvement.

**Version 1.0+**: Will follow semantic versioning with stable API guarantees.

### Current API Functions

- `fromFile()` - Extract extent from individual files
- `fromDirectory()` - Extract extent from directories
- `fromRemote()` - Extract extent from remote sources (repositories, journals, preprint servers)

### Recent Breaking Changes

- **v0.8.0**: Renamed `from_repository()` to `fromRemote()` for consistency
- **v0.8.0**: Changed format metadata from `"repository"` to `"remote"`
- **v0.8.0**: Standardized all functions to use camelCase naming

## Installation

### System requirements

Python: `3.x`

GDAL: `3.11.x`

The package relies on common system libraries for reading geospatial datasets, such as GDAL and NetCDF.
On Debian systems, the [UbuntuGIS](https://wiki.ubuntu.com/UbuntuGIS) project offers easy installation of up to date versions of those libraries.
A one-line installer for GDAL is described at <>.

See the list in `travis.yml` for a full list of dependencies on Linux.

### Install from PyPI

```bash
python -m venv .env
source .env/bin/activate

pip install geoextent
```

### Source installation

```bash
git clone https://github.com/nuest/geoextent
cd geoextent

python -m venv .env
source .env/bin/activate

# installs deps from pyproject.toml
pip install -e .

# install dev, test, and docs dependencies
pip install -e ".[dev,test,docs]"

```

## Use

Run

```bash
python -m geoextent --help
```

to see all available options including repository extraction settings.

### Basic Usage Examples

```bash
# Extract bounding box from a single file
python -m geoextent -b tests/testdata/geojson/muenster_ring_zeit.geojson

# Extract convex hull instead of bounding box (vector files only)
python -m geoextent -b --convex-hull tests/testdata/geojson/ausgleichsflaechen_moers.geojson

# Extract temporal extent from a single file
python -m geoextent -t tests/testdata/csv/cities_NL_case5.csv

# Extract both spatial and temporal extents
python -m geoextent -b -t tests/testdata/shapefile/Abgrabungen_Kreis_Kleve_Shape.shp

# Extract convex hull with temporal extent
python -m geoextent -b -t --convex-hull tests/testdata/geojson/muenster_ring_zeit.geojson

# Process a directory of files
python -m geoextent -b -t tests/testdata/geojson/

# Process a directory with convex hull calculation
python -m geoextent -b --convex-hull tests/testdata/geojson/

# Process multiple specific files
python -m geoextent -b -t tests/testdata/shapefile/Abgrabungen_Kreis_Kleve_Shape.shp tests/testdata/csv/cities_NL_case5.csv tests/testdata/geopackage/nc.gpkg

# Process multiple files with convex hull merging
python -m geoextent -b --convex-hull tests/testdata/geojson/ausgleichsflaechen_moers.geojson tests/testdata/geopackage/nc.gpkg

# Process multiple files with wildcard (shell expansion)
python -m geoextent -t tests/testdata/geojson/*.geojson

# Show detailed results for each file
python -m geoextent -b -t --details tests/testdata/geojson/ausgleichsflaechen_moers.geojson tests/testdata/geojson/muenster_ring_zeit.geojson

# Extract from research repositories (DOI, URL, or identifier)
python -m geoextent -b -t https://zenodo.org/records/4593540
python -m geoextent -b -t 10.5281/zenodo.4593540
python -m geoextent -b -t https://doi.org/10.1594/PANGAEA.734969
python -m geoextent -b -t https://osf.io/4xe6z
python -m geoextent -b -t 10.17605/OSF.IO/4XE6Z
python -m geoextent -b -t https://doi.org/10.17605/OSF.IO/J2STA
python -m geoextent -b -t http://dx.doi.org/10.17605/OSF.IO/A5F3E
python -m geoextent -b -t OSF.IO/9JG2U
python -m geoextent -b -t https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=escidoc:5148893
python -m geoextent -b -t 1G 10.5880/GFZ.2.1.2020.001
python -m geoextent -b -t 10.5880/GFZ.4.8.2023.004
python -m geoextent -b -t 10.3897/BDJ.2.e1068
python -m geoextent -b -t https://doi.org/10.3897/BDJ.13.e159973

# Use metadata-only extraction for repositories (only partially supported)
python -m geoextent -b -t --no-download-data 10.1594/PANGAEA.734969

# Generate geojson.io URL for visualizing spatial extents
python -m geoextent -b --geojsonio tests/testdata/geojson/muenster_ring.geojson

# Generate geojson.io URL with convex hull
python -m geoextent -b --convex-hull --geojsonio tests/testdata/geojson/ausgleichsflaechen_moers.geojson

# Generate geojson.io URL with different output formats (URL always shows GeoJSON)
python -m geoextent -b --format wkt --geojsonio tests/testdata/shapefile/Abgrabungen_Kreis_Kleve_Shape.shp

# Combine multiple remote records
python -m geoextent -b -t --convex-hull --geojsonio 10.5281/zenodo.4593540 https://osf.io/4xe6z
```

### Download Size Limiting for Repositories

When extracting data from large research repositories, you can limit the total download size to control processing time and storage usage. This is particularly useful for exploring datasets or when working with limited bandwidth/storage.

#### Basic Size Limiting

```bash
# Limit total download across all files, will download as many files as fit within this limit
python -m geoextent -b --max-download-size 100MB https://doi.org/10.5281/zenodo.7080016
python -m geoextent -b --max-download-size 1G 10.5880/GFZ.2.1.2020.001

# Limit total download to 1000KB - download is not started
python -m geoextent -b --max-download-size 1000KB https://doi.org/10.5281/zenodo.7080016

# Limit to 50MB - useful for quick exploration
python -m geoextent -b --max-download-size 50MB https://osf.io/4xe6z/
```

#### File Selection Methods

The `--max-download-method` parameter controls how files are selected when the size limit is reached:

```bash
# Ordered method (default): Select files in original order until limit reached
python -m geoextent -b --max-download-size 100MB --max-download-method ordered https://doi.org/10.5281/zenodo.7080016

# Random method: Randomly shuffle files before selection (useful for sampling)
python -m geoextent -b --max-download-size 200MB --max-download-method random https://doi.org/10.5281/zenodo.7080016

# Random with custom seed for reproducible results
python -m geoextent -b --max-download-size 100MB --max-download-method random --max-download-method-seed 123 https://doi.org/10.5281/zenodo.7080016
```

#### Comparing Selection Methods

Different selection methods can produce different spatial extents depending on the geographic distribution of files:

**Example with Zenodo European Land Use dataset (<https://doi.org/10.5281/zenodo.7080016>):**

```bash
# Ordered method (50MB limit) - selects first few countries alphabetically
python -m geoextent -b --max-download-size 50MB --max-download-method ordered https://doi.org/10.5281/zenodo.7080016
# Result: Covers Albania, Andorra, Austria, Belarus, Belgium (Western/Central Europe)
# Bounding box: approximately [2.5°W to 30°E, 35°N to 60°N]

# Random method (50MB limit, seed 42) - selects random geographic sample
python -m geoextent -b --max-download-size 50MB --max-download-method random --max-download-method-seed 42 https://doi.org/10.5281/zenodo.7080016
# Result: Covers Belgium, Liechtenstein, Luxembourg, Norway, Romania (scattered across Europe)
# Bounding box: approximately [5°W to 30°E, 40°N to 75°N] - larger extent due to Norway

# Different seed produces different sample
python -m geoextent -b --max-download-size 50MB --max-download-method random --max-download-method-seed 789 https://doi.org/10.5281/zenodo.7080016
# Result: Covers Finland, Poland, Spain, Sweden, Ukraine (different geographic spread)
# Bounding box: approximately [10°W to 35°E, 35°N to 70°N]
```

**Key Observations:**

- **Ordered method**: Predictable but may be geographically biased (alphabetical selection often clusters regions)
- **Random method**: Better geographic sampling but results vary with different seeds
- **Larger random samples**: Often produce more representative spatial extents
- **Shapefile preservation**: Related files (.shp, .shx, .dbf, .prj) always stay together as a unit

#### Size Limiting Behavior

The limit applies to the cumulative total of all selected files
Files are selected until adding the next file would exceed the limit

Example: With files of sizes [10MB, 15MB, 8MB, 12MB] and 20MB limit:

- Ordered: Selects 10MB file only (10MB total) - next file would exceed 20MB
- The 15MB file is skipped because 10MB + 15MB = 25MB > 20MB limit

Shapefile components are kept together as a single unit.
If a shapefile's total size (.shp + .shx + .dbf + .prj) fits within remaining space, all components are selected together. Otherwise, all are skipped together.

#### Advanced Examples

```bash
# Combine size limiting with other options
python -m geoextent -b -t --max-download-size 200MB --convex-hull --geojsonio https://doi.org/10.5281/zenodo.7080016

# Use size limiting for quick dataset exploration
python -m geoextent -b --max-download-size 10MB --max-download-method random https://osf.io/4xe6z/

# Process multiple repositories with size limits
python -m geoextent -b --max-download-size 50MB https://doi.org/10.5281/zenodo.7080016 https://osf.io/4xe6z/
```

**Note**: When no size limit is specified, all available files are downloaded and processed.

### Performance and Filtering Options

#### Parallel Downloads

Control download performance using parallel workers for faster processing of multi-file datasets:

```bash
# Use 8 parallel download workers for faster downloads
python -m geoextent -b --max-download-workers 8 https://doi.org/10.5281/zenodo.7080016

# Disable parallel downloads (use sequential, slower but more conservative)
python -m geoextent -b --max-download-workers 1 https://osf.io/4xe6z/

# Default is 4 workers - good balance of speed and server politeness
python -m geoextent -b https://doi.org/10.5281/zenodo.7080016
```

#### File Type Filtering

Skip non-geospatial files during download to save time and bandwidth:

```bash
# Skip non-geospatial files (PDFs, images, text files, etc.)
python -m geoextent -b --download-skip-nogeo https://doi.org/10.5281/zenodo.7080016

# Include additional file types as geospatial (point clouds, mesh files)
python -m geoextent -b --download-skip-nogeo --download-skip-nogeo-exts ".xyz,.las,.ply" https://osf.io/4xe6z/

# Combine filtering with size limits and parallel downloads
python -m geoextent -b --download-skip-nogeo --max-download-size 100MB --max-download-workers 6 https://doi.org/10.5281/zenodo.7080016

# OSF filtering examples - now fully supported!
python -m geoextent -b --download-skip-nogeo https://osf.io/4xe6z/
python -m geoextent -b --download-skip-nogeo --max-download-size 50MB https://doi.org/10.17605/OSF.IO/9JG2U

# Dryad filtering examples - intelligently chooses individual file downloads when filtering is needed
python -m geoextent -b --download-skip-nogeo https://datadryad.org/dataset/doi:10.5061/dryad.0k6djhb7x
python -m geoextent -b --download-skip-nogeo --max-download-size 10MB https://datadryad.org/dataset/doi:10.5061/dryad.wm37pvmvf
```

**File Type Detection**: Geospatial files are automatically detected based on extensions including: `.geojson`, `.csv`, `.shp`, `.tif`, `.gpkg`, `.gpx`, `.gml`, `.kml`, `.fgb`, and others. Use `--download-skip-nogeo-exts` to add custom extensions.

**Provider Support**: File filtering is fully supported by Figshare, Zenodo, OSF, and Dryad. Other providers (PANGAEA, GFZ, Dataverse, Pensoft) will show warnings when filtering is requested but will continue with their standard download behavior.

### Output Format Options

geoextent supports multiple output formats for spatial extents to facilitate integration with different programming languages and tools:

```bash
# Default GeoJSON format (geographic coordinates as polygon)
python -m geoextent -b tests/testdata/geojson/muenster_ring_zeit.geojson
python -m geoextent -b --format geojson tests/testdata/geojson/muenster_ring_zeit.geojson

# Well-Known Text (WKT) format
python -m geoextent -b --format wkt tests/testdata/geojson/muenster_ring_zeit.geojson

# Well-Known Binary (WKB) format as hex string
python -m geoextent -b --format wkb tests/testdata/geojson/muenster_ring_zeit.geojson
```

**Format Details:**

- **GeoJSON** (default): Returns spatial extent as a GeoJSON Polygon geometry with coordinate arrays
- **WKT**: Returns spatial extent as [Well-Known Text](https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry) POLYGON string, easily parsed by PostGIS, GDAL, and other geospatial tools
- **WKB**: Returns spatial extent as [Well-Known Binary](https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry#Well-known_binary) hexadecimal string, compact binary format for database storage

An easy way to verify these outputs is this online viewer/converter: <https://wkbrew.tszheichoi.com/>

### Quiet Mode

Use the `--quiet` option to suppress all console messages including warnings and progress bars. This is particularly useful for scripting, automation, or when you only want the final result:

```bash
# Normal output (shows progress bars and warnings)
python -m geoextent -b tests/testdata/geojson/
# Output: Progress bars, warnings, and result

# Quiet mode (clean output, no progress or warnings)
python -m geoextent -b --quiet tests/testdata/geojson/
# Output: Only the final result

# Quiet mode with specific format
python -m geoextent -b --format wkt --quiet tests/testdata/geojson/
# Output: POLYGON((6.220493316650391 50.52150360276628,7.647256851196289 50.52150360276628,7.647256851196289 51.974624029877454,6.220493316650391 51.974624029877454,6.220493316650391 50.52150360276628))

# Perfect for shell scripts and pipelines
BBOX=$(python -m geoextent -b --format wkt --quiet tests/testdata/geojson/muenster_ring_zeit.geojson)
echo "Bounding box: $BBOX"
```

You can call geoextent from within R scripts as well, for example using the `system2()` function, in combination with WKT format for creating R objects easily:

```r
sf::st_as_sfc(
  system2("geoextent",
    c("-b", "--format", "wkt", "--quiet", "tests/testdata/geojson"),
    stdout=TRUE)
  )
```

**Note**: The `--quiet` option automatically enables `--no-progress` behavior and sets logging to only show critical errors.

### Repository Extraction Options

When extracting geospatial data from research repositories, geoextent supports two extraction modes:

#### Default Mode: Data Download (Recommended)

By default, geoextent downloads actual data files from repositories and processes them locally using GDAL. This provides the most accurate and comprehensive geospatial extent extraction.

```bash
# Default behavior - downloads and processes actual data files
python -m geoextent -b -t https://doi.org/10.1594/PANGAEA.786028
python -m geoextent -b -t 10.5281/zenodo.654321
python -m geoextent -b -t https://osf.io/4xe6z
python -m geoextent -b -t OSF.IO/J2STA

# GFZ Data Services examples with geospatial datasets
python -m geoextent -b -t 10.5880/GFZ.2.1.2020.001  # Photogrammetry data from Guatemala
python -m geoextent -b -t 10.5880/GFZ.4.8.2023.004  # Geothermal resources in North German Basin
```

#### Metadata-Only Mode (Limited)

Use the `--no-download-data` flag to extract information from repository metadata only, without downloading actual files. This is faster but may result in incomplete or missing spatial/temporal extents, especially for providers like Zenodo, Figshare, Dryad, and OSF that don't include detailed geospatial metadata.

```bash
# Metadata-only extraction (not recommended for most use cases)
python -m geoextent -b -t --no-download-data https://doi.org/10.1594/PANGAEA.786028
```

**Note**: PANGAEA datasets often include rich geospatial metadata, but for best results and compatibility with all providers, the default data download mode is recommended.

### Convex Hull Extraction

The `--convex-hull` option calculates the [convex hull](https://en.wikipedia.org/wiki/Convex_hull) of all geometries instead of just the bounding box for vector data files. This provides a more accurate representation of the actual spatial extent of complex geometries.

**Key Features:**
- **Vector files only**: Works with GeoJSON, Shapefile, GeoPackage, GPX, GML, KML, and FlatGeobuf formats
- **Automatic fallback**: Non-vector files (CSV, raster) automatically fall back to standard bounding box calculation
- **Multiple file support**: When processing multiple files or directories, creates a convex hull from all merged geometries
- **Format compatibility**: Works with all output formats (GeoJSON, WKT, WKB)

```bash
# Basic convex hull extraction
python -m geoextent -b --convex-hull tests/testdata/geojson/ausgleichsflaechen_moers.geojson

# Convex hull with quiet output and WKT format
python -m geoextent -b --convex-hull --format wkt --quiet tests/testdata/geojson/muenster_ring_zeit.geojson

# Process directory with convex hull calculation
python -m geoextent -b --convex-hull tests/testdata/geojson/

# Multiple files with convex hull merging
python -m geoextent -b --convex-hull tests/testdata/geojson/ausgleichsflaechen_moers.geojson tests/testdata/geojson/muenster_ring_zeit.geojson
```

**Output differences:**
- Convex hull results include `"convex_hull": true` in the JSON output
- The spatial extent represents the convex hull boundary rather than just the bounding rectangle
- For non-vector files, output remains unchanged (standard bounding box)

### Example Output

Extracting from a single GeoJSON file with default format:

```json
{
  "format": "geojson",
  "geoextent_handler": "handleVector",
  "bbox": {
    "type": "Polygon",
    "coordinates": [[[7.60, 51.95], [7.65, 51.95], [7.65, 51.97], [7.60, 51.97], [7.60, 51.95]]]
  },
  "crs": "4326",
  "tbox": ["2018-11-14", "2018-11-14"]
}
```

With WKT format (`--format wkt`):

```json
{
  "format": "geojson",
  "geoextent_handler": "handleVector",
  "bbox": "POLYGON((7.60 51.95,7.65 51.95,7.65 51.97,7.60 51.97,7.60 51.95))",
  "crs": "4326",
  "tbox": ["2018-11-14", "2018-11-14"]
}
```

With WKB format (`--format wkb`):

```json
{
  "format": "geojson",
  "geoextent_handler": "handleVector",
  "bbox": "0103000000010000000500000033333333333F1E403D0AD7A3703D4A40CDCCCCCCCC2F1F403D0AD7A3703D4A40CDCCCCCCCC2F1F40A4703D0A17394A4033333333333F1E40A4703D0A17394A4033333333333F1E403D0AD7A3703D4A40",
  "crs": "4326",
  "tbox": ["2018-11-14", "2018-11-14"]
}
```

Extracting with convex hull calculation:

```json
{
  "format": "geojson",
  "geoextent_handler": "handleVector",
  "bbox": {
    "type": "Polygon",
    "coordinates": [[[7.60, 51.95], [7.65, 51.95], [7.65, 51.97], [7.60, 51.97], [7.60, 51.95]]]
  },
  "crs": "4326",
  "convex_hull": true,
  "tbox": ["2018-11-14", "2018-11-14"]
}
```

Extracting from multiple files:

```json
{
  "format": "multiple_files",
  "crs": "4326",
  "bbox": [2.05, 41.32, 7.65, 53.22],
  "tbox": ["2017-08-01", "2019-09-30"],
  "details": {
    "cities.csv": {"format": "csv", "bbox": [...], "tbox": [...]},
    "districts.geojson": {"format": "geojson", "bbox": [...], "tbox": [...]}
  }
}
```

## Showcases

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/nuest/geoextent/main?filepath=showcase%2FSG_01_Exploring_Research_Data_Repositories_with_geoextent.ipynb)

To run the showcase notebooks, install [JupyterLab](https://jupyter.org/) or the classic Jupyter Notebook and then start a local server as shown below.
If your IDE has support for the Jupyter format, installing `ipykernel` might be enough.
We recommend running the below commands in a virtual environment as described [here](https://jupyter-tutorial.readthedocs.io/en/latest/first-steps/install.html).
The notebook must be [trusted](https://jupyter-notebook.readthedocs.io/en/stable/security.html#notebook-security) and [python-markdown extension](https://jupyter-contrib-nbextensions.readthedocs.io/en/latest/install.html) must be installed so that variables within Markdown text can be shown.

```bash
cd showcase
pip install -r requirements.txt
pip install -r showcase/requirements.txt
pip install -e .

jupyter trust showcase/SG_01_Exploring_Research_Data_Repositories_with_geoextent.ipynb
jupyter lab
```

Then open the local Jupyter Notebook server using the displayed link and open the notebook (`*.ipynb` files) in the `showcase/` directory.
Consult the documentation on [paired notebooks based on Jupytext](https://github.com/mwouts/jupytext/blob/master/docs/paired-notebooks.md) before editing selected notebooks.

## Supported data formats

- GeoJSON (.geojson)
- Tabular data (.csv)
- Shapefile (.shp)
- GeoTIFF (.geotiff, .tif)
- GeoPackage (.gpkg)
- GPS Exchange Format (.gpx)
- Geography Markup Language (.gml)
- Keyhole Markup Language (.kml)
- FlatGeobuf (.fgb)

## Supported data repositories

- [Zenodo](https://zenodo.org/) - Research data repository
- [Dryad](https://datadryad.org/) - Data publishing platform
- [Figshare](https://figshare.com/) - Research data sharing platform
- [PANGAEA](https://www.pangaea.de/) - Earth & Environmental Science data publisher
- [OSF](https://osf.io/) - Open Science Framework
- [GFZ Data Services](https://dataservices.gfz-potsdam.de/) - Geoscientific research data from GFZ Potsdam

## Development

### Testing

Run tests using pytest:

```bash
# Install development dependencies
pip install -e .[dev,test]

# Run all tests
pytest

# Run specific test categories
pytest tests/test_api_*.py         # API tests
pytest tests/test_cli*.py          # CLI tests
pytest -m "not slow"               # Exclude slow tests

# Run with coverage
pytest --cov=geoextent --cov-report=term-missing
```

### Local GitHub Actions Testing

Test workflows locally using [act](https://github.com/nektos/act):

```bash
# Install act (macOS/Linux)
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run main test suite
./scripts/test-local-ci.sh

# Run specific test categories
./scripts/test-local-ci.sh --workflow comprehensive-tests --test-category api-core

# List all available workflows and jobs
./scripts/test-local-ci.sh --list-jobs

# See all options
./scripts/test-local-ci.sh --help
```

Available test categories:

- `api-core`: Core API functionality
- `api-repositories`: Repository providers (Zenodo, Figshare, Dryad, PANGAEA, OSF, GFZ, Pensoft, Dataverse)
- `api-formats`: Format handlers (CSV, GeoJSON, GeoTIFF, Shapefile, FlatGeobuf)
- `cli`: Command-line interface
- `integration`: Integration and special features

### Code Formatting

```bash
# Format code with black
black geoextent/ tests/

# Set up pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## Contribute

All help is welcome: asking questions, providing documentation, testing, or even development.

Please note that this project is released with a [Contributor Code of Conduct](https://github.com/nuest/geoextent/blob/main/CONDUCT.md).
By participating in this project you agree to abide by its terms.

See [CONTRIBUTING.md](https://github.com/nuest/geoextent/blob/main/CONTRIBUTING.md) for details.

## How to cite

> Nüst, Daniel; Garzón, Sebastian and Qamaz, Yousef. (2021, May 14). o2r-project/geoextent (Version v0.7.1). Zenodo. [https://zenodo.org/record/4762205](https://zenodo.org/record/4762205)

See also the `CITATION.cff` and `codemeta.json` files in this repository, which can possibly be imported in the reference manager of your choice.

## License

`geoextent` is licensed under MIT license, see file [LICENSE](https://github.com/o2r-project/nuest/blob/main/LICENSE).

Copyright (C) 2025 - o2r project and project contributors.
