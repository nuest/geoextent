# geoextent

![Python package](https://github.com/nuest/geoextent/workflows/Python%20package/badge.svg?branch=main) [![PyPI version](https://badge.fury.io/py/geoextent.svg)](https://pypi.org/project/geoextent/0.1.0/)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/nuest/main) [![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.3925694.svg)](https://doi.org/10.5281/zenodo.3925694) [![SWH](https://archive.softwareheritage.org/badge/origin/https://github.com/nuest/geoextent.git/)](https://archive.softwareheritage.org/browse/origin/?origin_url=https://github.com/nuest/geoextent.git) [![SWH](https://archive.softwareheritage.org/badge/swh:1:dir:ff1e19d884833b2bc2c1ef7d9265ba45b5314332/)](https://archive.softwareheritage.org/swh:1:dir:ff1e19d884833b2bc2c1ef7d9265ba45b5314332;origin=https://github.com/nuest/geoextent.git;visit=swh:1:snp:609428a8b466b7877f2ca39921d69a5f6a11df9f;anchor=swh:1:rev:6aca93956d5cd6742318fd3ab27bb176b5f8c24b;path=//)

Python library for extracting geospatial extent of files and directories with multiple data formats.
[Read a notebook-based article about the library published at EarthCube 2021](https://earthcube2021.github.io/ec21_book/notebooks/ec21_garzon_etal/showcase/SG_01_Exploring_Research_Data_Repositories_with_geoextent.html).

This project was originally developed as part of the [DFG-funded](https://o2r.info/about/#funding) research project Opening Reproducible Research (o2r, [https://o2r.info](https://o2r.info)).

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
python -m geoextent -b data/cities.geojson

# Extract temporal extent from a single file
python -m geoextent -t data/measurements.csv

# Extract both spatial and temporal extents
python -m geoextent -b -t data/survey.shp

# Process a directory of files
python -m geoextent -b -t data/

# Process multiple specific files
python -m geoextent -b -t data/boundaries.shp data/points.csv data/tracks.gpkg

# Process multiple files with wildcard (shell expansion)
python -m geoextent -t data/*.geojson

# Show detailed results for each file
python -m geoextent -b -t --details data/countries.fgb data/cities.geojson

# Extract from research repositories (DOI, URL, or identifier)
python -m geoextent -b -t https://zenodo.org/records/4593540
python -m geoextent -b -t 10.5281/zenodo.4593540
python -m geoextent -b -t https://doi.org/10.1594/PANGAEA.734969
python -m geoextent -b -t https://osf.io/4xe6z
python -m geoextent -b -t 10.17605/OSF.IO/4XE6Z
python -m geoextent -b -t https://doi.org/10.17605/OSF.IO/J2STA
python -m geoextent -b -t http://dx.doi.org/10.17605/OSF.IO/A5F3E
python -m geoextent -b -t OSF.IO/9JG2U

# Use metadata-only extraction for repositories (not recommended)
python -m geoextent -b -t --no-download-data 10.5281/zenodo.4593540
```

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
```

#### Metadata-Only Mode (Limited)

Use the `--no-download-data` flag to extract information from repository metadata only, without downloading actual files. This is faster but may result in incomplete or missing spatial/temporal extents, especially for providers like Zenodo, Figshare, Dryad, and OSF that don't include detailed geospatial metadata.

```bash
# Metadata-only extraction (not recommended for most use cases)
python -m geoextent -b -t --no-download-data https://doi.org/10.1594/PANGAEA.786028
```

**Note**: PANGAEA datasets often include rich geospatial metadata, but for best results and compatibility with all providers, the default data download mode is recommended.

### Example Output

Extracting from a single GeoJSON file:

```json
{
  "format": "geojson",
  "geoextent_handler": "handleVector",
  "bbox": [7.60, 51.95, 7.65, 51.97],
  "crs": "4326",
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

Copyright (C) 2020 - o2r project.
