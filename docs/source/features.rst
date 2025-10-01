Advanced Features
==================

This page documents advanced features and options available in geoextent for specialized use cases.

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
