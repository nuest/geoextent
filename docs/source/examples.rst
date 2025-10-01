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

PANGAEA datasets often include rich geospatial metadata.

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

   python -m geoextent -b -t https://datadryad.org/stash/dataset/doi:10.5061/dryad.0k6djhb7x

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

   # Limit to 10MB total download
   python -m geoextent -b --max-download-size 10MB https://doi.org/10.5281/zenodo.4593540

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

Combine with convex hull:

::

   python -m geoextent -b --convex-hull --geojsonio https://doi.org/10.1594/PANGAEA.734969

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

   python -m geoextent -b https://doi.org/10.6084/m9.figshare.12345678

Dryad:
::

   python -m geoextent -b https://datadryad.org/stash/dataset/doi:10.5061/dryad.0k6djhb7x

PANGAEA:
::

   python -m geoextent -b https://doi.org/10.1594/PANGAEA.734969

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
