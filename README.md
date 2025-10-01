# geoextent

![Python package](https://github.com/nuest/geoextent/workflows/Python%20package/badge.svg?branch=main) [![PyPI version](https://badge.fury.io/py/geoextent.svg)](https://pypi.org/project/geoextent/0.1.0/)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/nuest/main) [![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.3925694.svg)](https://doi.org/10.5281/zenodo.3925694) [![SWH](https://archive.softwareheritage.org/badge/origin/https://github.com/nuest/geoextent.git/)](https://archive.softwareheritage.org/browse/origin/?origin_url=https://github.com/nuest/geoextent.git) [![SWH](https://archive.softwareheritage.org/badge/swh:1:dir:ff1e19d884833b2bc2c1ef7d9265ba45b5314332/)](https://archive.softwareheritage.org/swh:1:dir:ff1e19d884833b2bc2c1ef7d9265ba45b5314332;origin=https://github.com/nuest/geoextent.git;visit=swh:1:snp:609428a8b466b7877f2ca39921d69a5f6a11df9f;anchor=swh:1:rev:6aca93956d5cd6742318fd3ab27bb176b5f8c24b;path=//)

Python library for extracting geospatial extent of files and directories with multiple data formats.

**Key Features:**

- Extract spatial (bounding box/convex hull) and temporal extents
- Support for 9+ file formats (GeoJSON, CSV, Shapefile, GeoTIFF, etc.)
- Direct integration with 8 research repositories (Zenodo, PANGAEA, OSF, Figshare, Dryad, GFZ, Dataverse, Pensoft)
- Command-line interface and Python API
- Docker support for easy deployment

[📖 Full Documentation](https://nuest.github.io/geoextent/) | [📦 PyPI](https://pypi.org/project/geoextent/) | [📓 EarthCube 2021 Article](https://earthcube2021.github.io/ec21_book/notebooks/ec21_garzon_etal/showcase/SG_01_Exploring_Research_Data_Repositories_with_geoextent.html)

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

### Requirements

- Python 3.10+
- GDAL 3.11.x

### Install from PyPI

```bash
pip install geoextent
```

### Install from Source

```bash
git clone https://github.com/nuest/geoextent
cd geoextent
pip install -e .[dev,test,docs]
```

For detailed installation instructions including system dependencies, see the [installation guide](https://nuest.github.io/geoextent/install.html).

### Docker

Docker images are available for easy deployment without managing dependencies:

```bash
# Build the Docker image
docker build -t geoextent .

# Run geoextent using Docker
docker run --rm geoextent -b https://doi.org/10.5281/zenodo.4593540
```

See the [Docker guide](https://nuest.github.io/geoextent/howto/docker.html) for detailed usage examples.

## Quick Start

### Basic Usage

```bash
# Extract bounding box from a file
python -m geoextent -b tests/testdata/geojson/muenster_ring_zeit.geojson

# Extract both spatial and temporal extents
python -m geoextent -b -t tests/testdata/csv/cities_NL.csv

# Extract from research repository
python -m geoextent -b -t https://doi.org/10.5281/zenodo.4593540

# Extract with convex hull (more precise for vector data)
python -m geoextent -b --convex-hull tests/testdata/geojson/muenster_ring.geojson
```

### Python API

```python
import geoextent.lib.extent as geoextent

# From file
result = geoextent.fromFile('data.geojson', bbox=True, tbox=True)

# From directory
result = geoextent.fromDirectory('data/', bbox=True, tbox=True)

# From repository
result = geoextent.fromRemote('10.5281/zenodo.4593540', bbox=True, tbox=True)
```

For comprehensive examples and advanced features, see the [examples documentation](https://nuest.github.io/geoextent/examples.html).

## Supported Formats

**Data Formats:** GeoJSON, CSV, Shapefile, GeoTIFF, GeoPackage, GPX, GML, KML, FlatGeobuf

**Repositories:** Zenodo, PANGAEA, OSF, Figshare, Dryad, GFZ Data Services, Dataverse, Pensoft

See [full format documentation](https://nuest.github.io/geoextent/supportedformats/index_supportedformats.html) for details.

## Advanced Features

geoextent includes many advanced features for specialized use cases:

- **Placename lookup** - Add geographic context using GeoNames, Nominatim, or Photon
- **Download size limiting** - Control data download size with flexible file selection methods
- **File filtering** - Skip non-geospatial files to save bandwidth
- **Parallel downloads** - Speed up multi-file processing with parallel workers
- **Output formats** - GeoJSON (default), WKT, or WKB output
- **Quiet mode** - Suppress output for scripting and automation

See the [features documentation](https://nuest.github.io/geoextent/features.html) for detailed information on all advanced features.

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black geoextent/ tests/
pre-commit install
```

### Building Documentation

```bash
pip install -e .[docs]
cd docs && make html
```

See the [development guide](https://nuest.github.io/geoextent/development.html) for detailed instructions including local CI testing with act.

## Contributing

Contributions of all kinds are welcome! This includes bug reports, feature suggestions, code improvements, and documentation enhancements.

Please use the [issue tracker](https://github.com/nuest/geoextent/issues) to report bugs or suggest features, and submit pull requests for code or documentation improvements.

## Citation

If you use geoextent in your research, please cite:

> Nüst, Daniel; Garzón, Sebastian and Qamaz, Yousef. (2021, May 11). o2r-project/geoextent (Version v0.7.1). Zenodo. <https://doi.org/10.5281/zenodo.3925693>

## License

This software is published under the MIT license, see file `LICENSE` for details.

This documentation is published under a Creative Commons CC0 1.0 Universal License.
