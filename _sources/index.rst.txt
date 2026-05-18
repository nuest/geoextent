Welcome to the geoextent documentation!
=======================================

``geoextent`` is a Python library for **extracting geospatial extent of files and directories with multiple data formats**.

geoextent supports a wide range of geospatial file formats and can extract data from major research repositories like Zenodo, PANGAEA, OSF, Figshare, and many others. It provides both bounding box (spatial) and temporal extent extraction, with additional features like convex hull computation, placename lookup, and flexible output formats.

**Key Features:**

- **Multiple format support**: GeoJSON, CSV, Shapefile, GeoTIFF, GeoPackage, GPX, KML, GML, FlatGeobuf, and more
- **Repository integration**: Direct extraction from Zenodo, PANGAEA, OSF, Figshare, Dryad, GFZ Data Services, and other research repositories
- **Flexible extent types**: Bounding boxes, temporal extents, and convex hulls
- **Advanced filtering**: Size limits, file type filtering, and parallel downloads
- **Rich output options**: GeoJSON, WKT, WKB formats with optional geojson.io visualization and static map preview
- **Geographic context**: Placename lookup using multiple gazetteer services
- **Docker support**: Containerized execution for easy deployment

**API Stability**

*Version 0.x (Current)*: Breaking changes may occur between minor versions. The API is under active development.

*Version 1.0+*: Will follow semantic versioning with stable API guarantees.

**Current API Functions:**

- ``from_file()`` - Extract extent from individual files
- ``from_directory()`` - Extract extent from directories
- ``from_remote()`` - Extract extent from remote sources (repositories, journals, preprint servers)

This project was originally developed as part of the `DFG-funded <https://o2r.info/about/#funding>`_ research project Opening Reproducible Research `o2r <https://o2r.info>`_.

Please report `Bugs <https://github.com/nuest/geoextent/issues>`_.

Documentation overview
----------------------

.. toctree::
    :maxdepth: 2

    install
    examples
    examples_journals
    features
    external-metadata
    howto/index_howto
    supportedformats/index_supportedformats
    changelog
    development

------

How to cite
-----------

::

    Nüst, Daniel; Garzón, Sebastian; Drechsler, Lars and Qamaz, Yousef. (2026, May 15). geoextent (Version v0.13.0). Zenodo. https://doi.org/10.5281/zenodo.18635398

------

The software project is published under the MIT license, see file ``LICENSE`` for details.

This documentation is published under a Creative Commons CC0 1.0 Universal License.
To the extent possible under law, the people who associated CC0 with this work have waived all copyright and related or neighboring rights to this work.
This work is published from: Germany.

------

Funding & Acknowledgements
--------------------------

This project was initially developed as part of the German Research
Foundation (DFG)-funded research project Opening Reproducible Research
(`o2r <https://o2r.info>`_, DFG project no.
`PE 1632/10-1 <https://gepris.dfg.de/gepris/projekt/274927273>`_ and
`PE 1632/17-1 <https://gepris.dfg.de/gepris/projekt/415851837>`_).
Continuing development is supported by the DFG-funded
`NFDI4Earth <https://nfdi4earth.de>`_ consortium (DFG project no.
`460036893 <https://gepris.dfg.de/gepris/projekt/460036893>`_) and by the
German Federal Ministry of Research, Technology and Space (BMFTR) through
the `KOMET <https://projects.tib.eu/komet/en/projekt/>`_ project —
*Collaborative enrichment of the metadata commons to foster a diverse OA
ecosystem* (BMFTR grant no. 16KOA009B).

.. list-table::
    :class: funding-logos
    :widths: auto

    * - .. image:: https://o2r.info/public/images/logo-transparent.png
           :height: 60px
           :alt: Logo of the o2r project
           :target: https://o2r.info
      - .. image:: https://www.nfdi4earth.de/templates/nfdi4earth/images/NFDI4Earth_logo.png
           :height: 60px
           :alt: Logo of NFDI4Earth
           :target: https://nfdi4earth.de
      - .. image:: https://projects.tib.eu/fileadmin/templates/komet/tib_projects_komet_1150.png
           :height: 60px
           :alt: Logo of the KOMET project
           :target: https://projects.tib.eu/komet/en/projekt/

------

geoextent version PLACEHOLDER_VERSION @ git PLACEHOLDER_HASH PLACEHOLDER_TIMESTAMP
