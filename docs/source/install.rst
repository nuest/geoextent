
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
   Windows support is tested in CI using the conda-forge approach described below (see ``.github/workflows/pythonpackage.yml`` for the exact setup).  If you encounter issues, please report them on the `issue tracker <https://github.com/nuest/geoextent/issues>`_.

GDAL has no official PyPI wheels for Windows, so ``pip install gdal`` will fail. Use one of these approaches instead:

**Option 1: Miniforge + conda-forge** (recommended)

This is the approach used by the geoextent CI and is the most reliable method on Windows.

1. Install `Miniforge <https://github.com/conda-forge/miniforge#miniforge3>`_ (provides conda with conda-forge as the default channel).

2. Open the Miniforge Prompt and create an environment:

::

   conda create -n geoextent python=3.12
   conda activate geoextent

3. Install GDAL and system dependencies via conda:

::

   conda install -y gdal libgdal libspatialite netcdf4 proj

4. Install geoextent **without dependency resolution** (to avoid pip trying to install GDAL from PyPI):

::

   pip install --no-deps geoextent

5. Install the remaining runtime dependencies via pip:

::

   pip install pyproj "geojson>=2.4.1" geojsonio pygeoj pyshp ^
     patool python-dateutil pandas "numpy<2" requests traitlets ^
     wheel pangaeapy osfclient filesizelib "setuptools-scm>=8" ^
     tqdm bs4 geopy python-dotenv humanfriendly crossref-commons ^
     datacite owslib

6. Verify the installation:

::

   python -c "from osgeo import gdal; print(f'GDAL {gdal.VersionInfo()}')"
   python -m geoextent --version

.. tip::
   **Long file paths:** Some operations (archive extraction with temporary directories) may exceed the Windows 260-character path limit.  Enable long paths via PowerShell (run as Administrator):

   .. code-block:: powershell

      New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
        -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force

.. tip::
   **Archive extraction:** geoextent uses ``patool`` for archive extraction.  On Windows, patool relies on `7-Zip <https://www.7-zip.org/>`_ being installed and available on the ``PATH``.  7-Zip is pre-installed on most Windows CI runners, but you may need to install it manually on your system.

**Option 2: Docker**

Use the Docker installation to avoid system dependency issues entirely. See the Docker Installation section below.

**Option 3: OSGeo4W**

Install OSGeo4W from https://trac.osgeo.org/osgeo4w/ for a complete geospatial stack on Windows.  After installation, use the OSGeo4W shell to run pip and geoextent.

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

Installing with uv
-------------------

`uv <https://docs.astral.sh/uv/>`_ is a fast Python package manager that can replace pip and venv. It handles virtual environments automatically and resolves dependencies significantly faster than pip.

::

   # Create a venv and install GDAL + geoextent
   GDAL_VERSION=$(gdal-config --version)
   uv venv .venv
   uv pip install "GDAL==$GDAL_VERSION" geoextent

   # Activate and use
   source .venv/bin/activate
   geoextent -b file.geojson

To install geoextent as a CLI tool (similar to pipx):

::

   GDAL_VERSION=$(gdal-config --version)
   uv tool install geoextent --with "gdal==$GDAL_VERSION"

   # Now available globally
   geoextent -b file.geojson

.. note::
   The ``--with "gdal==..."`` flag is required because uv's dependency resolver would otherwise install the latest GDAL Python bindings from PyPI, which may not match the system GDAL library.

Installing with conda / mamba
------------------------------

`conda <https://docs.conda.io/>`_ and `mamba <https://mamba.readthedocs.io/>`_ (a faster drop-in replacement for conda) can install GDAL and its Python bindings together from conda-forge, avoiding version mismatch issues entirely. This is particularly useful on **Windows** and **macOS** where system GDAL installation can be more involved.

::

   # Create environment (use 'mamba' instead of 'conda' for faster resolution)
   conda create -n geoextent python=3.12 -y
   conda activate geoextent

   # Install GDAL from conda-forge (includes matching Python bindings)
   conda install -c conda-forge gdal -y

   # Install geoextent via pip
   pip install geoextent

.. note::
   Always activate the conda environment (``conda activate geoextent``) before running geoextent. This sets environment variables like ``PROJ_DATA`` that GDAL needs for coordinate transformations.

Installing with Poetry
-----------------------

`Poetry <https://python-poetry.org/>`_ manages Python dependencies with a lockfile for reproducible installs. Because Poetry resolves all dependencies together, you must pin the GDAL version to match your system:

::

   poetry init --no-interaction
   poetry add "gdal==$(gdal-config --version)" geoextent
   poetry run geoextent -b file.geojson

Without the explicit GDAL version pin, Poetry will resolve to the latest GDAL on PyPI, which will fail to build if it does not match the system GDAL library.

Installing with pipx
---------------------

`pipx <https://pipx.pypa.io/>`_ installs Python CLI tools in isolated environments. Use ``--preinstall`` to install the correct GDAL bindings before geoextent:

::

   GDAL_VERSION=$(gdal-config --version)
   pipx install geoextent --preinstall "gdal==$GDAL_VERSION"

   # Now available globally
   geoextent -b file.geojson

.. note::
   A plain ``pipx install geoextent`` will fail because pipx resolves to the latest GDAL on PyPI. The ``--preinstall`` flag ensures the correct GDAL version is installed first.

Optional Extras
----------------

Install optional feature groups as needed:

::

   # Map preview (--map and --preview CLI flags)
   pip install geoextent[preview]

   # Development tools
   pip install geoextent[dev]

   # Testing
   pip install geoextent[test]

   # Documentation building
   pip install geoextent[docs]

Development Installation
------------------------

For development, install with additional dependencies:

::

   git clone https://github.com/nuest/geoextent
   cd geoextent

   # Install in development mode with all dependencies
   pip install -e .[dev,test,docs,preview]

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

1. Using Miniforge + conda-forge (see the Windows Installation section above for step-by-step instructions)
2. Or using the Docker installation for the easiest setup
