Development
===========

Notes for developers of ``geoextent``.

Environment
-----------

All commands in this file assume you work in a Python virtual environment. We recommend using Python's built-in ``venv`` module:

::

    # Create a virtual environment
    python -m venv .venv

    # Activate the environment (Linux/macOS)
    source .venv/bin/activate

    # Activate the environment (Windows)
    .venv\Scripts\activate

    # Deactivate the environment
    deactivate

    # Remove the environment (if needed)
    rm -rf .venv

Required packages
-----------------

System Dependencies
^^^^^^^^^^^^^^^^^^^

First, ensure you have the required system packages installed. On Debian/Ubuntu:

::

    sudo add-apt-repository ppa:ubuntugis/ubuntugis-unstable
    sudo apt-get update
    sudo apt-get install -y libproj-dev libgeos-dev libspatialite-dev libgdal-dev gdal-bin netcdf-bin

Python Dependencies
^^^^^^^^^^^^^^^^^^^

In the virtual environment created above, install geoextent in development mode with all dependencies:

::

    # Install GDAL Python bindings first (matching your system GDAL version)
    GDAL_VERSION=$(gdal-config --version)
    pip install "GDAL==$GDAL_VERSION"

    # Install geoextent in editable mode with all optional dependencies
    pip install -e .[dev,test,docs]

This will install all required and optional dependencies defined in ``pyproject.toml``.

Run tests
---------

After installing geoextent with development dependencies (see above), run the test suite using pytest:

::

    pytest

    # Run specific test file
    pytest tests/test_api.py

    # Run specific test categories
    pytest tests/test_api_*.py         # API tests
    pytest tests/test_cli*.py          # CLI tests
    pytest -m "not slow"               # Exclude slow tests

    # Run with coverage
    pytest --cov=geoextent --cov-report=term-missing

    # Run specific test class or method
    pytest tests/test_api.py::TestClassName::test_method_name

Local GitHub Actions Testing
-----------------------------

Test workflows locally using `act <https://github.com/nektos/act>`_ to validate changes before pushing to GitHub.

Installing act
^^^^^^^^^^^^^^

::

    # macOS
    brew install act

    # Linux
    curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

    # Windows
    choco install act-cli

Configuration
^^^^^^^^^^^^^

The project includes an ``.actrc`` configuration file with Ubuntu 24.04 image settings.

Running Local Tests
^^^^^^^^^^^^^^^^^^^

Use the provided script for easy local testing::

    # Run main Python package tests (default)
    ./scripts/test-local-ci.sh

    # Run specific workflow
    ./scripts/test-local-ci.sh --workflow comprehensive-tests

    # Run specific test category
    ./scripts/test-local-ci.sh --workflow comprehensive-tests --test-category api-core

    # Run with specific Python version
    ./scripts/test-local-ci.sh --python-version 3.11

    # List all available jobs
    ./scripts/test-local-ci.sh --list-jobs

    # Show what would be executed (dry run)
    ./scripts/test-local-ci.sh --dry-run

Available Test Categories
^^^^^^^^^^^^^^^^^^^^^^^^^

- ``api-core`` - Core API functionality tests
- ``api-repositories`` - Remote repository provider tests (Zenodo, Figshare, Dryad, PANGAEA, OSF, GFZ, Pensoft, Dataverse)
- ``api-formats`` - Format handler tests (CSV, GeoJSON, GeoTIFF, Shapefile, FlatGeobuf)
- ``cli`` - Command-line interface tests
- ``integration`` - Integration and special feature tests

Direct act Commands
^^^^^^^^^^^^^^^^^^^

::

    # Run main test workflow
    act -W .github/workflows/pythonpackage.yml

    # Run comprehensive tests for api-core category
    act -W .github/workflows/comprehensive-tests.yml --matrix test-category:api-core

    # Run with specific Python version
    act -W .github/workflows/pythonpackage.yml --matrix python-version:3.11

    # List all jobs in a workflow
    act -W .github/workflows/comprehensive-tests.yml --list

Code Formatting
---------------

Format code with black and set up pre-commit hooks::

    # Format code
    black geoextent/ tests/

    # Set up pre-commit hooks (run once)
    pre-commit install

    # Run pre-commit hooks manually
    pre-commit run --all-files

Documentation
-------------

The documentation is based on Sphinx_.
The source files can be found in the directory ``docs/`` and the rendered online documentation is at https://nuest.github.io/geoextent/.

Build documentation locally
^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

    # Ensure documentation dependencies are installed
    pip install -e .[docs]

    # Build HTML documentation
    cd docs/
    make html

    # View the documentation (Linux)
    xdg-open build/html/index.html

    # Clean build artifacts
    make clean

.. _Sphinx: https://www.sphinx-doc.org

Release
-------

Prerequisites
^^^^^^^^^^^^^

Required tools:

- ``setuptools``
- ``wheel``
- ``twine``

::

    pip install --upgrade setuptools wheel twine

Run tests
^^^^^^^^^

Make sure that all tests work locally by running

::

    pytest

Bump version for release
^^^^^^^^^^^^^^^^^^^^^^^^

Follow the `Semantic Versioning specification`_ to clearly mark changes as a new major version, minor changes, or patches.
The version number is managed using `setuptools-scm`_ via git tags.

.. _Semantic Versioning specification: https://semver.org/
.. _setuptools-scm: https://setuptools-scm.readthedocs.io/en/stable/usage/

Update changelog
^^^^^^^^^^^^^^^^

Update the changelog in file ``docs/source/changelog.rst``, use the `sphinx-issues`_ syntax for referring to pull requests and contributors for changes where appropriate.

.. _sphinx-issues: https://github.com/sloria/sphinx-issues

Update citation and authors information
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Make sure the following files have the current information (version, commit, contributors, dates, ...):

- ``CITATION.cff``, see https://citation-file-format.github.io/
- ``codemeta.json``, see https://codemeta.github.io/codemeta-generator/
- ``README.md`` and ``docs/source/index.rst``, the "How to cite" sections.

Build distribution archive
^^^^^^^^^^^^^^^^^^^^^^^^^^

See the PyPI documentation on generating a distribution archive, https://packaging.python.org/tutorials/packaging-projects/, for details.

::

    # remove previous releases and builds
    rm dist/*
    rm -rf build *.egg-info

    python3 setup.py sdist bdist_wheel

Upload to test repository
^^^^^^^^^^^^^^^^^^^^^^^^^

First upload to the test repository and check everything is in order.

::

    # upload with twine, make sure only one wheel is in dist/
    twine upload --repository-url https://test.pypi.org/legacy/ dist/*

Check if the information on https://test.pypi.org/project/geoextent/ is correct.
Then switch to a new Python environment or use a Python 3 container to get an "empty" setup.
Install geoextent from TestPyPI and ensure the package is functional:

::

    docker run --rm -it -v $(pwd)/tests/testdata/:/testdata python:3-buster /bin/bash

    # install system deps
    apt-get update
    apt-get install gdal-bin libgdal-dev libproj-dev libgeos-dev libspatialite-dev netcdf-bin

    # # Package dependencies (from regular PyPI), not all are on TestPyPI
    pip install -r requirements.txt
    pip install pygdal==`gdal-config --version`.*

    pip install -i https://test.pypi.org/simple/ geoextent
    geoextent --help
    geoextent --version

    geoextent -b -t /testdata/geojson/muenster_ring_zeit.geojson
    geoextent -b -t /testdata/shapefile/gis_osm_buildings_a_free_1.shp

Alternatively, use Debian Testing container to try out a more recent version of GDAL which matches the current release of the GDAL package on PyPI:

::

    docker run --rm -it -v $(pwd)/tests/testdata/:/testdata debian:testing

    # Python + PIP
    apt-get update
    apt-get install python3 python3-pip wget

    # System dependencies
    apt-get install gdal-bin libgdal-dev libproj-dev libgeos-dev

    # Package dependencies (from regular PyPI)
    pip install -r requirements.txt
    pip install pygdal==`gdal-config --version`.*

    pip install -i https://test.pypi.org/simple/ geoextent
    geoextent --help
    geoextent --version

    wget https://github.com/nuest/geoextent/blob/main/tests/testdata/tif/wf_100m_klas.tif

    geoextent -b wf_100m_klas.tif


Upload to PyPI
^^^^^^^^^^^^^^

::

    twine upload dist/*


Check if information on https://pypi.org/project/geoextent/ is all correct.
Install the library from PyPI into a new environment, e.g., by reusing the container session from above, and check that everything works.


Add tag
^^^^^^^

Add a version tag to the commit of the release and push it to the main repository.
Go to GitHub and create a new release by using the "Draft a new release" button and using the just pushed tag.
Releases are automatically stored on Zenodo - double-check that the release is also available on Zenodo
