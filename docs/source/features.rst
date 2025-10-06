Advanced Features
==================

This page documents advanced features and options available in geoextent for specialized use cases.

Features API
------------

Overview
^^^^^^^^

The geoextent Features API provides machine-readable information about all supported file formats and content providers. This enables external tools, libraries, and user interfaces to discover geoextent's capabilities programmatically and validate inputs before processing.

**Key Features:**

- **Dynamic Information**: All data is extracted from existing class properties and methods, not hardcoded
- **Validation Functions**: Validate file formats and remote identifiers before calling geoextent
- **JSON Export**: Machine-readable JSON format for integration with other tools
- **CLI Access**: Command-line option for quick access to capabilities

CLI Usage
^^^^^^^^^

List all features::

   python -m geoextent --list-features

This outputs a JSON document containing:

- Version information
- File format handlers with capabilities and supported extensions
- Content providers with URL patterns, DOI prefixes, and examples

Example output structure:

.. code-block:: json

   {
     "version": "0.9.1",
     "file_formats": [
       {
         "handler": "handleVector",
         "description": "Vector geospatial formats",
         "capabilities": {
           "bounding_box": true,
           "temporal_extent": true,
           "convex_hull": true
         },
         "file_extensions": [".geojson", ".shp", ".gpkg", "..."]
       }
     ],
     "content_providers": [
       {
         "name": "Opara",
         "description": "OPARA is the Open Access Repository...",
         "website": "https://opara.zih.tu-dresden.de/",
         "doi_prefix": "10.25532/OPARA",
         "url_patterns": ["..."],
         "supported_identifiers": ["..."],
         "examples": ["..."]
       }
     ]
   }

Python API Usage
^^^^^^^^^^^^^^^^

Import functions::

   from geoextent.lib.features import (
       get_supported_features,
       get_supported_features_json,
       validate_remote_identifier,
       validate_file_format
   )

**Get all features:**

.. code-block:: python

   # Get as Python dict
   features = get_supported_features()

   print(f"Version: {features['version']}")
   print(f"Handlers: {len(features['file_formats'])}")
   print(f"Providers: {len(features['content_providers'])}")

   # Get as JSON string
   json_output = get_supported_features_json(indent=2)

**Validate remote identifiers:**

Validate a DOI, URL, or identifier before calling ``fromRemote()``:

.. code-block:: python

   result = validate_remote_identifier("10.25532/OPARA-581")

   if result['valid']:
       print(f"Supported by: {result['provider']}")
       # Proceed with geoextent extraction
   else:
       print(f"Error: {result['message']}")

**Validate file formats:**

Check if a file format is supported before calling ``fromFile()``:

.. code-block:: python

   result = validate_file_format("data.geojson")

   if result['valid']:
       print(f"Handler: {result['handler']}")
       # Proceed with geoextent extraction
   else:
       print(f"Error: {result['message']}")

Use Cases
"""""""""

**1. Web Application Input Validation**

.. code-block:: python

   # Validate user input before processing
   user_input = request.form['identifier']
   validation = validate_remote_identifier(user_input)

   if validation['valid']:
       # Process with geoextent
       extent = geoextent.fromRemote(user_input, bbox=True)
   else:
       # Show error to user
       return {"error": validation['message']}

**2. Documentation Generation**

.. code-block:: python

   # Auto-generate documentation from features
   features = get_supported_features()

   for provider in features['content_providers']:
       print(f"## {provider['name']}")
       print(f"DOI Prefix: {provider['doi_prefix']}")
       print(f"Examples:")
       for example in provider['examples']:
           print(f"  - {example}")

**3. Testing Frameworks**

.. code-block:: python

   # Ensure all providers are tested
   features = get_supported_features()
   provider_names = [p['name'] for p in features['content_providers']]

   for name in provider_names:
       test_name = f"test_{name.lower()}_provider"
       assert hasattr(TestSuite, test_name), f"Missing test for {name}"

Supported Content Providers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All supported content providers are included with their name, description, website, DOI prefix, URL patterns, and examples:

1. **Zenodo** - ``10.5281/zenodo`` - `zenodo.org <https://zenodo.org/>`_

   Free and open digital archive built by CERN and OpenAIRE for sharing research output in any format.

2. **Figshare** - ``10.6084/m9.figshare`` - `figshare.com <https://figshare.com/>`_

   Online open access repository for preserving and sharing research outputs with DOI assignment and altmetrics.

3. **Dryad** - ``10.5061/dryad`` - `datadryad.org <https://datadryad.org/>`_

   Nonprofit curated repository specializing in data underlying scientific publications with CC0 licensing.

4. **PANGAEA** - ``10.1594/PANGAEA`` - `pangaea.de <https://www.pangaea.de/>`_

   Digital data library and publisher for earth system science with over 375,000 georeferenced datasets.

5. **OSF** - ``10.17605/OSF.IO`` - `osf.io <https://osf.io/>`_

   Free open-source project management tool by Center for Open Science for collaborative research workflows.

6. **Dataverse** - ``10.7910/DVN`` (varies by instance) - `dataverse.org <https://dataverse.org/>`_

   Open-source web application from Harvard University for sharing and preserving research data across disciplines.

7. **GFZ Data Services** - ``10.5880/GFZ`` - `dataservices.gfz-potsdam.de <https://dataservices.gfz-potsdam.de/>`_

   Curated repository for geosciences domain hosted at GFZ German Research Centre in Potsdam.

8. **Pensoft** - ``10.3897`` - `pensoft.net <https://pensoft.net/>`_

   Scholarly publisher from Bulgaria specializing in biodiversity with 60+ open access journals.

9. **OPARA (TU Dresden)** - ``10.25532/OPARA`` - `opara.zih.tu-dresden.de <https://opara.zih.tu-dresden.de/>`_

   Open Access Repository for research data of Saxon universities with 10-year archiving guarantee.

Multiple Remote Resource Extraction
------------------------------------

Overview
^^^^^^^^

The ``fromRemote()`` function accepts either a single identifier (string) or multiple identifiers (list) for extracting geospatial and temporal extents. When multiple identifiers are provided, the function returns a **merged geometry** (bounding box or convex hull) covering all resources, similar to directory extraction. This is useful for:

- Processing multiple datasets from different repositories
- Comparing spatial coverage across multiple sources
- Automated workflows that need to handle lists of DOIs
- Creating combined metadata for related datasets

Python API
^^^^^^^^^^

**Extract from multiple remote resources (list):**

.. code-block:: python

   from geoextent.lib import extent

   identifiers = [
       '10.5281/zenodo.4593540',
       '10.25532/OPARA-581',
       'https://osf.io/abc123/'
   ]

   result = extent.fromRemote(
       identifiers,
       bbox=True,
       tbox=True,
       max_download_size='100MB',
       download_skip_nogeo=True
   )

   # Access merged bounding box (covers all resources)
   print(result['bbox'])  # [minx, miny, maxx, maxy]
   print(result['crs'])   # '4326'

   # Check extraction statistics
   metadata = result['extraction_metadata']
   print(f"Total: {metadata['total_resources']}")
   print(f"Successful: {metadata['successful']}")
   print(f"Failed: {metadata['failed']}")

   # Optional: Access individual resource details for diagnostics
   for identifier, details in result['details'].items():
       if 'error' in details:
           print(f"Failed: {identifier} - {details['error']}")

**Extract from single remote resource (string):**

.. code-block:: python

   result = extent.fromRemote(
       '10.5281/zenodo.4593540',
       bbox=True,
       tbox=True
   )

CLI Usage
^^^^^^^^^

The CLI supports multiple inputs including remote resources::

   # Extract from multiple repositories
   python -m geoextent -b -t \
       10.5281/zenodo.4593540 \
       10.25532/OPARA-581 \
       https://osf.io/abc123/

   # Mix remote resources with local files (also supported)
   python -m geoextent -b -t \
       data.geojson \
       10.5281/zenodo.4593540 \
       data_dir/

Features
^^^^^^^^

All standard ``fromRemote()`` parameters are supported:

- ``bbox``, ``tbox``, ``convex_hull`` - Extraction options
- ``max_download_size``, ``max_download_method`` - Download control
- ``download_skip_nogeo`` - File filtering
- ``max_download_workers`` - Parallel processing
- ``placename`` - Geographic context lookup
- ``details`` - Include detailed extraction information

Return Structure
^^^^^^^^^^^^^^^^

For multiple identifiers (list input), the function returns a **merged geometry** covering all resources:

.. code-block:: python

   {
       "format": "remote_bulk",
       "bbox": [minx, miny, maxx, maxy],  # Merged bounding box (all resources)
       "crs": "4326",                      # Coordinate reference system
       "tbox": ["2020-01-01", "2023-12-31"],  # Merged temporal extent (all resources)
       "details": {
           "10.5281/zenodo.4593540": {
               "bbox": [...],              # Individual resource bbox (for diagnostics)
               "tbox": [...],
               "format": "remote",
               ...
           },
           "10.25532/OPARA-581": {
               "bbox": [...],              # Individual resource bbox (for diagnostics)
               ...
           }
       },
       "extraction_metadata": {
           "total_resources": 2,
           "successful": 2,
           "failed": 0
       }
   }

The primary result is the merged ``bbox`` at the top level, which combines all successfully extracted resources into a single bounding box (or convex hull if ``convex_hull=True``). Individual bounding boxes in ``details`` are retained for diagnostic purposes only.

For single identifier (string input):

.. code-block:: python

   {
       "format": "remote",
       "bbox": [minx, miny, maxx, maxy],
       "crs": "4326",
       "tbox": ["2020-01-01", "2023-12-31"],
       ...
   }

Extraction Metadata
-------------------

Geoextent automatically includes metadata about each extraction in the GeoJSON output. This metadata helps track what was processed and provides statistics about the extraction operation.

Metadata Structure
^^^^^^^^^^^^^^^^^^

The ``geoextent_extraction`` field is added to all GeoJSON FeatureCollection outputs (but not WKT or WKB formats). It contains:

- ``version``: The geoextent version used for the extraction
- ``inputs``: List of input files, directories, or remote resources processed
- ``statistics``: Processing statistics including:

  - ``files_processed``: Total number of files analyzed
  - ``files_with_extent``: Number of files with successfully extracted spatial extent
  - ``total_size``: Total size of processed files in human-readable format (e.g., "592.39 KiB", "1.5 MiB")

- ``format``: Format of the processed data (e.g., "geojson", "csv", "shapefile", "multiple_files")
- ``geoextent_handler``: Handler module used for processing (e.g., "handleVector", "handleCSV")
- ``crs``: Coordinate reference system (typically "4326" for WGS84)
- ``extent_type``: Type of extent extracted - "bounding_box", "convex_hull", or "point"

Suppressing Metadata
^^^^^^^^^^^^^^^^^^^^

Use the ``--no-metadata`` option to exclude extraction metadata from the output::

   python -m geoextent -b --no-metadata tests/testdata/geojson/muenster_ring.geojson

This produces minimal GeoJSON without the ``geoextent_extraction`` field.

Example Output
^^^^^^^^^^^^^^

Single file extraction::

   {
     "type": "FeatureCollection",
     "features": [
       {
         "type": "Feature",
         "geometry": {"type": "Polygon", "coordinates": [...]},
         "properties": {}
       }
     ],
     "geoextent_extraction": {
       "version": "0.9.0",
       "inputs": ["tests/testdata/geojson/muenster_ring.geojson"],
       "statistics": {
         "files_processed": 1,
         "files_with_extent": 1,
         "total_size": "1.7 KiB"
       },
       "format": "geojson",
       "geoextent_handler": "handleVector",
       "crs": "4326",
       "extent_type": "bounding_box"
     }
   }

Multiple files extraction::

   {
     "type": "FeatureCollection",
     "features": [
       {
         "type": "Feature",
         "geometry": {"type": "Polygon", "coordinates": [...]},
         "properties": {}
       }
     ],
     "geoextent_extraction": {
       "version": "0.9.0",
       "inputs": [
         "tests/testdata/geojson/muenster_ring.geojson",
         "tests/testdata/csv/cities_NL.csv"
       ],
       "statistics": {
         "files_processed": 2,
         "files_with_extent": 2,
         "total_size": "2.2 KiB"
       },
       "format": "multiple_files",
       "crs": "4326",
       "extent_type": "bounding_box"
     }
   }

Directory extraction::

   {
     "type": "FeatureCollection",
     "features": [
       {
         "type": "Feature",
         "geometry": {"type": "Polygon", "coordinates": [...]},
         "properties": {}
       }
     ],
     "geoextent_extraction": {
       "version": "0.9.0",
       "inputs": ["tests/testdata/geojson/"],
       "statistics": {
         "files_processed": 15,
         "files_with_extent": 14,
         "total_size": "45.1 KiB"
       },
       "format": "folder",
       "crs": "4326",
       "extent_type": "bounding_box"
     }
   }

Use Cases
^^^^^^^^^

The extraction metadata is useful for:

- **Reproducibility**: Track which version of geoextent was used
- **Provenance**: Document input sources for derived data
- **Quality assessment**: Identify incomplete extractions when ``files_with_extent`` < ``files_processed``
- **Batch processing**: Monitor processing statistics across multiple extractions
- **Research workflows**: Maintain complete records of data processing steps

The metadata is automatically included and requires no additional options or configuration.

Placename Lookup
----------------

Geoextent can automatically identify place names for extracted geographic areas using various gazetteer services. This feature adds meaningful location context to your spatial data extracts.

Basic Placename Usage
^^^^^^^^^^^^^^^^^^^^^

::

   # Add placename using default gazetteer (GeoNames)
   python -m geoextent -b --placename tests/testdata/geojson/muenster_ring.geojson

   # Specify a specific gazetteer service
   python -m geoextent -b --placename nominatim tests/testdata/shapefile/Abgrabungen_Kreis_Kleve_Shape.shp
   python -m geoextent -b --placename photon tests/testdata/geojson/ausgleichsflaechen_moers.geojson
   python -m geoextent -b --placename geonames tests/testdata/geopackage/nc.gpkg

   # Use placename with convex hull extraction
   python -m geoextent -b --convex-hull --placename nominatim tests/testdata/geojson/muenster_ring.geojson

   # Add placenames to repository extracts
   python -m geoextent -b --placename --max-download-size 1G 10.5880/GFZ.2.1.2020.001
   python -m geoextent -b --placename nominatim https://zenodo.org/record/4593540
   python -m geoextent -b --placename photon 10.1594/PANGAEA.734969

   # Use placename with Unicode escape sequences (for special characters)
   python -m geoextent -b --placename photon --placename-escape https://doi.org/10.3897/BDJ.13.e159973

Supported Gazetteer Services
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**GeoNames** (``geonames``)
  Comprehensive geographic database with global coverage. Requires free account registration at `geonames.org <https://www.geonames.org/login>`_. Set ``GEONAMES_USERNAME`` in your ``.env`` file. Most detailed results, best for scientific applications.

**Nominatim** (``nominatim``)
  OpenStreetMap-based geocoding service. No API key required. Good global coverage with detailed local information. Optionally set ``NOMINATIM_USER_AGENT`` in ``.env`` file.

**Photon** (``photon``)
  Fast OpenStreetMap-based geocoding. No API key required. Good performance for European locations. Optionally set ``PHOTON_DOMAIN`` in ``.env`` file for custom server.

Setting Up API Keys
^^^^^^^^^^^^^^^^^^^^

1. Copy the example environment file::

     cp .env.example .env

2. Edit ``.env`` file with your credentials::

     # For GeoNames (required for --placename geonames)
     GEONAMES_USERNAME=your_username_here

     # Optional: Custom user agent for Nominatim
     NOMINATIM_USER_AGENT=your_app_name/1.0

     # Optional: Custom Photon server
     PHOTON_DOMAIN=photon.komoot.io

3. Get a free GeoNames account at `geonames.org/login <https://www.geonames.org/login>`_

Example Output with Placename
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   {
     "type": "FeatureCollection",
     "features": [
       {
         "type": "Feature",
         "geometry": {
           "type": "Polygon",
           "coordinates": [[...]]
         },
         "properties": {
           "extent_type": "bounding_box",
           "format": "vector",
           "crs": "4326",
           "placename": "Münster, North Rhine-Westphalia, Germany"
         }
       }
     ]
   }

The placename appears in the GeoJSON output's feature properties, providing geographical context for the extracted extent.

Unicode Character Handling
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``--placename-escape`` option controls how Unicode characters are handled in placename output::

   # Normal output (default): "Chỗ chôn ông nội, Hải Phòng, Việt Nam"
   python -m geoextent -b --placename photon https://doi.org/10.3897/BDJ.13.e159973

   # Escaped output: "Ch\u1ed7 ch\xf4n \xf4ng n\u1ed9i, H\u1ea3i Ph\xf2ng, Vi\u1ec7t Nam"
   python -m geoextent -b --placename photon --placename-escape https://doi.org/10.3897/BDJ.13.e159973

The escaped format is useful for:

- Systems that don't handle Unicode well
- Data interchange with legacy applications
- Debugging character encoding issues

Download Size Limiting
----------------------

When extracting data from large research repositories, you can limit the total download size to control processing time and storage usage.

Basic Size Limiting
^^^^^^^^^^^^^^^^^^^

::

   # Limit total download across all files
   python -m geoextent -b --max-download-size 100MB https://doi.org/10.5281/zenodo.7080016
   python -m geoextent -b --max-download-size 1G 10.5880/GFZ.2.1.2020.001

   # Limit total download to 1000KB - download is not started
   python -m geoextent -b --max-download-size 1000KB https://doi.org/10.5281/zenodo.7080016

   # Limit to 50MB - useful for quick exploration
   python -m geoextent -b --max-download-size 50MB https://osf.io/4xe6z/

File Selection Methods
^^^^^^^^^^^^^^^^^^^^^^

The ``--max-download-method`` parameter controls how files are selected when the size limit is reached::

   # Ordered method (default): Select files in original order until limit reached
   python -m geoextent -b --max-download-size 100MB --max-download-method ordered https://doi.org/10.5281/zenodo.7080016

   # Random method: Randomly shuffle files before selection (useful for sampling)
   python -m geoextent -b --max-download-size 200MB --max-download-method random https://doi.org/10.5281/zenodo.7080016

   # Random with custom seed for reproducible results
   python -m geoextent -b --max-download-size 100MB --max-download-method random --max-download-method-seed 123 https://doi.org/10.5281/zenodo.7080016

Comparing Selection Methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Different selection methods can produce different spatial extents depending on the geographic distribution of files.

**Example with Zenodo European Land Use dataset** (https://doi.org/10.5281/zenodo.7080016)::

   # Ordered method (50MB limit) - selects first few countries alphabetically
   python -m geoextent -b --max-download-size 50MB --max-download-method ordered https://doi.org/10.5281/zenodo.7080016
   # Result: Covers Albania, Andorra, Austria, Belarus, Belgium (Western/Central Europe)
   # Bounding box: approximately [2.5°W to 30°E, 35°N to 60°N]

   # Random method (50MB limit, seed 42) - selects random geographic sample
   python -m geoextent -b --max-download-size 50MB --max-download-method random --max-download-method-seed 42 https://doi.org/10.5281/zenodo.7080016
   # Result: Covers Belgium, Liechtenstein, Luxembourg, Norway, Romania (scattered across Europe)
   # Bounding box: approximately [5°W to 30°E, 40°N to 75°N] - larger extent due to Norway

**Key Observations:**

- **Ordered method**: Predictable but may be geographically biased (alphabetical selection often clusters regions)
- **Random method**: Better geographic sampling but results vary with different seeds
- **Larger random samples**: Often produce more representative spatial extents
- **Shapefile preservation**: Related files (.shp, .shx, .dbf, .prj) always stay together as a unit

Size Limiting Behavior
^^^^^^^^^^^^^^^^^^^^^^^

The limit applies to the cumulative total of all selected files. Files are selected until adding the next file would exceed the limit.

Example: With files of sizes [10MB, 15MB, 8MB, 12MB] and 20MB limit:

- Ordered: Selects 10MB file only (10MB total) - next file would exceed 20MB
- The 15MB file is skipped because 10MB + 15MB = 25MB > 20MB limit

Shapefile components are kept together as a single unit. If a shapefile's total size (.shp + .shx + .dbf + .prj) fits within remaining space, all components are selected together. Otherwise, all are skipped together.

Advanced Examples
^^^^^^^^^^^^^^^^^

::

   # Combine size limiting with other options
   python -m geoextent -b -t --max-download-size 200MB --convex-hull --geojsonio https://doi.org/10.5281/zenodo.7080016

   # Use size limiting for quick dataset exploration
   python -m geoextent -b --max-download-size 10MB --max-download-method random https://osf.io/4xe6z/

**Note**: When no size limit is specified, all available files are downloaded and processed.

Performance and Filtering Options
----------------------------------

Parallel Downloads
^^^^^^^^^^^^^^^^^^

Control download performance using parallel workers for faster processing of multi-file datasets::

   # Use 8 parallel download workers for faster downloads
   python -m geoextent -b --max-download-workers 8 https://doi.org/10.5281/zenodo.7080016

   # Disable parallel downloads (use sequential, slower but more conservative)
   python -m geoextent -b --max-download-workers 1 https://osf.io/4xe6z/

   # Default is 4 workers - good balance of speed and server politeness
   python -m geoextent -b https://doi.org/10.5281/zenodo.7080016

File Type Filtering
^^^^^^^^^^^^^^^^^^^

Skip non-geospatial files during download to save time and bandwidth::

   # Skip non-geospatial files (PDFs, images, text files, etc.)
   python -m geoextent -b --download-skip-nogeo https://doi.org/10.5281/zenodo.7080016

   # Include additional file types as geospatial (point clouds, mesh files)
   python -m geoextent -b --download-skip-nogeo --download-skip-nogeo-exts ".xyz,.las,.ply" https://osf.io/4xe6z/

   # Combine filtering with size limits and parallel downloads
   python -m geoextent -b --download-skip-nogeo --max-download-size 100MB --max-download-workers 6 https://doi.org/10.5281/zenodo.7080016

   # OSF filtering examples
   python -m geoextent -b --download-skip-nogeo https://osf.io/4xe6z/
   python -m geoextent -b --download-skip-nogeo --max-download-size 50MB https://doi.org/10.17605/OSF.IO/9JG2U

   # Dryad filtering examples - intelligently chooses individual file downloads
   python -m geoextent -b --download-skip-nogeo https://datadryad.org/dataset/doi:10.5061/dryad.0k6djhb7x
   python -m geoextent -b --download-skip-nogeo --max-download-size 10MB https://datadryad.org/dataset/doi:10.5061/dryad.wm37pvmvf

**File Type Detection**: Geospatial files are automatically detected based on extensions including: ``.geojson``, ``.csv``, ``.shp``, ``.tif``, ``.gpkg``, ``.gpx``, ``.gml``, ``.kml``, ``.fgb``, and others. Use ``--download-skip-nogeo-exts`` to add custom extensions.

**Provider Support**: File filtering is fully supported by Figshare, Zenodo, OSF, and Dryad. Other providers (PANGAEA, GFZ, Dataverse, Pensoft) will show warnings when filtering is requested but will continue with their standard download behavior.

Output Format Options
---------------------

geoextent supports multiple output formats for spatial extents to facilitate integration with different programming languages and tools.

Supported Formats
^^^^^^^^^^^^^^^^^

::

   # Default GeoJSON format (geographic coordinates as polygon)
   python -m geoextent -b tests/testdata/geojson/muenster_ring_zeit.geojson
   python -m geoextent -b --format geojson tests/testdata/geojson/muenster_ring_zeit.geojson

   # Well-Known Text (WKT) format
   python -m geoextent -b --format wkt tests/testdata/geojson/muenster_ring_zeit.geojson

   # Well-Known Binary (WKB) format as hex string
   python -m geoextent -b --format wkb tests/testdata/geojson/muenster_ring_zeit.geojson

Format Details
^^^^^^^^^^^^^^

**GeoJSON** (default)
  Returns spatial extent as a GeoJSON Polygon geometry with coordinate arrays

**WKT**
  Returns spatial extent as `Well-Known Text <https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry>`_ POLYGON string, easily parsed by PostGIS, GDAL, and other geospatial tools

**WKB**
  Returns spatial extent as `Well-Known Binary <https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry#Well-known_binary>`_ hexadecimal string, compact binary format for database storage

An easy way to verify these outputs is the `online WKB viewer/converter <https://wkbrew.tszheichoi.com/>`_.

Interactive Visualization
-------------------------

Open extracted spatial extents in geojson.io for interactive visualization and editing.

Generate URL
^^^^^^^^^^^^

Use ``--geojsonio`` to generate a clickable geojson.io URL::

   python -m geoextent -b --geojsonio tests/testdata/geojson/muenster_ring.geojson

This prints the URL after the JSON output.

Open in Browser
^^^^^^^^^^^^^^^

Use ``--browse`` to automatically open the visualization in your default web browser::

   python -m geoextent -b --browse tests/testdata/geojson/muenster_ring.geojson

This opens the browser without printing the URL. To both print the URL to the console and open it in the browser, use both ``--geojsonio`` and ``--browse``::

   python -m geoextent -b --geojsonio --browse tests/testdata/geojson/muenster_ring.geojson

Works with Remote Repositories
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   # Open Zenodo data visualization in browser
   python -m geoextent -b --browse https://doi.org/10.5281/zenodo.4593540

   # Combine with other options
   python -m geoextent -b --convex-hull --browse --quiet https://doi.org/10.1594/PANGAEA.734969

Quiet Mode
----------

Use the ``--quiet`` option to suppress all console messages including warnings and progress bars. This is particularly useful for scripting, automation, or when you only want the final result.

Basic Usage
^^^^^^^^^^^

::

   # Normal output (shows progress bars and warnings)
   python -m geoextent -b tests/testdata/geojson/
   # Output: Progress bars, warnings, and result

   # Quiet mode (clean output, no progress or warnings)
   python -m geoextent -b --quiet tests/testdata/geojson/
   # Output: Only the final result

   # Quiet mode with specific format
   python -m geoextent -b --format wkt --quiet tests/testdata/geojson/
   # Output: POLYGON((6.220493316650391 50.52150360276628,...))

Scripting Examples
^^^^^^^^^^^^^^^^^^

Perfect for shell scripts and pipelines::

   # Capture output in variable
   BBOX=$(python -m geoextent -b --format wkt --quiet tests/testdata/geojson/muenster_ring_zeit.geojson)
   echo "Bounding box: $BBOX"

R Integration
^^^^^^^^^^^^^

You can call geoextent from within R scripts using the ``system2()`` function, in combination with WKT format for creating R objects easily::

   sf::st_as_sfc(
     system2("geoextent",
       c("-b", "--format", "wkt", "--quiet", "tests/testdata/geojson"),
       stdout=TRUE)
     )

Repository Extraction Options
-----------------------------

When extracting geospatial data from research repositories, geoextent supports two extraction modes.

Default Mode: Data Download (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, geoextent downloads actual data files from repositories and processes them locally using GDAL. This provides the most accurate and comprehensive geospatial extent extraction::

   # Default behavior - downloads and processes actual data files
   python -m geoextent -b -t https://doi.org/10.1594/PANGAEA.786028
   python -m geoextent -b -t 10.5281/zenodo.654321
   python -m geoextent -b -t https://osf.io/4xe6z

   # GFZ Data Services examples
   python -m geoextent -b -t 10.5880/GFZ.2.1.2020.001
   python -m geoextent -b -t 10.5880/GFZ.4.8.2023.004

Metadata-Only Mode (Limited)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use the ``--no-download-data`` flag to extract information from repository metadata only, without downloading actual files. This is faster but may result in incomplete or missing spatial/temporal extents, especially for providers like Zenodo, Figshare, Dryad, and OSF that don't include detailed geospatial metadata::

   # Metadata-only extraction (not recommended for most use cases)
   python -m geoextent -b -t --no-download-data https://doi.org/10.1594/PANGAEA.786028

.. note::
   PANGAEA datasets often include rich geospatial metadata, but for best results and compatibility with all providers, the default data download mode is recommended.

Convex Hull vs Bounding Box
----------------------------

By default, geoextent extracts a rectangular bounding box. For vector data, you can extract a more precise convex hull that better represents the actual spatial extent.

Basic Usage
^^^^^^^^^^^

::

   # Default bounding box extraction
   python -m geoextent -b tests/testdata/geojson/muenster_ring.geojson

   # Convex hull extraction (more precise for vector data)
   python -m geoextent -b --convex-hull tests/testdata/geojson/muenster_ring.geojson

When to Use Convex Hull
^^^^^^^^^^^^^^^^^^^^^^^^

**Use convex hull when:**

- You have vector data with complex or irregular shapes
- You need a more accurate representation of the actual data coverage
- You're working with point data that doesn't fill a rectangular area
- The bounding box would include large areas with no data

**Use bounding box when:**

- You need a simple rectangular extent
- You're working with raster data (convex hull not applicable)
- You need maximum performance (bounding box is faster)
- You need compatibility with systems that only accept rectangular extents

Combining with Other Features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   # Convex hull with placename lookup
   python -m geoextent -b --convex-hull --placename nominatim tests/testdata/geojson/muenster_ring.geojson

   # Convex hull with WKT output format
   python -m geoextent -b --convex-hull --format wkt tests/testdata/geojson/muenster_ring.geojson

   # Convex hull from repository data
   python -m geoextent -b --convex-hull --max-download-size 100MB https://doi.org/10.5281/zenodo.4593540
