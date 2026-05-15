# geoextent

![Python package](https://github.com/nuest/geoextent/workflows/Python%20package/badge.svg?branch=main) [![PyPI version](https://badge.fury.io/py/geoextent.svg)](https://pypi.org/project/geoextent/0.12.0/)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/nuest/main) [![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18635399.svg)](https://doi.org/10.5281/zenodo.18635399) [![SWH](https://archive.softwareheritage.org/badge/origin/https://github.com/nuest/geoextent.git/)](https://archive.softwareheritage.org/browse/origin/?origin_url=https://github.com/nuest/geoextent.git)

Python library for extracting geospatial and temporal extents from files and directories.

**Key Capabilities:**

- Extract spatial extents (bounding boxes, convex hulls) and temporal extents
- Support for 10+ file formats (GeoJSON, CSV, Shapefile, GeoTIFF, GeoPackage, GPX, GML, KML, FlatGeobuf, Esri File Geodatabase, LAS/LAZ point clouds) plus world files
- Plain-text inputs via spaCy named entity recognition + place and time-period gazetteers; recognises calendar dates, decade/century envelopes, ranges, and named geological periods (ICS GTS2020)
- Direct integration with [35 research repositories](https://nuest.github.io/geoextent/providers.html) ([Zenodo](https://zenodo.org/), [PANGAEA](https://www.pangaea.de/), [OSF](https://osf.io/), [Figshare](https://figshare.com/), [4TU.ResearchData](https://data.4tu.nl/), [Dryad](https://datadryad.org/), [GFZ](https://dataservices.gfz-potsdam.de/), [RADAR](https://www.radar-service.eu/), [Arctic Data Center](https://arcticdata.io/), [DataONE](https://www.dataone.org/), [B2SHARE](https://b2share.eudat.eu/), [MDI-DE](https://www.mdi-de.org/), [GDI-DE](https://www.geoportal.de/), [NFDI4Earth](https://onestop4all.nfdi4earth.de/), [SEANOE](https://www.seanoe.org/), [GeoScienceWorld](https://pubs.geoscienceworld.org/), [UKCEH](https://catalogue.ceh.ac.uk/), [GBIF](https://www.gbif.org/), [DEIMS-SDR](https://deims.org/), [HALO DB](https://halo-db.pa.op.dlr.de/), [GitHub](https://github.com/), [GitLab](https://gitlab.com/), [Software Heritage](https://www.softwareheritage.org/), [Dataverse](https://dataverse.org/) [[Harvard](https://dataverse.harvard.edu/), [DataverseNL](https://dataverse.nl/), [DataverseNO](https://dataverse.no/), [UNC](https://dataverse.unc.edu/), [UVA](https://data.library.virginia.edu/), [Recherche Data Gouv](https://recherche.data.gouv.fr/), [ioerDATA](https://data.fdz.ioer.de/), [heiDATA](https://heidata.uni-heidelberg.de/), [Edmond](https://edmond.mpg.de/)], [Pensoft](https://pensoft.net/), [TU Dresden Opara](https://opara.zih.tu-dresden.de/), [Senckenberg](https://dataportal.senckenberg.de/), [BGR](https://geoportal.bgr.de/), [BAW](https://datenrepository.baw.de/), [Mendeley Data](https://data.mendeley.com/)), [Wikidata](https://www.wikidata.org/), any [STAC](https://stacspec.org/) catalog, and any [CKAN](https://ckan.org/) instance (e.g. [data.gov.uk](https://ckan.publishing.service.gov.uk/), [GovData.de](https://ckan.govdata.de/), [data.gov.au](https://data.gov.au/), [data.gov.ie](https://data.gov.ie/))
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

# Extract convex hull from multiple Wikidata items and open in geojson.io.
# --convex-hull keeps the GeoJSON payload under the 150 KB URL-fragment limit
# of the geojsonio wrapper; the anonymous-gist fallback for larger payloads
# is no longer reachable since GitHub requires auth for gist creation.
# See the text-extraction guide for details.
python -m geoextent -b --convex-hull --geojsonio Q64 Q35 Q60786916

# Parallel extraction from a directory (auto-detect CPU cores)
geoextent -p -b -t path/to/geodata_directory

# Parallel extraction with 4 workers
geoextent -p 4 -b -t path/to/geodata_directory

# Extract place names from free text — spaCy NER + Nominatim by default,
# no API key required. Install the optional extra and English model once:
#   pip install geoextent[nlp] && python -m spacy download en_core_web_sm
geoextent -b --text "Field campaigns in Berlin and Paris"
echo "Workshops in Tokyo and London" | geoextent -b -
geoextent -b notes.md

# Keep the highest-ranked gazetteer match instead of dropping ambiguous names
geoextent -b --ner-ambiguity top --text "Field campaigns in Berlin and Paris"

# Administrative boundaries: Nominatim returns the polygon of areal features,
# so a state name resolves to its bounding polygon rather than a centroid.
geoextent -b --ner-ambiguity top --text "Field campaign in Saxony"
# Force the centroid instead with --place-geometry point
geoextent -b --ner-ambiguity top --place-geometry point --text "Field campaign in Saxony"

# Extract a temporal extent from text — calendar dates, decades, centuries,
# ranges, and named geological time periods (ICS GTS2020 bundled gazetteer)
geoextent -t --text "Monitoring ran between 2010 and 2015"
# → "tbox": ["2010-01-01", "2015-12-31"]
geoextent -t --text "Sediment cores from the Holocene"
# → "tbox": ["-9750-01-01", "1950-01-01"]  (signed ISO 8601: years before 1 BCE
#    are prefixed with `-`; deep-time periods like the Mesozoic produce
#    long-year strings such as "-251900050-01-01")
geoextent -b -t --text "Pleistocene cores near Berlin re-surveyed on 2024-05-12"

# Show the source text with matched place names and periods highlighted
geoextent -b -t --annotate brackets \
  --text "Sediment cores in Berlin span the Holocene; resurvey on 2024-05-12"
# → ...JSON...
# → ---annotated source (brackets)---
# → Sediment cores in [[Berlin|place]] span the [[Holocene|period]]; resurvey on [[2024-05-12|date]]

# Disable text extraction (e.g. when processing directories of structured
# data and you don't want README.md to be NER-ed)
geoextent -b -t --text-method none path/to/data_dir
```

For each matched place / date / period, geoextent also emits standoff
`char_start` / `char_end` offsets into the (NFC-normalised) source so
external tools can highlight matches independently:

```python
from geoextent.lib import extent
result = extent.from_text("Sediment cores in Berlin span the Holocene.",
                          bbox=True, tbox=True,
                          ner_ambiguity="top")
src = result["source_text"]
for rec in result["place_names"] + result["date_entities"]:
    s, e = rec["char_start"], rec["char_end"]
    print(f"{rec.get('kind', 'place'):6} {src[s:e]!r} → {rec.get('gazetteer_url') or rec.get('start')}")
```

See [the text-extraction guide](https://nuest.github.io/geoextent/howto/text-extraction.html) for examples and gotchas, or [the highlighting guide](https://nuest.github.io/geoextent/howto/highlighting.html) for the offset contract and a JS/Java re-encoding recipe.

See the [CLI guide](https://nuest.github.io/geoextent/howto/cli.html) for all options.

### Python API

```python
import geoextent.lib.extent as geoextent

# From file
result = geoextent.fromFile('data.geojson', bbox=True, tbox=True)

# From directory
result = geoextent.fromDirectory('data/', bbox=True, tbox=True)

# From directory with parallel extraction (0 = auto-detect CPU cores)
result = geoextent.from_directory('data/', bbox=True, tbox=True, workers=0)

# From repository (single or multiple)
result = geoextent.fromRemote('10.5281/zenodo.4593540', bbox=True)

identifiers = ['10.5281/zenodo.4593540', '10.25532/OPARA-581']
result = geoextent.fromRemote(identifiers, bbox=True)
print(result['bbox'])  # Merged bounding box covering all resources
```

See the [API documentation](https://nuest.github.io/geoextent/howto/api.html) and [examples](https://nuest.github.io/geoextent/examples.html).

## What Can I Do With geoextent?

- **Extract Spatial Extents** - Get bounding boxes or convex hulls from geospatial files
- **Process Research Data** - Extract extents from Zenodo, Figshare, Dryad, PANGAEA, OSF, DataONE, SEANOE, UKCEH, GBIF, DEIMS-SDR, NFDI4Earth, GitHub, GitLab, any STAC catalog, and more
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

### Bundled third-party material

- `geoextent/lib/data/periods.json` — the named-time-period gazetteer used by
  the text/NER source. Derived from the **International Chronostratigraphic
  Chart** (ICS / IUGS, GTS2020 vocabulary), distributed by CGI-IUGS at
  <https://github.com/CGI-IUGS/timescale-data> and dedicated to the public
  domain under **CC0-1.0**
  (<https://creativecommons.org/publicdomain/zero/1.0/>). The file embeds the
  upstream commit SHA, build timestamp, and full attribution string in its
  metadata block; run `geoextent --list-periods` to read it.
- The DOI regex and helper functions in `geoextent/lib/helpfunctions.py` are
  derived from [`idutils`](https://github.com/inveniosoftware/idutils)
  (© 2015-2018 CERN; © 2018 Alan Rubin) under **BSD-3-Clause**, as noted
  inline.
