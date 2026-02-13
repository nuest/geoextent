Senckenberg Data Portal Examples
=================================

This page demonstrates how to use geoextent with the Senckenberg Biodiversity and Climate Research Centre data portal.

Overview
--------

Senckenberg operates a CKAN-based data portal at https://dataportal.senckenberg.de/ providing access to biodiversity, climate, and geoscience research datasets. Geoextent supports extracting spatial and temporal extents from Senckenberg datasets using various identifier formats.

.. important::
   **Senckenberg is primarily a metadata repository.** Most datasets contain rich geospatial and temporal metadata but may not have downloadable data files, or files may be restricted.

   **Best Practice:** Always use ``--no-download-data`` (metadata-only mode) when working with Senckenberg datasets to extract spatial and temporal extents from the metadata without attempting to download potentially unavailable files.

Supported Identifiers
---------------------

DOI Format
^^^^^^^^^^

Use Senckenberg DOIs directly (recommended with ``--no-download-data``):

.. code-block:: bash

   python -m geoextent -b -t --no-download-data 10.12761/sgn.2018.10225

DOI Resolver URLs:

.. code-block:: bash

   python -m geoextent -b --no-download-data https://doi.org/10.12761/sgn.2018.10225

Dataset URLs
^^^^^^^^^^^^

Direct dataset landing pages:

.. code-block:: bash

   python -m geoextent -b --no-download-data https://dataportal.senckenberg.de/dataset/as-sahabi-1

JSON-LD URLs (metadata format):

.. code-block:: bash

   python -m geoextent -b --no-download-data https://dataportal.senckenberg.de/dataset/as-sahabi-1.jsonld

Dataset IDs
^^^^^^^^^^^

Name slugs:

.. code-block:: bash

   python -m geoextent -b --no-download-data as-sahabi-1

UUID format:

.. code-block:: bash

   python -m geoextent -b --no-download-data 00dda005-68c0-4e92-96e5-ceb68034f3ba

Common Use Cases
----------------

Temporal and Spatial Extraction (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extract both spatial and temporal extent from metadata (most common use case):

.. code-block:: bash

   # Command line
   python -m geoextent -b -t --no-download-data 10.12761/sgn.2018.10268

.. code-block:: python

   # Python API
   import geoextent.lib.extent as geoextent

   # Extract both spatial (bbox) and temporal (tbox) extent
   result = geoextent.fromRemote(
       '10.12761/sgn.2018.10268',
       bbox=True,
       tbox=True,
       download_data=False  # Metadata-only extraction
   )

   print(f"Location: {result['bbox']}")
   # Output: [-79.1667, -4.0992, -78.9667, -3.9667] (Ecuador)

   print(f"Time period: {result['tbox']}")
   # Output: ['2014-05-01', '2015-12-30']

**Why this example?**

- Dataset: "Functional responses of avian frugivores to variation in fruit resources"
- Contains complete spatial coverage (bounding box in Ecuador)
- Contains temporal coverage (May 2014 to December 2015)
- Metadata-only extraction works perfectly without downloading files
- Demonstrates the recommended workflow for Senckenberg

Basic Spatial Extraction
^^^^^^^^^^^^^^^^^^^^^^^^^

Extract spatial extent only from a Senckenberg dataset:

.. code-block:: python

   import geoextent.lib.extent as geoextent

   # Using DOI (always use download_data=False for Senckenberg)
   result = geoextent.fromRemote(
       '10.12761/sgn.2018.10225',
       bbox=True,
       download_data=False
   )
   print(result['bbox'])

   # Using dataset URL
   result = geoextent.fromRemote(
       'https://dataportal.senckenberg.de/dataset/as-sahabi-1',
       bbox=True,
       download_data=False
   )

   # Using dataset name
   result = geoextent.fromRemote(
       'as-sahabi-1',
       bbox=True,
       download_data=False
   )

Why Use Metadata-Only Mode?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Metadata-only extraction (``--no-download-data``) is **recommended for all Senckenberg datasets** because:

- **Primary use case**: Senckenberg is a metadata repository - most datasets have rich metadata but limited/restricted data files
- **Faster extraction**: No time wasted attempting to download unavailable files
- **Accurate results**: Spatial and temporal metadata in CKAN is authoritative
- **Bandwidth efficient**: No unnecessary downloads
- **Works with restricted datasets**: Metadata is publicly accessible even when data files are restricted

.. code-block:: bash

   # Always use --no-download-data for Senckenberg
   python -m geoextent -b -t --no-download-data 10.12761/sgn.2018.10225

With Size Limits
^^^^^^^^^^^^^^^^

Download only a subset of files to stay within size constraints:

.. code-block:: bash

   python -m geoextent -b \
       --max-download-size 50MB \
       as-sahabi-1

Geospatial Files Only
^^^^^^^^^^^^^^^^^^^^^

Skip non-geospatial files (like documentation, scripts, etc.):

.. code-block:: bash

   python -m geoextent -b \
       --download-skip-nogeo \
       as-sahabi-1

This will prioritize downloading:

- Shapefiles (.shp, .shx, .dbf, .prj)
- GeoJSON files (.geojson, .json)
- GeoTIFF files (.tif, .tiff)
- Archives that might contain geospatial data (.zip, .tar.gz)
- Other geospatial formats (GeoPackage, KML, etc.)

Multiple Datasets
^^^^^^^^^^^^^^^^^

Extract and merge extents from multiple Senckenberg datasets:

.. code-block:: python

   import geoextent.lib.extent as geoextent

   datasets = [
       'as-sahabi-1',
       '10.12761/sgn.2018.10225',
   ]

   result = geoextent.fromRemote(datasets, bbox=True, tbox=True)

   # Returns merged bounding box covering all datasets
   print(f"Combined extent: {result['bbox']}")
   print(f"Temporal range: {result.get('tbox', 'N/A')}")

   # Access individual dataset results
   for dataset_id, dataset_result in result['details'].items():
       print(f"{dataset_id}: {dataset_result.get('bbox', 'No bbox')}")

Mixed Providers
^^^^^^^^^^^^^^^

Combine Senckenberg datasets with other repositories:

.. code-block:: bash

   python -m geoextent -b \
       10.12761/sgn.2018.10225 \
       10.5281/zenodo.4593540 \
       10.25532/OPARA-581

Python API Examples
-------------------

Basic Usage
^^^^^^^^^^^

.. code-block:: python

   import geoextent.lib.extent as geoextent

   # Extract spatial and temporal extent
   result = geoextent.fromRemote(
       'as-sahabi-1',
       bbox=True,
       tbox=True
   )

   if 'bbox' in result:
       print(f"Spatial extent: {result['bbox']}")
       print(f"CRS: {result['crs']}")

   if 'tbox' in result:
       print(f"Temporal extent: {result['tbox']}")

Advanced Options
^^^^^^^^^^^^^^^^

.. code-block:: python

   import geoextent.lib.extent as geoextent

   result = geoextent.fromRemote(
       '10.12761/sgn.2018.10225',
       bbox=True,
       tbox=True,
       convex_hull=True,           # Extract convex hull instead of bbox
       details=True,               # Include detailed file information
       max_download_size='100MB',  # Limit total download size
       download_skip_nogeo=True,   # Skip non-geospatial files
       max_download_workers=8,     # Parallel downloads
       placename='nominatim'       # Add placename lookup
   )

   # Access detailed information
   if 'details' in result:
       for filename, file_info in result['details'].items():
           print(f"{filename}: {file_info}")

Error Handling
^^^^^^^^^^^^^^

.. code-block:: python

   import geoextent.lib.extent as geoextent

   try:
       result = geoextent.fromRemote('invalid-dataset-id', bbox=True)
       print(f"Success: {result}")
   except Exception as e:
       print(f"Error extracting extent: {e}")

   # For multiple datasets, check individual errors
   datasets = ['as-sahabi-1', 'invalid-dataset']
   result = geoextent.fromRemote(datasets, bbox=True)

   for dataset_id, dataset_result in result['details'].items():
       if 'error' in dataset_result:
           print(f"{dataset_id}: ERROR - {dataset_result['error']}")
       else:
           print(f"{dataset_id}: SUCCESS - {dataset_result.get('bbox', 'No bbox')}")

Example Datasets
----------------

As-Sahabi 1
^^^^^^^^^^^

Paleontological dataset from Libya with geospatial data:

.. code-block:: bash

   python -m geoextent -b https://dataportal.senckenberg.de/dataset/as-sahabi-1

**Contains:**

- Study area shapefile (ZIP archive)
- Spatial fossil data (CSV)
- Research data and analyses

**Use case:** Extracting spatial extent from fossil site locations

Grazer Population Model
^^^^^^^^^^^^^^^^^^^^^^^

Dataset with spatial extent metadata but restricted data access:

.. code-block:: bash

   python -m geoextent -b --no-download-data \
       00dda005-68c0-4e92-96e5-ceb68034f3ba

**Contains:**

- Metadata with spatial coverage (East & South African Savannahs)
- Temporal coverage (1960-2006)
- Model data (may require authorization)

**Use case:** Metadata extraction for datasets with access restrictions

Technical Details
-----------------

CKAN Integration
^^^^^^^^^^^^^^^^

Senckenberg uses CKAN (Comprehensive Knowledge Archive Network), an open-source data management system. Geoextent leverages the CKAN API for:

- Dataset metadata retrieval
- File listing and download URLs
- Spatial and temporal metadata extraction

Authentication
^^^^^^^^^^^^^^

Some Senckenberg datasets may have restricted access. Geoextent will:

- Download publicly accessible files
- Skip restricted files with appropriate warnings
- Extract metadata when available

For full access to restricted datasets, contact the data providers directly.

See Also
--------

- :doc:`providers` - All supported content providers
- :doc:`howto/api` - Complete Python API documentation
- :doc:`howto/cli` - Command-line interface reference
- :doc:`examples` - General usage examples
