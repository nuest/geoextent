# geoextent

![Python package](https://github.com/nuest/geoextent/workflows/Python%20package/badge.svg?branch=main) [![PyPI version](https://badge.fury.io/py/geoextent.svg)](https://pypi.org/project/geoextent/0.12.0/)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/nuest/main) [![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18635399.svg)](https://doi.org/10.5281/zenodo.18635399) [![SWH](https://archive.softwareheritage.org/badge/origin/https://github.com/nuest/geoextent.git/)](https://archive.softwareheritage.org/browse/origin/?origin_url=https://github.com/nuest/geoextent.git)

Python library for extracting geospatial and temporal extents from files and directories.

**Key Capabilities:**

- Extract spatial extents (bounding boxes, convex hulls) and temporal extents
- Support for 10+ file formats (GeoJSON, CSV, Shapefile, GeoTIFF, GeoPackage, GPX, GML, KML, FlatGeobuf, Esri File Geodatabase) plus world files
- Direct integration with [31 research repositories](https://nuest.github.io/geoextent/providers.html) ([Zenodo](https://zenodo.org/), [PANGAEA](https://www.pangaea.de/), [OSF](https://osf.io/), [Figshare](https://figshare.com/), [4TU.ResearchData](https://data.4tu.nl/), [Dryad](https://datadryad.org/), [GFZ](https://dataservices.gfz-potsdam.de/), [RADAR](https://www.radar-service.eu/), [Arctic Data Center](https://arcticdata.io/), [B2SHARE](https://b2share.eudat.eu/), [MDI-DE](https://www.mdi-de.org/), [GDI-DE](https://www.geoportal.de/), [NFDI4Earth](https://onestop4all.nfdi4earth.de/), [SEANOE](https://www.seanoe.org/), [UKCEH](https://catalogue.ceh.ac.uk/), [GBIF](https://www.gbif.org/), [DEIMS-SDR](https://deims.org/), [HALO DB](https://halo-db.pa.op.dlr.de/), [Dataverse](https://dataverse.org/) [[Harvard](https://dataverse.harvard.edu/), [DataverseNL](https://dataverse.nl/), [DataverseNO](https://dataverse.no/), [UNC](https://dataverse.unc.edu/), [UVA](https://data.library.virginia.edu/), [Recherche Data Gouv](https://recherche.data.gouv.fr/), [ioerDATA](https://data.fdz.ioer.de/), [heiDATA](https://heidata.uni-heidelberg.de/), [Edmond](https://edmond.mpg.de/)], [Pensoft](https://pensoft.net/), [TU Dresden Opara](https://opara.zih.tu-dresden.de/), [Senckenberg](https://dataportal.senckenberg.de/), [BGR](https://geoportal.bgr.de/), [BAW](https://datenrepository.baw.de/), [Mendeley Data](https://data.mendeley.com/)), [Wikidata](https://www.wikidata.org/), any [STAC](https://stacspec.org/) catalog, and any [CKAN](https://ckan.org/) instance (e.g. [data.gov.uk](https://ckan.publishing.service.gov.uk/), [GovData.de](https://ckan.govdata.de/), [data.gov.au](https://data.gov.au/), [data.gov.ie](https://data.gov.ie/))
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
geoextent -b -t tests/testdata/geojson/muenster_ring_zeit.geojson

# Extract from research repository
python -m geoextent -b -t https://doi.org/10.5281/zenodo.4593540

# Extract merged bbox from multiple local files
geoextent -b -t tests/testdata/geojson/muenster_ring_zeit.geojson tests/testdata/csv/cities_NL.csv

# Extract from multiple repositories (returns merged geometry)
python -m geoextent -b 10.5281/zenodo.123 10.25532/OPARA-456

# Extract convex hull from multiple Wikidata items and open in geojson.io
python -m geoextent -b --convex-hull --geojsonio Q64 Q35 Q60786916
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
- **Process Research Data** - Extract extents from Zenodo, Figshare, Dryad, PANGAEA, OSF, SEANOE, UKCEH, GBIF, DEIMS-SDR, NFDI4Earth, any STAC catalog, and more
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
# Install dev and test dependencies
pip install -e .[dev,test,docs]

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

## Showcase Notebooks

Interactive Jupyter notebooks demonstrating geoextent are available in the [`showcase/`](showcase/) directory:

- **[NFDI4Earth Knowledge Hub × geoextent](showcase/nfdi4earth_geoextent_showcase.ipynb)** — Queries the [NFDI4Earth Knowledge Hub](https://knowledgehub.nfdi4earth.de/) SPARQL endpoint to map NFDI4Earth-labelled and harvested repositories to geoextent providers, analyses dataset spatial/temporal metadata coverage, and demonstrates live extraction with `geoextent.fromRemote()`.
- **[Exploring Research Data Repositories with geoextent](showcase/SG_01_Exploring_Research_Data_Repositories_with_geoextent.ipynb)** — EarthCube 2021 case study analysing Zenodo records.

To run the notebooks:

```bash
cd showcase
pip install -r requirements.txt
pip install -e ..  # install geoextent from local checkout
jupyter lab
```

## Contributing

Contributions are welcome! Please use the [issue tracker](https://github.com/nuest/geoextent/issues) to report bugs or suggest features, and submit pull requests for code or documentation improvements.

## Citation

If you use geoextent in your research, please cite:

> Nüst, Daniel; Garzón, Sebastian and Qamaz, Yousef. (2021, May 11). o2r-project/geoextent (Version v0.7.1). Zenodo. <https://doi.org/10.5281/zenodo.3925693>

## License

This software is published under the MIT license. See the `LICENSE` file for details.

This documentation is published under a Creative Commons CC0 1.0 Universal License.
