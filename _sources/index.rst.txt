Welcome to the geoextent documentation!
=======================================

``geoextent`` is a Python library for **extracting geospatial extent of files and directories with multiple data formats**.

geoextent supports a wide range of geospatial file formats and can extract data from major research repositories like Zenodo, PANGAEA, OSF, Figshare, and many others. It provides both bounding box (spatial) and temporal extent extraction, with additional features like convex hull computation, placename lookup, and flexible output formats.

**Key Features:**

- **Multiple format support**: GeoJSON, CSV, Shapefile, GeoTIFF, GeoPackage, GPX, KML, GML, FlatGeobuf, and more
- **Repository integration**: Direct extraction from Zenodo, PANGAEA, OSF, Figshare, Dryad, GFZ Data Services, and other research repositories
- **Flexible extent types**: Bounding boxes, temporal extents, and convex hulls
- **Advanced filtering**: Size limits, file type filtering, and parallel downloads
- **Rich output options**: GeoJSON, WKT, WKB formats with optional geojson.io visualization
- **Geographic context**: Placename lookup using multiple gazetteer services
- **Docker support**: Containerized execution for easy deployment

**API Stability**

*Version 0.x (Current)*: Breaking changes may occur between minor versions. The API is under active development.

*Version 1.0+*: Will follow semantic versioning with stable API guarantees.

**Current API Functions:**

- ``fromFile()`` - Extract extent from individual files
- ``fromDirectory()`` - Extract extent from directories
- ``fromRemote()`` - Extract extent from remote sources (repositories, journals, preprint servers)

This project was originally developed as part of the `DFG-funded <https://o2r.info/about/#funding>`_ research project Opening Reproducible Research `o2r <https://o2r.info>`_.

Please report `Bugs <https://github.com/nuest/geoextent/issues>`_.

Documentation overview
----------------------

.. toctree::
    :maxdepth: 2

    install
    examples
    howto/index_howto
    supportedformats/index_supportedformats
    changelog
    development

------

How to cite
-----------

::

    Nüst, Daniel; Garzón, Sebastian and Qamaz, Yousef. (2021, May 11). o2r-project/geoextent (Version v0.7.1). Zenodo. https://doi.org/10.5281/zenodo.3925693

------

The software project is published under the MIT license, see file ``LICENSE`` for details.

This documentation is published under a Creative Commons CC0 1.0 Universal License.
To the extent possible under law, the people who associated CC0 with this work have waived all copyright and related or neighboring rights to this work.
This work is published from: Germany.

.. image:: https://o2r.info/public/images/logo-transparent.png

------

geoextent version PLACEHOLDER_VERSION @ git PLACEHOLDER_HASH PLACEHOLDER_TIMESTAMP
