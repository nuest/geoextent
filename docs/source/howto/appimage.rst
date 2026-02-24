AppImage Usage
==============

An AppImage is available for Linux that bundles geoextent with Python, GDAL, PROJ, and all dependencies into a single portable executable. No installation or system dependencies required — just download and run.

Downloading the AppImage
------------------------

Download the latest AppImage from the `GitHub Releases page <https://github.com/nuest/geoextent/releases>`_:

::

   # Download (replace VERSION and URL with the latest release)
   wget https://github.com/nuest/geoextent/releases/download/vVERSION/geoextent-VERSION-x86_64.AppImage

   # Make executable
   chmod +x geoextent-*-x86_64.AppImage

Or using curl:

::

   curl -fSL -o geoextent.AppImage https://github.com/nuest/geoextent/releases/download/vVERSION/geoextent-VERSION-x86_64.AppImage
   chmod +x geoextent.AppImage

.. tip::
   You can rename the AppImage to ``geoextent`` and place it on your ``PATH`` for convenient usage:

   ::

      mv geoextent-*-x86_64.AppImage ~/.local/bin/geoextent

Basic Usage
-----------

The AppImage works exactly like the regular ``geoextent`` CLI::

   # Show help
   ./geoextent-*-x86_64.AppImage --help

   # Show version
   ./geoextent-*-x86_64.AppImage --version

   # Show supported formats
   ./geoextent-*-x86_64.AppImage --formats

Local File Processing
---------------------

Process local files directly — no volume mounts or path translation needed::

   # Extract bounding box from a GeoTIFF
   ./geoextent-*-x86_64.AppImage -b data/raster.tif

   # Extract both spatial and temporal extent from GeoJSON
   ./geoextent-*-x86_64.AppImage -b -t data/muenster_ring_zeit.geojson

   # Extract bounding box from a CSV with coordinate columns
   ./geoextent-*-x86_64.AppImage -b data/cities.csv

   # Process a directory of geospatial files
   ./geoextent-*-x86_64.AppImage -b -t data/

   # Extract convex hull instead of bounding box
   ./geoextent-*-x86_64.AppImage -b --convex-hull data/

Remote Repository Processing
-----------------------------

Extract geospatial extent from research repositories using DOIs or URLs::

   # Extract from Zenodo
   ./geoextent-*-x86_64.AppImage -b https://doi.org/10.5281/zenodo.4593540

   # Extract from PANGAEA with temporal extent
   ./geoextent-*-x86_64.AppImage -b -t https://doi.org/10.1594/PANGAEA.734969

   # Extract from OSF with size limiting
   ./geoextent-*-x86_64.AppImage -b --max-download-size 50MB https://osf.io/4xe6z/

   # Extract from a GitHub repository
   ./geoextent-*-x86_64.AppImage -b https://github.com/user/repo

Output Formats
--------------

::

   # GeoJSON output (default)
   ./geoextent-*-x86_64.AppImage -b data/file.geojson

   # WKT output for PostGIS/GDAL
   ./geoextent-*-x86_64.AppImage -b --format wkt data/file.geojson

   # WKB output for database storage
   ./geoextent-*-x86_64.AppImage -b --format wkb data/file.geojson

   # Export results to a file
   ./geoextent-*-x86_64.AppImage -b -t --output results.gpkg data/

AppImage vs CLI Equivalence
----------------------------

The AppImage is a drop-in replacement for ``python -m geoextent``:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - CLI Command
     - AppImage Equivalent
   * - ``python -m geoextent --help``
     - ``./geoextent.AppImage --help``
   * - ``python -m geoextent -b file.geojson``
     - ``./geoextent.AppImage -b file.geojson``
   * - ``python -m geoextent -b -t directory/``
     - ``./geoextent.AppImage -b -t directory/``
   * - ``python -m geoextent -b https://doi.org/...``
     - ``./geoextent.AppImage -b https://doi.org/...``

Scripting with the AppImage
----------------------------

::

   #!/bin/bash
   # Process multiple repositories
   GEOEXTENT="./geoextent-x86_64.AppImage"

   REPOSITORIES=(
     "https://doi.org/10.5281/zenodo.4593540"
     "https://doi.org/10.1594/PANGAEA.734969"
   )

   for repo in "${REPOSITORIES[@]}"; do
     echo "Processing: $repo"
     $GEOEXTENT -b --quiet "$repo"
   done

Capture output in a variable::

   BBOX=$(./geoextent.AppImage -b --format wkt --quiet data/file.geojson)
   echo "Bounding box: $BBOX"

Environment Variables
---------------------

The AppImage bundles its own GDAL, PROJ, and Python, so you do **not** need to set ``GDAL_DATA``, ``PROJ_DATA``, or ``PYTHONHOME``. These are configured automatically inside the AppImage.

For placename lookup, pass API keys as usual::

   GEONAMES_USERNAME=your_username ./geoextent.AppImage -b --placename data/file.geojson

Building the AppImage Locally
------------------------------

If a pre-built AppImage is not available for your needs (e.g., you want to package a development version), you can build it yourself on any Linux x86_64 system:

::

   git clone https://github.com/nuest/geoextent
   cd geoextent
   bash scripts/build-appimage.sh

The build script downloads Miniforge and appimagetool automatically (cached for subsequent builds). The resulting AppImage is written to the project root directory.

Requirements:

- Linux x86_64
- ~2 GB disk space during build
- Internet access (first run)
- bash, curl

You can set the version explicitly::

   GEOEXTENT_VERSION=0.13.0 bash scripts/build-appimage.sh

See ``scripts/build-appimage.sh`` for all options.

Troubleshooting
---------------

FUSE not available
^^^^^^^^^^^^^^^^^^

Some systems (containers, older kernels) lack FUSE support. Use the ``--appimage-extract-and-run`` flag::

   ./geoextent.AppImage --appimage-extract-and-run -b data/file.geojson

Or extract the AppImage once and run directly::

   ./geoextent.AppImage --appimage-extract
   ./squashfs-root/AppRun -b data/file.geojson

SSL certificate errors
^^^^^^^^^^^^^^^^^^^^^^

The AppImage bundles its own CA certificates. If you encounter SSL errors (e.g., behind a corporate proxy), set the ``SSL_CERT_FILE`` environment variable to your system certificates::

   SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt ./geoextent.AppImage -b https://doi.org/...

Glibc compatibility
^^^^^^^^^^^^^^^^^^^

The AppImage is built on Ubuntu 22.04 (glibc 2.35). It should work on most Linux distributions from 2022 onwards. If you get a glibc error, your system is too old to run this AppImage.

Extracting the AppImage contents
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To inspect what's inside the AppImage::

   ./geoextent.AppImage --appimage-extract
   ls squashfs-root/
