# geoextent

![Python package](https://github.com/nuest/geoextent/workflows/Python%20package/badge.svg?branch=main) [![PyPI version](https://badge.fury.io/py/geoextent.svg)](https://pypi.org/project/geoextent/0.1.0/)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/nuest/main) [![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.3925694.svg)](https://doi.org/10.5281/zenodo.3925694) [![SWH](https://archive.softwareheritage.org/badge/origin/https://github.com/nuest/geoextent.git/)](https://archive.softwareheritage.org/browse/origin/?origin_url=https://github.com/nuest/geoextent.git)

Python library for extracting geospatial and temporal extents from files and directories.

**Key Capabilities:**

- Extract spatial extents (bounding boxes, convex hulls) and temporal extents
- Support for 9+ file formats (GeoJSON, CSV, Shapefile, GeoTIFF, GeoPackage, GPX, GML, KML, FlatGeobuf)
- Direct integration with 10 research repositories (Zenodo, PANGAEA, OSF, Figshare, Dryad, GFZ, Dataverse, Pensoft, TU Dresden Opara, Senckenberg)
- Process single files, directories, or multiple repositories in one call
- Command-line interface and Python API
- Export as GeoJSON, WKT, or WKB

[📖 Full Documentation](https://nuest.github.io/geoextent/) | [📦 PyPI](https://pypi.org/project/geoextent/) | [🚀 Quick Start](https://nuest.github.io/geoextent/quickstart.html) | [📓 EarthCube 2021 Article](https://earthcube2021.github.io/ec21_book/notebooks/ec21_garzon_etal/showcase/SG_01_Exploring_Research_Data_Repositories_with_geoextent.html)

## Installation

```bash
pip install geoextent
```

**Requirements:** Python 3.10+ and GDAL 3.11.x

See the [installation guide](https://nuest.github.io/geoextent/install.html) for system dependencies and Docker setup.

## Quick Start

### Command Line

```bash
# Extract from a file
python -m geoextent -b tests/testdata/geojson/muenster_ring.geojson

# Extract from research repository
python -m geoextent -b -t https://doi.org/10.5281/zenodo.4593540

# Extract from multiple repositories (returns merged geometry)
python -m geoextent -b 10.5281/zenodo.123 10.25532/OPARA-456
```

See the [CLI guide](https://nuest.github.io/geoextent/howto/cli.html) for all options.

### Python API

```python
import geoextent.lib.extent as geoextent

# From file
result = geoextent.fromFile('data.geojson', bbox=True, tbox=True)

# From directory
result = geoextent.fromDirectory('data/', bbox=True, tbox=True)

# From repository (single or multiple)
result = geoextent.fromRemote('10.5281/zenodo.4593540', bbox=True)

identifiers = ['10.5281/zenodo.4593540', '10.25532/OPARA-581']
result = geoextent.fromRemote(identifiers, bbox=True)
print(result['bbox'])  # Merged bounding box covering all resources
```

See the [API documentation](https://nuest.github.io/geoextent/howto/api.html) and [examples](https://nuest.github.io/geoextent/examples.html).

## What Can I Do With geoextent?

- **Extract Spatial Extents** - Get bounding boxes or convex hulls from geospatial files
- **Process Research Data** - Extract extents from Zenodo, Figshare, Dryad, PANGAEA, OSF, and more
- **Batch Processing** - Process directories or multiple repositories in one call
- **Add Location Context** - Automatic placename lookup for your data
- **Flexible Output** - Export as GeoJSON, WKT, or WKB for use in other tools
- **Interactive Visualization** - Open extracted extents in geojson.io with one command

## Documentation

- **[Quick Start Guide](https://nuest.github.io/geoextent/quickstart.html)** - Get started in minutes
- **[Installation Guide](https://nuest.github.io/geoextent/install.html)** - System dependencies, Docker setup
- **[Examples](https://nuest.github.io/geoextent/examples.html)** - Common usage patterns with code
- **[CLI Reference](https://nuest.github.io/geoextent/howto/cli.html)** - Command-line options
- **[Python API](https://nuest.github.io/geoextent/howto/api.html)** - Function signatures and parameters
- **[Core Features](https://nuest.github.io/geoextent/core-features.html)** - Essential features for everyday use
- **[Advanced Features](https://nuest.github.io/geoextent/advanced-features.html)** - Specialized options
- **[Content Providers](https://nuest.github.io/geoextent/providers.html)** - Repository integration details
- **[Supported Formats](https://nuest.github.io/geoextent/supportedformats/index_supportedformats.html)** - File format details
- **[Development Guide](https://nuest.github.io/geoextent/development.html)** - Contributing and testing

## Development

This project was developed as part of the [DFG-funded](https://o2r.info/about/#funding) research project Opening Reproducible Research (o2r, [https://o2r.info](https://o2r.info)).

```bash
# Run tests (parallel execution enabled by default with -n auto)
pytest

# Run tests with specific number of workers
pytest -n 4

# Disable parallel execution for debugging
pytest -n 0

# Format code
black geoextent/ tests/
pre-commit install
```

See the [development guide](https://nuest.github.io/geoextent/development.html) for detailed instructions.

## Contributing

Contributions are welcome! Please use the [issue tracker](https://github.com/nuest/geoextent/issues) to report bugs or suggest features, and submit pull requests for code or documentation improvements.

## Citation

If you use geoextent in your research, please cite:

> Nüst, Daniel; Garzón, Sebastian and Qamaz, Yousef. (2021, May 11). o2r-project/geoextent (Version v0.7.1). Zenodo. <https://doi.org/10.5281/zenodo.3925693>

## License

This software is published under the MIT license. See the `LICENSE` file for details.

This documentation is published under a Creative Commons CC0 1.0 Universal License.
