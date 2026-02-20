Examples
========

This page provides comprehensive examples covering all features of geoextent using datasets under 100MB for fast execution.

Remote Repository Examples
---------------------------

Geoextent supports extracting geospatial extent from multiple research data repositories.

Zenodo Example
^^^^^^^^^^^^^^

Extract extent from a Zenodo atmospheric data repository (~50MB):

::

   python -m geoextent -b -t https://doi.org/10.5281/zenodo.4593540

Or using just the DOI:

::

   python -m geoextent -b -t 10.5281/zenodo.4593540

ZIP File Support
""""""""""""""""

Geoextent automatically detects and extracts ZIP files from remote repositories, including nested archives. Extract from a Zenodo repository containing a single ZIP file (~1MB):

::

   python -m geoextent -b https://doi.org/10.5281/zenodo.3446746

This will download the ZIP file, extract all geospatial data inside (GeoPackage, Shapefile, etc.), and calculate the spatial extent. Works with all supported repository providers.

PANGAEA Example
^^^^^^^^^^^^^^^

Extract extent from PANGAEA Arctic Ocean dataset (~1MB):

::

   python -m geoextent -b -t https://doi.org/10.1594/PANGAEA.734969

PANGAEA datasets often include rich geospatial metadata. Both tabular and non-tabular data are supported, including datasets with downloadable files (GeoJSON, GeoTIFF, Shapefile, etc.):

::

   # Non-tabular dataset with GeoTIFF files
   python -m geoextent -b https://doi.org/10.1594/PANGAEA.913496

   # Non-tabular dataset with GeoJSON files
   python -m geoextent -b https://doi.org/10.1594/PANGAEA.858767

OSF Example
^^^^^^^^^^^

Extract extent from OSF geographic research data (~5MB):

::

   python -m geoextent -b -t https://doi.org/10.17605/OSF.IO/4XE6Z

Multiple OSF identifier formats are supported:

::

   python -m geoextent -b -t OSF.IO/4XE6Z
   python -m geoextent -b -t https://osf.io/4xe6z/

GFZ Data Services Example
^^^^^^^^^^^^^^^^^^^^^^^^^^

Extract extent from GFZ geothermal resources dataset (~30MB):

::

   python -m geoextent -b -t 10.5880/GFZ.4.8.2023.004

Dryad Example
^^^^^^^^^^^^^

Extract extent from Dryad dataset:

::

   python -m geoextent -b -t https://doi.org/10.5061/dryad.0k6djhb7x

TU Dresden Opara Example
^^^^^^^^^^^^^^^^^^^^^^^^^

Extract extent from TU Dresden Opara repository (DSpace 7.x):

::

   python -m geoextent -b -t https://opara.zih.tu-dresden.de/items/4cdf08d6-2738-4c9e-9d27-345a0647ff7c

Multiple URL variants are supported:

::

   python -m geoextent -b -t 10.25532/OPARA-581
   python -m geoextent -b -t https://doi.org/10.25532/OPARA-581
   python -m geoextent -b -t https://opara.zih.tu-dresden.de/handle/123456789/821

This example dataset contains glacier calving front locations with ZIP files containing nested directories and multiple shapefiles.

UKCEH (EIDC) Example
^^^^^^^^^^^^^^^^^^^^^

Extract extent from a UKCEH Environmental Information Data Centre dataset (metadata-only):

::

   python -m geoextent -b -t --no-download-data 10.5285/dd35316a-cecc-4f6d-9a21-74a0f6599e9e

Download data and extract extent:

::

   python -m geoextent -b -t 10.5285/dd35316a-cecc-4f6d-9a21-74a0f6599e9e

UKCEH supports both Apache datastore directory listings and data-package ZIP downloads. The provider tries the datastore first (enabling selective file download) and falls back to the ZIP if needed.

Convex hull from a multi-region UKCEH dataset (3 bounding boxes across Africa):

::

   python -m geoextent -b --convex-hull --no-download-data 10.5285/3de48cb6-d1c2-446e-a652-57d329849361

DEIMS-SDR Example
^^^^^^^^^^^^^^^^^^

Extract extent from a DEIMS-SDR ecological research dataset (metadata-only):

::

   python -m geoextent -b -t https://deims.org/dataset/3d87da8b-2b07-41c7-bf05-417832de4fa2

Extract spatial extent from a DEIMS-SDR research site:

::

   python -m geoextent -b https://deims.org/8eda49e9-1f4e-4f3e-b58e-e0bb25dc32a6

DEIMS-SDR is a metadata-only provider. It extracts geospatial boundaries (POINT, POLYGON, MULTIPOLYGON) and temporal ranges from the DEIMS-SDR REST API for long-term ecological research sites and datasets.

NFDI4Earth Knowledge Hub Example
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extract extent from the NFDI4Earth Knowledge Hub (metadata-only, via SPARQL):

::

   # Schiffsdichte 2013 — North Sea shipping density (spatial only)
   python -m geoextent -b https://onestop4all.nfdi4earth.de/result/dthb-82b6552d-2b8e-4800-b955-ea495efc28af/

   # ESA Antarctic Ice Sheet — spatial + temporal extent (1994–2021)
   python -m geoextent -b -t https://onestop4all.nfdi4earth.de/result/dthb-7b3bddd5af4945c2ac508a6d25537f0a/

NFDI4Earth is a metadata-only provider. It extracts WKT geometry and temporal ranges from the SPARQL endpoint. When a dataset has a ``landingPage`` URL that matches another supported provider, geoextent automatically follows it. Use ``--no-follow`` to stay with NFDI4Earth metadata:

::

   python -m geoextent -b -t --no-follow https://onestop4all.nfdi4earth.de/result/dthb-82b6552d-2b8e-4800-b955-ea495efc28af/

STAC Catalog Example
^^^^^^^^^^^^^^^^^^^^^

Extract extent from any STAC (SpatioTemporal Asset Catalog) Collection. STAC Collections contain pre-computed bounding boxes and temporal intervals, so extraction is instant (metadata-only, no file downloads).

::

   # US National Agriculture Imagery (Element84 Earth Search)
   python -m geoextent -b -t https://earth-search.aws.element84.com/v1/collections/naip

   # German forest structure (DLR EOC) — open-ended temporal range
   python -m geoextent -b -t https://geoservice.dlr.de/eoc/ogc/stac/v1/collections/FOREST_STRUCTURE_DE_COVER_P1Y

   # Switzerland population data (WorldPop)
   python -m geoextent -b -t https://api.stac.worldpop.org/collections/CHE

Any URL pointing to a STAC Collection is supported — geoextent recognizes known STAC API hosts, ``/stac/`` URL path patterns, and falls back to JSON content inspection. See :doc:`providers` for the full list of known hosts.

CKAN Example
^^^^^^^^^^^^

Extract extent from any CKAN open data portal. The generic CKAN provider works with all CKAN instances.

**Metadata-only extraction** (fast, no file downloads):

::

   # GeoKur TU Dresden — global cropland extent with temporal range
   python -m geoextent -b -t --no-download-data https://geokur-dmp.geo.tu-dresden.de/dataset/cropland-extent

   # German GovData — Rhine surface water sampling dataset
   python -m geoextent -b -t --no-download-data https://ckan.govdata.de/dataset/a-spatially-distributed-sampling-of-rhine-surface-water-for-non-target-screening

**Data download** (downloads files and extracts extent from contents):

::

   # Ireland — downloads Shapefile of Dublin library locations
   python -m geoextent -b https://data.gov.ie/dataset/libraries-dlr

   # Australia — downloads GeoJSON of Gisborne neighbourhood precincts
   python -m geoextent -b https://data.gov.au/dataset/gisborne-neighbourhood-character-precincts

**Recommended: metadata-first strategy** for CKAN datasets, which tries catalogue metadata first and falls back to data download if needed:

::

   python -m geoextent -b -t --metadata-first https://ckan.govdata.de/dataset/a-spatially-distributed-sampling-of-rhine-surface-water-for-non-target-screening

The CKAN provider supports known hosts (instant matching) and unknown CKAN instances (verified via API probe). See :doc:`providers` for the full list of known hosts.

GitHub Example
^^^^^^^^^^^^^^

Extract extent from public GitHub repositories. The GitHub provider downloads geospatial files and extracts their spatial and temporal extent.

**Repository root** (all geospatial files):

::

   python -m geoextent -b https://github.com/fraxen/tectonicplates

**Specific subdirectory** (only files under the given path):

::

   python -m geoextent -b https://github.com/Nowosad/spDataLarge/tree/master/inst/raster

**Skip non-geospatial files** (recommended for repositories with many non-geospatial files):

::

   python -m geoextent -b --download-skip-nogeo https://github.com/fraxen/tectonicplates

The GitHub provider preserves directory structure when downloading, which is essential for shapefile components and world files. Set the ``GITHUB_TOKEN`` environment variable for higher API rate limits (5000/hour vs 60/hour unauthenticated).

Advanced Features
-----------------

Convex Hull Extraction
^^^^^^^^^^^^^^^^^^^^^^

Calculate the convex hull instead of just the bounding box for vector files:

::

   python -m geoextent -b --convex-hull https://doi.org/10.5281/zenodo.4593540

This provides a more accurate representation of the actual spatial extent.

Placename Lookup
^^^^^^^^^^^^^^^^

Add geographic context to your extracts:

::

   # Using default GeoNames gazetteer (requires API key in .env)
   python -m geoextent -b --placename https://doi.org/10.5281/zenodo.4593540

   # Using Nominatim (no API key needed)
   python -m geoextent -b --placename nominatim https://doi.org/10.1594/PANGAEA.734969

   # Using Photon (no API key needed)
   python -m geoextent -b --placename photon https://osf.io/4xe6z/

Size Limiting
^^^^^^^^^^^^^

Control download size when processing large repositories:

::

   # Limit to 10MB total download (ordered method - files as returned by provider)
   python -m geoextent -b --max-download-size 10MB https://doi.org/10.5281/zenodo.4593540

   # Select smallest files first to maximize file coverage within size limit
   python -m geoextent -b --max-download-size 100MB --max-download-method smallest https://doi.org/10.25532/OPARA-703

   # Select largest files first (useful when you want the most substantial data)
   python -m geoextent -b --max-download-size 500MB --max-download-method largest https://doi.org/10.5281/zenodo.4593540

   # Random sampling with seed for reproducibility
   python -m geoextent -b --max-download-size 50MB --max-download-method random --max-download-method-seed 42 https://doi.org/10.5281/zenodo.4593540

File Filtering
^^^^^^^^^^^^^^

Skip non-geospatial files to save time:

::

   python -m geoextent -b --download-skip-nogeo https://doi.org/10.5281/zenodo.4593540

Combine with size limits:

::

   python -m geoextent -b --download-skip-nogeo --max-download-size 50MB https://osf.io/4xe6z/

Output Formats
^^^^^^^^^^^^^^

Choose different output formats:

::

   # Default GeoJSON format
   python -m geoextent -b https://doi.org/10.1594/PANGAEA.734969

   # Well-Known Text (WKT) format
   python -m geoextent -b --format wkt https://doi.org/10.1594/PANGAEA.734969

   # Well-Known Binary (WKB) hex format
   python -m geoextent -b --format wkb https://doi.org/10.1594/PANGAEA.734969

Visualization
^^^^^^^^^^^^^

Generate geojson.io URLs for interactive visualization:

::

   python -m geoextent -b --geojsonio https://doi.org/10.5281/zenodo.4593540

Open the visualization directly in your browser (without printing URL):

::

   python -m geoextent -b --browse https://doi.org/10.5281/zenodo.4593540

Print URL and open in browser (use both options):

::

   python -m geoextent -b --geojsonio --browse https://doi.org/10.5281/zenodo.4593540

Combine with other options:

::

   python -m geoextent -b --convex-hull --geojsonio --browse https://doi.org/10.1594/PANGAEA.734969

Quiet Mode
^^^^^^^^^^

Suppress progress bars and warnings for scripting:

::

   python -m geoextent -b --quiet https://doi.org/10.1594/PANGAEA.734969

Perfect for shell scripts:

::

   BBOX=$(python -m geoextent -b --format wkt --quiet https://doi.org/10.1594/PANGAEA.734969)
   echo "Bounding box: $BBOX"

Local File Examples
-------------------

All GeoJSON outputs automatically include extraction metadata with version information, input sources, and processing statistics. See the Extraction Metadata section in the Advanced Features documentation for details.

Single File Processing
^^^^^^^^^^^^^^^^^^^^^^

Extract from GeoJSON:

::

   python -m geoextent -b -t tests/testdata/geojson/muenster_ring_zeit.geojson

Extract from CSV:

::

   python -m geoextent -b -t tests/testdata/csv/cities_NL.csv

Extract from Shapefile:

::

   python -m geoextent -b -t tests/testdata/shapefile/muenster_ring.shp

Directory Processing
^^^^^^^^^^^^^^^^^^^^

Process all files in a directory:

::

   python -m geoextent -b -t tests/testdata/geojson/

With convex hull:

::

   python -m geoextent -b --convex-hull tests/testdata/geojson/

Multiple Files
^^^^^^^^^^^^^^

Process specific files together:

::

   python -m geoextent -b -t tests/testdata/shapefile/muenster_ring.shp tests/testdata/csv/cities_NL.csv

Mix files and directories:

::

   python -m geoextent -b -t tests/testdata/geojson/muenster_ring_zeit.geojson tests/testdata/folders/folder_two_files

Use ``--details`` for per-file breakdown:

::

   python -m geoextent -b -t --details tests/testdata/geojson/muenster_ring_zeit.geojson tests/testdata/csv/cities_NL.csv tests/testdata/geopackage/nc.gpkg

Convex hull from multiple files:

::

   python -m geoextent -b --convex-hull tests/testdata/geojson/muenster_ring_zeit.geojson tests/testdata/folders/folder_two_files/districtes.geojson tests/testdata/csv/cities_NL.csv

Combined Examples
-----------------

All Features Together
^^^^^^^^^^^^^^^^^^^^^

Extract with all features enabled:

::

   python -m geoextent -b -t \
     --convex-hull \
     --placename nominatim \
     --max-download-size 50MB \
     --download-skip-nogeo \
     --format wkt \
     --geojsonio \
     https://doi.org/10.5281/zenodo.4593540

Multiple Repositories
^^^^^^^^^^^^^^^^^^^^^^

Process multiple repositories together:

::

   python -m geoextent -b \
     --max-download-size 20MB \
     https://doi.org/10.5281/zenodo.4593540 \
     https://doi.org/10.1594/PANGAEA.734969 \
     https://osf.io/4xe6z/

Docker Examples
---------------

Basic Docker Usage
^^^^^^^^^^^^^^^^^^

Using Docker for remote repositories:

::

   docker run --rm geoextent -b https://doi.org/10.5281/zenodo.4593540

With placename lookup:

::

   docker run --rm --env-file .env geoextent -b --placename https://doi.org/10.5281/zenodo.4593540

Local files with Docker:

::

   docker run --rm -v ${PWD}/tests/testdata:/data geoextent -b -t /data/geojson/

Performance Options
-------------------

Parallel Downloads
^^^^^^^^^^^^^^^^^^

Control download workers:

::

   # Use 8 parallel workers
   python -m geoextent -b --max-download-workers 8 https://doi.org/10.5281/zenodo.4593540

   # Sequential downloads (slower but safer)
   python -m geoextent -b --max-download-workers 1 https://doi.org/10.5281/zenodo.4593540

Testing Examples
----------------

Quick Repository Exploration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Explore a repository with minimal download:

::

   python -m geoextent -b \
     --max-download-size 5MB \
     --max-download-method random \
     --quiet \
     https://doi.org/10.5281/zenodo.4593540

Format Coverage Examples
------------------------

These examples demonstrate all supported formats using small datasets:

GeoJSON
^^^^^^^
::

   python -m geoextent -b -t tests/testdata/geojson/muenster_ring_zeit.geojson

CSV
^^^
::

   python -m geoextent -b -t tests/testdata/csv/cities_NL.csv

Shapefile
^^^^^^^^^
::

   python -m geoextent -b tests/testdata/shapefile/muenster_ring.shp

GeoTIFF
^^^^^^^
::

   python -m geoextent -b tests/testdata/tif/wf_100m_klas.tif

GeoPackage
^^^^^^^^^^
::

   python -m geoextent -b tests/testdata/geopackage/nc.gpkg

GPX
^^^
::

   python -m geoextent -b -t tests/testdata/gpx/gpx1.1_with_all_fields.gpx

KML
^^^
::

   python -m geoextent -b tests/testdata/kml/aasee.kml

GML
^^^
::

   python -m geoextent -b tests/testdata/gml/clc_1000_PT.gml

FlatGeobuf
^^^^^^^^^^
::

   python -m geoextent -b tests/testdata/flatgeobuf/sample.fgb

Repository Provider Coverage
----------------------------

All Supported Providers
^^^^^^^^^^^^^^^^^^^^^^^

Examples for each repository provider:

Zenodo:
::

   python -m geoextent -b https://doi.org/10.5281/zenodo.4593540

Figshare:
::

   python -m geoextent -b https://figshare.com/articles/dataset/London_boroughs/11373984

Figshare (institutional portal - ICES Library):
::

   python -m geoextent -b https://ices-library.figshare.com/articles/dataset/HELCOM_request_2022_for_spatial_data_layers_on_effort_fishing_intensity_and_fishing_footprint_for_the_years_2016-2021/20310255

Figshare (metadata-only - USDA Ag Data Commons with geospatial coverage):
::

   python -m geoextent -b --no-download-data https://api.figshare.com/v2/articles/30753383

Dryad:
::

   python -m geoextent -b https://datadryad.org/stash/dataset/doi:10.5061/dryad.0k6djhb7x

PANGAEA (tabular data):
::

   python -m geoextent -b https://doi.org/10.1594/PANGAEA.734969

PANGAEA (non-tabular data - GeoTIFF files):
::

   python -m geoextent -b https://doi.org/10.1594/PANGAEA.913496

OSF:
::

   python -m geoextent -b https://doi.org/10.17605/OSF.IO/4XE6Z

GFZ Data Services:
::

   python -m geoextent -b 10.5880/GFZ.4.8.2023.004

Dataverse:
::

   python -m geoextent -b https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/12345

Pensoft:
::

   python -m geoextent -b https://doi.org/10.3897/BDJ.2.e1068

TU Dresden Opara:
::

   python -m geoextent -b 10.25532/OPARA-581

NFDI4Earth Knowledge Hub (OneStop4All URL):
::

   python -m geoextent -b -t https://onestop4all.nfdi4earth.de/result/dthb-7b3bddd5af4945c2ac508a6d25537f0a/

STAC Catalog (any STAC Collection URL):
::

   python -m geoextent -b -t https://earth-search.aws.element84.com/v1/collections/naip

Interactive Showcase Notebooks
-------------------------------

Explore geoextent's capabilities through interactive Jupyter notebooks that demonstrate real-world usage with research data repositories.

Running Showcase Notebooks
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. image:: https://mybinder.org/badge_logo.svg
   :target: https://mybinder.org/v2/gh/nuest/geoextent/main?filepath=showcase%2FSG_01_Exploring_Research_Data_Repositories_with_geoextent.ipynb
   :alt: Launch Binder

Click the Binder badge above to run the showcase notebooks in your browser without installation.

Local Setup
^^^^^^^^^^^

To run the showcase notebooks locally, install JupyterLab or the classic Jupyter Notebook. We recommend using a virtual environment::

   cd showcase
   pip install -r requirements.txt
   pip install -r showcase/requirements.txt
   pip install -e .

   # Trust the notebook for full functionality
   jupyter trust showcase/SG_01_Exploring_Research_Data_Repositories_with_geoextent.ipynb

   # Start Jupyter
   jupyter lab

Then open the local Jupyter Notebook server using the displayed link and open the notebook files (``*.ipynb``) in the ``showcase/`` directory.

.. note::
   The notebook must be `trusted <https://jupyter-notebook.readthedocs.io/en/stable/security.html#notebook-security>`_ and the `python-markdown extension <https://jupyter-contrib-nbextensions.readthedocs.io/en/latest/install.html>`_ should be installed so that variables within Markdown text can be shown.

.. note::
   Some notebooks use `paired notebooks based on Jupytext <https://github.com/mwouts/jupytext/blob/master/docs/paired-notebooks.md>`_. Consult the Jupytext documentation before editing these notebooks.
