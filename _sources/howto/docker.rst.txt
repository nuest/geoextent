Docker Usage
============

A Docker image is available for easy deployment without managing dependencies. The Docker container is functionally equivalent to the CLI, making it easy to use geoextent in containerized environments.

Building the Docker Image
--------------------------

::

   # Build the Docker image
   docker build -t geoextent .

Basic Docker Usage
------------------

Run geoextent using Docker with the same options as the CLI::

   # Show help
   docker run --rm geoextent --help

   # Extract bounding box from a file
   docker run --rm -v $(pwd):/data geoextent -b /data/file.geojson

   # Extract both spatial and temporal extents
   docker run --rm -v $(pwd)/tests/testdata/shapefile:/data geoextent -b -t /data/ifgi_denkpause.shp

Local File Processing
---------------------

When working with local files, mount your data directory using ``-v``::

   # Extract bounding box from local GeoJSON file
   docker run --rm -v $(pwd)/tests/testdata/geojson:/data geoextent -b /data/muenster_ring.geojson

   # Extract convex hull from a local directory
   docker run --rm -v $(pwd)/tests/testdata/geojson:/data geoextent -b --convex-hull /data

   # Extract with GeoJSON.io link for visualization
   docker run --rm -v $(pwd)/tests/testdata/shapefile:/data geoextent -b -t --geojsonio /data/ifgi_denkpause.shp

   # Output in WKT format
   docker run --rm -v $(pwd)/tests/testdata/geojson:/data geoextent -b --format wkt /data

Remote Repository Processing
-----------------------------

For remote repositories, no local data mount is needed::

   # Extract from Zenodo
   docker run --rm geoextent -b https://doi.org/10.5281/zenodo.4593540

   # Extract from PANGAEA with temporal extent
   docker run --rm geoextent -b -t https://doi.org/10.1594/PANGAEA.734969

   # Extract from OSF with size limiting
   docker run --rm geoextent -b --max-download-size 50MB https://osf.io/4xe6z/

   # Combine with quiet mode for clean output
   docker run --rm geoextent -b --max-download-size 10MB --quiet https://doi.org/10.5281/zenodo.10731546

Placename Lookup with Docker
-----------------------------

When using placename lookup, pass environment variables using ``--env-file`` or ``-e``::

   # Use environment file for API keys
   docker run --rm --env-file .env geoextent -b --placename https://doi.org/10.5281/zenodo.3446746

   # Pass environment variable directly
   docker run --rm -e GEONAMES_USERNAME=your_username geoextent -b --placename geonames /data/file.geojson

   # Nominatim doesn't require API key
   docker run --rm -v $(pwd):/data geoextent -b --placename nominatim /data/file.shp

Advanced Docker Features
------------------------

Size Limiting and Filtering
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   # Limit download size
   docker run --rm geoextent -b --max-download-size 100MB https://doi.org/10.5281/zenodo.7080016

   # Skip non-geospatial files
   docker run --rm geoextent -b --download-skip-nogeo https://doi.org/10.5281/zenodo.7080016

   # Combine multiple options
   docker run --rm geoextent -b --max-download-size 50MB --download-skip-nogeo --quiet https://osf.io/4xe6z/

Parallel Downloads
^^^^^^^^^^^^^^^^^^

::

   # Use 8 parallel workers for faster downloads
   docker run --rm geoextent -b --max-download-workers 8 https://doi.org/10.5281/zenodo.7080016

Output Formats
^^^^^^^^^^^^^^

::

   # GeoJSON output (default)
   docker run --rm geoextent -b https://doi.org/10.5281/zenodo.4593540

   # WKT output for PostGIS/GDAL
   docker run --rm geoextent -b --format wkt https://doi.org/10.5281/zenodo.4593540

   # WKB output for database storage
   docker run --rm geoextent -b --format wkb https://doi.org/10.5281/zenodo.4593540

Docker vs CLI Equivalence
--------------------------

The Docker container is designed to be a drop-in replacement for the CLI:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - CLI Command
     - Docker Equivalent
   * - ``python -m geoextent --help``
     - ``docker run --rm geoextent --help``
   * - ``python -m geoextent -b file.geojson``
     - ``docker run --rm -v $(pwd):/data geoextent -b /data/file.geojson``
   * - ``python -m geoextent -b -t directory/``
     - ``docker run --rm -v $(pwd):/data geoextent -b -t /data/directory/``
   * - ``python -m geoextent -b --placename file.shp``
     - ``docker run --rm --env-file .env -v $(pwd):/data geoextent -b --placename /data/file.shp``
   * - ``python -m geoextent -b https://doi.org/10.5281/zenodo.4593540``
     - ``docker run --rm geoextent -b https://doi.org/10.5281/zenodo.4593540``

Key Docker Usage Notes
----------------------

**Data mounting**
  Use ``-v /host/path:/data`` to mount your local data directory. Files inside the container are referenced relative to ``/data``.

**Environment variables**
  Use ``--env-file .env`` or ``-e VARIABLE=value`` for API keys (GeoNames, Nominatim, Photon).

**Working directory**
  The container's working directory is ``/data``, so reference files relative to this path.

**Output**
  Results are printed to stdout, same as the CLI. Use ``--quiet`` for clean output without progress bars.

**Permissions**
  The container runs as non-root user ``geoextent`` (UID 1000) for security.

**Remove container**
  Use ``--rm`` flag to automatically remove the container after execution.

Scripting with Docker
---------------------

Shell Script Example
^^^^^^^^^^^^^^^^^^^^

::

   #!/bin/bash
   # Process multiple repositories with Docker

   REPOSITORIES=(
     "https://doi.org/10.5281/zenodo.4593540"
     "https://doi.org/10.1594/PANGAEA.734969"
     "https://osf.io/4xe6z/"
   )

   for repo in "${REPOSITORIES[@]}"; do
     echo "Processing: $repo"
     docker run --rm geoextent -b --quiet "$repo"
   done

Capture Output
^^^^^^^^^^^^^^

::

   # Capture WKT output in variable
   BBOX=$(docker run --rm geoextent -b --format wkt --quiet https://doi.org/10.5281/zenodo.4593540)
   echo "Bounding box: $BBOX"

Docker Compose Example
^^^^^^^^^^^^^^^^^^^^^^

For integration with other services, use Docker Compose::

   version: '3.8'
   services:
     geoextent:
       build: .
       volumes:
         - ./data:/data
       env_file:
         - .env
       command: -b -t /data

Troubleshooting
---------------

Permission Issues
^^^^^^^^^^^^^^^^^

If you encounter permission issues with mounted volumes::

   # Run with current user UID/GID
   docker run --rm --user $(id -u):$(id -g) -v $(pwd):/data geoextent -b /data/file.geojson

Volume Mount Not Working
^^^^^^^^^^^^^^^^^^^^^^^^^

Ensure you're using absolute paths or ``$(pwd)`` for current directory::

   # Wrong: relative path may not work
   docker run --rm -v ./data:/data geoextent -b /data/file.geojson

   # Correct: absolute path or $(pwd)
   docker run --rm -v $(pwd)/data:/data geoextent -b /data/file.geojson

API Keys Not Working
^^^^^^^^^^^^^^^^^^^^

Make sure your ``.env`` file is in the current directory and properly formatted::

   # Check .env file exists
   ls -la .env

   # Verify environment variables are passed
   docker run --rm --env-file .env geoextent -b --placename geonames /data/file.geojson
