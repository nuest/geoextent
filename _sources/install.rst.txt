
Installing geoextent
====================

geoextent requires Python 3.10+ and GDAL 3.11.x. It supports Linux, macOS, and Windows.

System Requirements
-------------------

**Python:** 3.10 or later

**GDAL:** 3.11.x

The package relies on common system libraries for reading geospatial datasets, such as GDAL and NetCDF.
On Debian systems, the `UbuntuGIS <https://wiki.ubuntu.com/UbuntuGIS>`_ project offers easy installation of up to date versions of those libraries.

Ubuntu/Debian Installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install system dependencies:

::

   sudo add-apt-repository ppa:ubuntugis/ubuntugis-unstable
   sudo apt-get update
   sudo apt-get install -y libproj-dev libgeos-dev libspatialite-dev libgdal-dev gdal-bin netcdf-bin

Verify GDAL installation:

::

   gdal-config --version

Installing with pip
-------------------

Recommended installation using virtual environment:

::

   python -m venv .venv
   source .venv/bin/activate

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
