Core Features
=============

This page covers fundamental geoextent capabilities used in everyday workflows.

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

Supported Parameters
^^^^^^^^^^^^^^^^^^^^

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

See :doc:`providers` for details on all supported repositories.

Output Formats
--------------

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

See Also
--------

- :doc:`quickstart` - Quick introduction to basic usage
- :doc:`examples` - Detailed examples for common tasks
- :doc:`advanced-features` - Specialized options and performance tuning
- :doc:`providers` - Repository provider details
- :doc:`howto/cli` - Complete CLI reference
- :doc:`howto/api` - Python API documentation
