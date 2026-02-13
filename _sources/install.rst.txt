
Installing geoextent
====================

geoextent requires Python 3.10+ and GDAL 3.11.x. It supports Linux, macOS, and Windows.

System Requirements
-------------------

**Python:** 3.10 or later

**GDAL:** 3.11.x

The package relies on common system libraries for reading geospatial datasets:

- **GDAL/OGR** - Core library for reading raster and vector formats
- **PROJ** - Coordinate transformation library
- **GEOS** - Geometric operations library
- **libspatialite** - Spatial database support
- **NetCDF** - Climate and atmospheric data format support

Ubuntu/Debian Installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^

On Debian-based systems, the `UbuntuGIS <https://wiki.ubuntu.com/UbuntuGIS>`_ project provides up-to-date versions of geospatial libraries.

Install system dependencies:

::

   sudo add-apt-repository ppa:ubuntugis/ubuntugis-unstable
   sudo apt-get update
   sudo apt-get install -y libproj-dev libgeos-dev libspatialite-dev libgdal-dev gdal-bin netcdf-bin

Verify GDAL installation:

::

   gdal-config --version

macOS Installation
^^^^^^^^^^^^^^^^^^

.. note::
   These macOS installation instructions are provided by the community and have not been extensively tested by the geoextent developers. If you encounter issues, please report them on the `issue tracker <https://github.com/nuest/geoextent/issues>`_.

Install system dependencies using Homebrew:

::

   brew install gdal

Verify GDAL installation:

::

   gdal-config --version

Windows Installation
^^^^^^^^^^^^^^^^^^^^

.. note::
   These Windows installation instructions are provided by the community and have not been extensively tested by the geoextent developers. We recommend using Docker (Option 1) for the most reliable experience on Windows. If you encounter issues with other methods, please report them on the `issue tracker <https://github.com/nuest/geoextent/issues>`_.

For Windows, we recommend using one of these approaches:

**Option 1: Docker** (recommended)

Use the Docker installation to avoid system dependency issues. See :doc:`howto/docker` for details.

**Option 2: Conda**

Use conda-forge which handles system dependencies automatically:

::

   conda install -c conda-forge gdal

**Option 3: OSGeo4W**

Install OSGeo4W from https://trac.osgeo.org/osgeo4w/ for a complete geospatial stack on Windows.

Installing GDAL Python Bindings
--------------------------------

After installing system GDAL, install the matching Python bindings:

::

   # Get your system GDAL version
   GDAL_VERSION=$(gdal-config --version)
   echo "System GDAL version: $GDAL_VERSION"

   # Install matching Python bindings
   pip install "GDAL==$GDAL_VERSION"

If the exact version is not available on PyPI, try the nearest compatible version:

::

   pip install "GDAL>=3.11.0,<3.12.0"

Installing with pip
-------------------

Recommended installation using virtual environment:

::

   python -m venv .venv
   source .venv/bin/activate

   # Install GDAL Python bindings first (see above)
   GDAL_VERSION=$(gdal-config --version)
   pip install "GDAL==$GDAL_VERSION"

   # Then install geoextent
   pip install geoextent

Development Installation
------------------------

For development, install with additional dependencies:

::

   git clone https://github.com/nuest/geoextent
   cd geoextent

   # Install in development mode with all dependencies
   pip install -e .[dev,test,docs]

Docker Installation
-------------------

Use the official Docker image:

::

   # Pull the image
   docker pull geoextent

   # Or build locally
   docker build -t geoextent .

**Docker Usage Examples:**

Process remote repositories:

::

   docker run --rm geoextent -b https://doi.org/10.5281/zenodo.4593540

Process local files (mount your data directory):

::

   docker run --rm -v /path/to/your/data:/data geoextent -b /data/file.geojson

Multiple files:

::

   docker run --rm -v /path/to/your/data:/data geoextent -b /data/*.shp

Directories:

::

   docker run --rm -v /path/to/your/data:/data geoextent -b /data/geojson/

With placename lookup (requires .env file):

::

   docker run --rm --env-file .env -v /path/to/your/data:/data geoextent -b --placename /data/file.geojson

Verification
------------

Test your installation:

::

   python -m geoextent --version

   # Test with a small example
   python -m geoextent -b https://doi.org/10.1594/PANGAEA.734969

Troubleshooting
---------------

**Import Errors**

If you encounter GDAL-related import errors:

1. Ensure GDAL is properly installed on your system
2. Check that your Python environment can find the GDAL libraries
3. On Ubuntu/Debian, make sure you have both ``libgdal-dev`` and ``gdal-bin`` installed

**Version Conflicts**

If you have conflicting GDAL versions:

1. Use a fresh virtual environment
2. Ensure system GDAL version matches the Python bindings
3. Consider using the Docker installation to avoid system conflicts

**Windows Installation**

For Windows users, we recommend:

1. Using the Docker installation for the easiest setup
2. Or installing via conda-forge which handles system dependencies
