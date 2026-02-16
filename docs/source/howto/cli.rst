
Command-Line Interface (CLI)
============================

Basics
------

``geoextent`` can be called on the command line with this command :

.. autoprogram:: geoextent.__main__:arg_parser
   :prog: \

Examples
--------

.. note::
   Depending on the local configuration, **geoextent** might need to be called with the python interpreter prepended:

   `python -m geoextent ...`

Show help message
^^^^^^^^^^^^^^^^^

::

   geoextent -h

.. jupyter-execute::
   :hide-code:
   :stderr:

   import geoextent.__main__ as geoextent
   geoextent.print_help()

Extract bounding box from a single file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   You can find the file used in the examples of this section from `muenster_ring_zeit <https://raw.githubusercontent.com/nuest/geoextent/main/tests/testdata/geojson/muenster_ring_zeit.geojson>`_. Furthermore, for displaying the rendering of the file contents, see `rendered blob <https://github.com/nuest/geoextent/blob/main/tests/testdata/geojson/muenster_ring_zeit.geojson>`_.

::

   geoextent -b muenster_ring_zeit.geojson

Output:

.. jupyter-execute::
   :hide-code:
   :stderr:

   import geoextent.lib.extent as geoextent
   geoextent.fromFile('../tests/testdata/geojson/muenster_ring_zeit.geojson', True, False)

Extract time interval from a single file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   You can find the file used in the examples of this section from `muenster_ring_zeit <https://raw.githubusercontent.com/nuest/geoextent/main/tests/testdata/geojson/muenster_ring_zeit.geojson>`_. Furthermore, for displaying the rendering of the file contents, see `rendered blob <https://github.com/nuest/geoextent/blob/main/tests/testdata/geojson/muenster_ring_zeit.geojson>`_.

::

   geoextent -t muenster_ring_zeit.geojson

Output:

.. jupyter-execute::
   :hide-code:
   :stderr:

   import geoextent.lib.extent as geoextent
   geoextent.fromFile('../tests/testdata/geojson/muenster_ring_zeit.geojson', False, True)

Extract both bounding box and time interval from a single file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   You can find the file used in the examples of this section from `muenster_ring_zeit <https://raw.githubusercontent.com/nuest/geoextent/main/tests/testdata/geojson/muenster_ring_zeit.geojson>`_. Furthermore, for displaying the rendering of the file contents, see `rendered blob <https://github.com/nuest/geoextent/blob/main/tests/testdata/geojson/muenster_ring_zeit.geojson>`_.

::

   geoextent -b -t muenster_ring_zeit.geojson

.. jupyter-execute::
   :hide-code:
   :stderr:

   import geoextent.lib.extent as geoextent
   geoextent.fromFile('../tests/testdata/geojson/muenster_ring_zeit.geojson', True, True)

Folders or ZIP files(s)
-----------------------

Geoextent also supports queries for multiple files inside **folders** or **ZIP file(s)**.

Extract both bounding box and time interval from a folder or zipfile
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   geoextent -b -t folder_two_files

.. jupyter-execute::
   :hide-code:
   :stderr:

   import geoextent.lib.extent as geoextent
   geoextent.fromDirectory('../tests/testdata/folders/folder_two_files', True, True)

The output of this function is the combined bbox or tbox resulting from merging all results of individual files (see: :doc:`../supportedformats/index_supportedformats`) inside the folder or zipfile. The resulting coordinate reference system  ``CRS`` of the combined bbox is always in the `EPSG: 4326 <https://epsg.io/4326>`_ system.


Remote Repositories
-------------------

Geoextent supports extracting geospatial extent from multiple research data repositories including Zenodo, PANGAEA, OSF, Figshare, Dryad, GFZ Data Services, Dataverse, and Pensoft.

Extract from Zenodo
^^^^^^^^^^^^^^^^^^^

::

   geoextent -b -t https://doi.org/10.5281/zenodo.4593540

Extract from PANGAEA
^^^^^^^^^^^^^^^^^^^^

::

   geoextent -b -t https://doi.org/10.1594/PANGAEA.734969

Extract from OSF
^^^^^^^^^^^^^^^^

::

   geoextent -b -t https://doi.org/10.17605/OSF.IO/4XE6Z
   geoextent -b -t OSF.IO/4XE6Z

Extract from GFZ Data Services
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   geoextent -b -t 10.5880/GFZ.4.8.2023.004

Extract from RADAR
^^^^^^^^^^^^^^^^^^

::

   geoextent -b -t 10.35097/tvn5vujqfvf99f32

Extract from Arctic Data Center
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   geoextent -b -t 10.18739/A2Z892H2J

Extract from Arctic Data Center (metadata only)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   geoextent -b --no-download-data 10.18739/A2Z892H2J

Extract from 4TU.ResearchData
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   geoextent -b -t https://data.4tu.nl/articles/_/12707150/1

Extract from 4TU.ResearchData (metadata only)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   geoextent -b --no-download-data https://data.4tu.nl/articles/_/12707150/1

Smart metadata-first extraction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``--metadata-first`` to try metadata-only extraction first, falling back to data download if the provider has no metadata or the metadata didn't yield results. This is useful for batch extractions across multiple providers:

::

   geoextent -b --metadata-first 10.12761/sgn.2018.10225
   geoextent -b --metadata-first Q64

Extract from three German regional datasets with a convex hull — Wikidata (Berlin), 4TU (Dresden), and Senckenberg all use fast metadata extraction, producing a compact convex hull over central Germany:

::

   geoextent -b --convex-hull --metadata-first Q64 https://data.4tu.nl/datasets/3035126d-ee51-4dbd-a187-5f6b0be85e9f/1 10.12761/sgn.2018.10225

Comparing extraction modes: metadata, download, and convex hull
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following three calls on an `Arctic Data Center <https://arcticdata.io/>`_ dataset of ice wedge thermokarst polygons at Point Lay, Alaska illustrate how ``--no-download-data`` and ``--convex-hull`` affect the output geometry.

**1. Metadata-only extraction** (``--no-download-data``): Uses the bounding box stored in the repository metadata — fast, no file downloads. The bbox is slightly larger because it comes from the dataset-level metadata rather than the actual geometries:

::

   geoextent -b -t --no-download-data 10.18739/A2Z892H2J

Output bbox: ``[-163.049, 69.721, -162.935, 69.760]`` with tbox ``[1949-01-01, 2020-01-01]``.
`View on geojson.io <https://geojson.io/#data=data:application/json,%7B%22type%22%3A%20%22FeatureCollection%22%2C%20%22features%22%3A%20%5B%7B%22type%22%3A%20%22Feature%22%2C%20%22geometry%22%3A%20%7B%22type%22%3A%20%22Polygon%22%2C%20%22coordinates%22%3A%20%5B%5B%5B-163.04877%2C%2069.721436%5D%2C%20%5B-162.93472%2C%2069.721436%5D%2C%20%5B-162.93472%2C%2069.760124%5D%2C%20%5B-163.04877%2C%2069.760124%5D%2C%20%5B-163.04877%2C%2069.721436%5D%5D%5D%7D%2C%20%22properties%22%3A%20%7B%22tbox%22%3A%20%5B%221949-01-01%22%2C%20%222020-01-01%22%5D%7D%7D%5D%7D>`_

**2. Full download extraction** (default): Downloads the 2 GeoJSON files (1.6 MB) and computes the merged bounding box from the actual feature geometries — tighter than metadata:

::

   geoextent -b -t 10.18739/A2Z892H2J

Output bbox: ``[-163.027, 69.723, -162.931, 69.751]``.
`View on geojson.io <https://geojson.io/#data=data:application/json,%7B%22type%22%3A%20%22FeatureCollection%22%2C%20%22features%22%3A%20%5B%7B%22type%22%3A%20%22Feature%22%2C%20%22geometry%22%3A%20%7B%22type%22%3A%20%22Polygon%22%2C%20%22coordinates%22%3A%20%5B%5B%5B-163.02738054677604%2C%2069.72281732635359%5D%2C%20%5B-162.93103114652428%2C%2069.72281732635359%5D%2C%20%5B-162.93103114652428%2C%2069.75146586193965%5D%2C%20%5B-163.02738054677604%2C%2069.75146586193965%5D%2C%20%5B-163.02738054677604%2C%2069.72281732635359%5D%5D%5D%7D%2C%20%22properties%22%3A%20%7B%7D%7D%5D%7D>`_

**3. Convex hull extraction** (``--convex-hull``): Downloads the same files but computes a convex hull around all feature vertices instead of an axis-aligned bounding box — most precise representation of the data footprint:

::

   geoextent -b -t --convex-hull 10.18739/A2Z892H2J

`View on geojson.io <https://geojson.io/#data=data:application/json,%7B%22type%22%3A%20%22FeatureCollection%22%2C%20%22features%22%3A%20%5B%7B%22type%22%3A%20%22Feature%22%2C%20%22geometry%22%3A%20%7B%22type%22%3A%20%22Polygon%22%2C%20%22coordinates%22%3A%20%5B%5B%5B-162.9354945417586%2C%2069.72283808540368%5D%2C%20%5B-162.93557496284427%2C%2069.7228390285746%5D%2C%20%5B-163.0194325297929%2C%2069.72838204531571%5D%2C%20%5B-163.02030700560616%2C%2069.72850357636389%5D%2C%20%5B-163.0214176193676%2C%2069.72868360497586%5D%2C%20%5B-163.02435253222512%2C%2069.72916334627877%5D%2C%20%5B-163.02450952668033%2C%2069.72920699391047%5D%2C%20%5B-163.02482091488488%2C%2069.72932218370318%5D%2C%20%5B-163.0250142330283%2C%2069.72940812452067%5D%2C%20%5B-163.02572128008003%2C%2069.73003038428426%5D%2C%20%5B-163.0258328544103%2C%2069.73012936964642%5D%2C%20%5B-163.02635311487705%2C%2069.73059594956999%5D%2C%20%5B-163.02657237555903%2C%2069.73083576188635%5D%2C%20%5B-163.0266437299001%2C%2069.7309342959129%5D%2C%20%5B-163.02670988409136%2C%2069.7310886198561%5D%2C%20%5B-163.0267007826062%2C%2069.73118625225948%5D%2C%20%5B-163.02664885167755%2C%2069.73131132883259%5D%2C%20%5B-163.02660212132923%2C%2069.73138061544832%5D%2C%20%5B-163.02330823108616%2C%2069.73603492940758%5D%2C%20%5B-163.02160167895758%2C%2069.73834743619085%5D%2C%20%5B-163.01288307826624%2C%2069.74796693841913%5D%2C%20%5B-163.00909952064822%2C%2069.7509500736801%5D%2C%20%5B-163.00906358200902%2C%2069.75097811658188%5D%2C%20%5B-163.00688215603128%2C%2069.7510636751487%5D%2C%20%5B-162.95969874108445%2C%2069.75072411709584%5D%2C%20%5B-162.95965847693193%2C%2069.75072365094097%5D%2C%20%5B-162.95941823800084%2C%2069.75070690693762%5D%2C%20%5B-162.93367084453843%2C%2069.72337519437507%5D%2C%20%5B-162.93367356637467%2C%2069.72334730097528%5D%2C%20%5B-162.93417515224687%2C%2069.72315771059625%5D%2C%20%5B-162.93421672390681%2C%2069.72314423578342%5D%2C%20%5B-162.93442322101038%2C%2069.7230908082779%5D%2C%20%5B-162.93495956459498%2C%2069.72295747430567%5D%2C%20%5B-162.93528940963182%2C%2069.72287756746046%5D%2C%20%5B-162.9354945417586%2C%2069.72283808540368%5D%5D%5D%7D%2C%20%22properties%22%3A%20%7B%7D%7D%5D%7D>`_

The three modes yield progressively tighter representations: metadata bbox > download bbox > convex hull. Use ``--no-download-data`` for speed when approximate extents suffice, or ``--convex-hull`` for the most faithful footprint of the actual data.

The output of this function is the combined bbox or tbox resulting from merging all results of individual files (see: :doc:`../supportedformats/index_supportedformats`) inside the repository. The resulting coordinate reference system  ``CRS`` of the combined bbox is always in the `EPSG: 4326 <https://epsg.io/4326>`_ system.

For comprehensive examples including all supported repositories and advanced features, see :doc:`../examples`.

Debugging
^^^^^^^^^

You can enable detailed logs by passing the ``--debug`` option, or by setting the environment variable ``GEOEXTENT_DEBUG=1``.

::

   geoextent --debug -b -t muenster_ring_zeit.geojson

   GEOEXTENT_DEBUG=1 geoextent -b -t muenster_ring_zeit.geojson

Details
^^^^^^^
You can enable details for folders and ZIP files by passing the ``--details`` option, this option allows you to access
to the geoextent of the individual files inside the folders/ ZIP files used to compute the aggregated bounding box (bbox)
or time box (tbox).

::

   geoextent --details -b -t folder_one_file

.. jupyter-execute::
   :hide-code:
   :stderr:

   import geoextent.lib.extent as geoextent
   geoextent.fromDirectory('../tests/testdata/folders/folder_one_file', True, True, True)

Export function
^^^^^^^^^^^^^^^
You can export the result of Geoextent to a Geopackage file. This file contains the output of all files within the
folder or repository.

::

    geoextent -b -t --output path/to/output/geopackage_file.gpkg folder_path
