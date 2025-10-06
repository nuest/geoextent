Quick Start Guide
=================

This guide helps you get started with geoextent quickly through practical examples.

Installation
------------

Install geoextent via pip::

   pip install geoextent

**Requirements:** Python 3.10+ and GDAL 3.11.x

For detailed installation instructions including system dependencies and Docker setup, see :doc:`install`.

Basic Usage
-----------

Extract from a Local File
^^^^^^^^^^^^^^^^^^^^^^^^^^

Extract spatial extent from a GeoJSON file::

   python -m geoextent -b tests/testdata/geojson/muenster_ring.geojson

Output:

.. code-block:: json

   {
     "type": "FeatureCollection",
     "features": [{
       "type": "Feature",
       "geometry": {
         "type": "Polygon",
         "coordinates": [[...]]
       }
     }]
   }

Extract from a Directory
^^^^^^^^^^^^^^^^^^^^^^^^^

Process all geospatial files in a directory::

   python -m geoextent -b tests/testdata/geojson/

Geoextent automatically discovers supported file formats and returns a merged bounding box covering all files.

Extract from Research Repository
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extract directly from a Zenodo dataset using its DOI::

   python -m geoextent -b -t https://doi.org/10.5281/zenodo.4593540

Or use the short DOI format::

   python -m geoextent -b -t 10.5281/zenodo.4593540

Supported repositories include Zenodo, Figshare, Dryad, PANGAEA, OSF, Dataverse, GFZ Data Services, Pensoft, and TU Dresden Opara. See :doc:`providers` for complete list.

Extract from Multiple Repositories
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Process multiple repositories in a single command::

   python -m geoextent -b -t \
       10.5281/zenodo.4593540 \
       10.25532/OPARA-581 \
       https://osf.io/abc123/

Returns a merged bounding box covering all resources, similar to directory extraction.

Python API
----------

Single File Extraction
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import geoextent.lib.extent as geoextent

   result = geoextent.fromFile('data.geojson', bbox=True, tbox=True)
   print(result['bbox'])  # [minx, miny, maxx, maxy]
   print(result['tbox'])  # ['2020-01-01', '2020-12-31']

Directory Extraction
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   result = geoextent.fromDirectory('data/', bbox=True, tbox=True)
   print(result['bbox'])  # Merged bounding box of all files

Remote Repository Extraction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Single repository
   result = geoextent.fromRemote('10.5281/zenodo.4593540', bbox=True)

   # Multiple repositories
   identifiers = ['10.5281/zenodo.4593540', '10.25532/OPARA-581']
   result = geoextent.fromRemote(identifiers, bbox=True, tbox=True)
   print(result['bbox'])  # Merged bounding box covering all resources

Common Options
--------------

Bounding Box and Temporal Extent
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extract both spatial and temporal extents::

   python -m geoextent -b -t data.geojson

- ``-b`` or ``--bbox`` - Extract bounding box
- ``-t`` or ``--tbox`` - Extract temporal extent

Convex Hull
^^^^^^^^^^^

Extract a more precise convex hull instead of rectangular bounding box::

   python -m geoextent -b --convex-hull data.geojson

Useful for irregularly shaped data where a rectangular box would include large empty areas.

Output Formats
^^^^^^^^^^^^^^

Export spatial extent in different formats::

   # GeoJSON (default)
   python -m geoextent -b data.geojson

   # Well-Known Text
   python -m geoextent -b --format wkt data.geojson

   # Well-Known Binary
   python -m geoextent -b --format wkb data.geojson

Interactive Visualization
^^^^^^^^^^^^^^^^^^^^^^^^^^

Open the extracted extent in your browser using geojson.io::

   python -m geoextent -b --browse data.geojson

Next Steps
----------

- :doc:`examples` - More detailed examples for specific use cases
- :doc:`howto/cli` - Complete CLI reference with all options
- :doc:`howto/api` - Python API function signatures
- :doc:`core-features` - Essential features for everyday use
- :doc:`advanced-features` - Specialized options and performance tuning
- :doc:`providers` - Research repository provider details
