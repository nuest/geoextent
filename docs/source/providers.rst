Content Providers
==================

Geoextent supports extracting geospatial data from 9 research data repositories. All providers support DOI-based and URL-based extraction, and return merged geometries when processing multiple resources.

Overview
--------

All content providers support:

- **DOI-based extraction** - Use DOIs directly or via resolver URLs
- **URL-based extraction** - Use direct repository URLs
- **Merged geometry output** - Multiple resources combined into single extent
- **Download size limiting** - Control bandwidth with ``--max-download-size``
- **File filtering** - Skip non-geospatial files with ``--download-skip-nogeo``
- **Parallel downloads** - Speed up multi-file downloads with ``--max-download-workers``

Quick Reference
---------------

+-------------------+---------------------+----------------------------------------+
| Provider          | DOI Prefix          | Example                                |
+===================+=====================+========================================+
| Zenodo            | 10.5281/zenodo      | 10.5281/zenodo.4593540                |
+-------------------+---------------------+----------------------------------------+
| Figshare          | 10.6084/m9.figshare | 10.6084/m9.figshare.12345678          |
+-------------------+---------------------+----------------------------------------+
| Dryad             | 10.5061/dryad       | 10.5061/dryad.0k6djhb7x               |
+-------------------+---------------------+----------------------------------------+
| PANGAEA           | 10.1594/PANGAEA     | 10.1594/PANGAEA.734969                |
+-------------------+---------------------+----------------------------------------+
| OSF               | 10.17605/OSF.IO     | 10.17605/OSF.IO/ABC123                |
+-------------------+---------------------+----------------------------------------+
| Dataverse         | Varies by instance  | 10.7910/DVN/123456                    |
+-------------------+---------------------+----------------------------------------+
| GFZ Data Services | 10.5880/GFZ         | 10.5880/GFZ.2.1.2020.001              |
+-------------------+---------------------+----------------------------------------+
| Pensoft           | 10.3897             | 10.3897/BDJ.13.e159973                |
+-------------------+---------------------+----------------------------------------+
| TU Dresden Opara  | 10.25532/OPARA      | 10.25532/OPARA-581                    |
+-------------------+---------------------+----------------------------------------+

Provider Details
----------------

Zenodo
^^^^^^

**Description:** Free and open digital archive built by CERN and OpenAIRE for sharing research output in any format. Supports all research disciplines with unlimited storage and preservation guarantees.

**Website:** https://zenodo.org/

**DOI Prefix:** ``10.5281/zenodo``

**Supported Identifier Formats:**

- DOI: ``10.5281/zenodo.4593540``
- DOI URL: ``https://doi.org/10.5281/zenodo.4593540``
- Zenodo URL: ``https://zenodo.org/record/4593540``

**Example:**

.. code-block:: bash

   python -m geoextent -b -t 10.5281/zenodo.4593540

**Special Notes:**

- Supports download size limiting and file filtering
- Parallel downloads supported
- Handles both individual files and complete record archives

Figshare
^^^^^^^^

**Description:** Online open access repository for preserving and sharing research outputs with DOI assignment and altmetrics. Provides 20GB free private space and unlimited public sharing.

**Website:** https://figshare.com/

**DOI Prefix:** ``10.6084/m9.figshare``

**Supported Identifier Formats:**

- DOI: ``10.6084/m9.figshare.12345678``
- DOI URL: ``https://doi.org/10.6084/m9.figshare.12345678``
- Figshare URL: ``https://figshare.com/articles/dataset/title/12345678``

**Example:**

.. code-block:: bash

   python -m geoextent -b 10.6084/m9.figshare.12345678

**Special Notes:**

- Full support for size limiting and file filtering
- API-based file metadata retrieval
- Supports private and public datasets (public only accessible)

Dryad
^^^^^

**Description:** Nonprofit curated repository specializing in data underlying scientific publications with CC0 licensing. Focuses on data reusability and long-term preservation with Merritt Repository.

**Website:** https://datadryad.org/

**DOI Prefix:** ``10.5061/dryad``

**Supported Identifier Formats:**

- DOI: ``10.5061/dryad.0k6djhb7x``
- DOI URL: ``https://doi.org/10.5061/dryad.0k6djhb7x``
- Dryad URL: ``https://datadryad.org/stash/dataset/doi:10.5061/dryad.0k6djhb7x``

**Example:**

.. code-block:: bash

   python -m geoextent -b -t 10.5061/dryad.0k6djhb7x

**Special Notes:**

- Intelligent file vs. ZIP archive download selection
- Full filtering and size limiting support
- Handles nested ZIP files efficiently

PANGAEA
^^^^^^^

**Description:** Digital data library and publisher for earth system science with over 375,000 georeferenced datasets. Specialized in geosciences, environmental, and climate research with extensive metadata.

**Website:** https://www.pangaea.de/

**DOI Prefix:** ``10.1594/PANGAEA``

**Supported Identifier Formats:**

- DOI: ``10.1594/PANGAEA.734969``
- DOI URL: ``https://doi.org/10.1594/PANGAEA.734969``
- PANGAEA URL: ``https://pangaea.de/doi:10.1594/PANGAEA.734969``

**Example:**

.. code-block:: bash

   python -m geoextent -b -t 10.1594/PANGAEA.734969

**Special Notes:**

- Often includes rich geospatial metadata in repository records
- Supports ``--no-download-data`` for metadata-only extraction
- Specialized in Earth science datasets

OSF (Open Science Framework)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Description:** Free open-source project management tool by Center for Open Science for collaborative research workflows. Supports data storage, version control, and research lifecycle management.

**Website:** https://osf.io/

**DOI Prefix:** ``10.17605/OSF.IO``

**Supported Identifier Formats:**

- DOI: ``10.17605/OSF.IO/ABC123``
- DOI URL: ``https://doi.org/10.17605/OSF.IO/ABC123``
- OSF URL: ``https://osf.io/abc123/``
- Short ID: ``abc123``

**Example:**

.. code-block:: bash

   python -m geoextent -b https://osf.io/4xe6z/

**Special Notes:**

- Full filtering and size limiting capabilities
- Handles project storage and individual components
- Supports file versioning

Dataverse
^^^^^^^^^

**Description:** Open-source web application from Harvard University for sharing and preserving research data across disciplines. Supports institutional repositories with customizable metadata schemas.

**Website:** https://dataverse.org/

**DOI Prefix:** Varies by Dataverse instance (commonly ``10.7910/DVN``)

**Supported Identifier Formats:**

- DOI: ``10.7910/DVN/ABCDEF``
- DOI URL: ``https://doi.org/10.7910/DVN/ABCDEF``
- Dataverse URL: ``https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/ABCDEF``

**Example:**

.. code-block:: bash

   python -m geoextent -b -t 10.7910/DVN/ABCDEF

**Special Notes:**

- Supports multiple Dataverse instances (Harvard, ICPSR, etc.)
- Handles complex dataset structures
- API-based metadata and file retrieval

GFZ Data Services
^^^^^^^^^^^^^^^^^

**Description:** Curated repository for geosciences domain hosted at GFZ German Research Centre in Potsdam. Specialized in Earth observation, geophysics, and geoscience research data.

**Website:** https://dataservices.gfz-potsdam.de/

**DOI Prefix:** ``10.5880/GFZ``

**Supported Identifier Formats:**

- DOI: ``10.5880/GFZ.2.1.2020.001``
- DOI URL: ``https://doi.org/10.5880/GFZ.2.1.2020.001``
- GFZ URL: ``https://dataservices.gfz-potsdam.de/panmetaworks/showshort.php?id=...``

**Example:**

.. code-block:: bash

   python -m geoextent -b -t 10.5880/GFZ.2.1.2020.001

**Special Notes:**

- Specialized in geoscience datasets
- Comprehensive metadata for spatial datasets
- Long-term preservation guarantees

Pensoft
^^^^^^^

**Description:** Scholarly publisher from Bulgaria specializing in biodiversity with 60+ open access journals. Integrates data publishing with manuscript publication for transparent research.

**Website:** https://pensoft.net/

**DOI Prefix:** ``10.3897``

**Supported Identifier Formats:**

- DOI: ``10.3897/BDJ.13.e159973``
- DOI URL: ``https://doi.org/10.3897/BDJ.13.e159973``

**Example:**

.. code-block:: bash

   python -m geoextent -b -t 10.3897/BDJ.13.e159973

**Special Notes:**

- Specialized in biodiversity and ecological data
- Links data directly to publications
- Handles occurrence data and species distributions

TU Dresden Opara
^^^^^^^^^^^^^^^^

**Description:** Open Access Repository and Archive for research data of Saxon universities with 10-year archiving guarantee. Supports DSpace 7.x with comprehensive metadata management.

**Website:** https://opara.zih.tu-dresden.de/

**DOI Prefix:** ``10.25532/OPARA``

**Supported Identifier Formats:**

- DOI: ``10.25532/OPARA-581``
- DOI URL: ``https://doi.org/10.25532/OPARA-581``
- Handle URL: ``https://opara.zih.tu-dresden.de/xmlui/handle/123456789/123``
- Item URL: ``https://opara.zih.tu-dresden.de/xmlui/handle/123456789/123``
- UUID: ``a1b2c3d4-e5f6-7890-abcd-ef1234567890``

**Example:**

.. code-block:: bash

   python -m geoextent -b -t 10.25532/OPARA-581

**Special Notes:**

- Full DSpace 7.x REST API integration
- Handles complex ZIP archives with nested directories
- Supports multiple shapefiles in single archive
- Size filtering and geospatial file filtering fully supported

Usage Examples
--------------

Single Provider
^^^^^^^^^^^^^^^

Extract from a Zenodo dataset::

   python -m geoextent -b -t 10.5281/zenodo.4593540

Multiple Providers
^^^^^^^^^^^^^^^^^^

Mix resources from different providers::

   python -m geoextent -b -t \
       10.5281/zenodo.4593540 \
       10.25532/OPARA-581 \
       https://osf.io/4xe6z/

Returns a merged bounding box covering all resources.

With Download Control
^^^^^^^^^^^^^^^^^^^^^

Limit download size and skip non-geospatial files::

   python -m geoextent -b \
       --max-download-size 100MB \
       --download-skip-nogeo \
       --max-download-workers 8 \
       10.5281/zenodo.7080016

Provider Selection
------------------

Geoextent automatically detects the appropriate provider based on:

1. **DOI prefix matching** - Most reliable method
2. **URL pattern matching** - For direct repository URLs
3. **Known host detection** - For repository-specific domains

The first matching provider is used. If no provider matches, an error is returned.

See Also
--------

- :doc:`quickstart` - Get started with repository extraction
- :doc:`examples` - Detailed repository extraction examples
- :doc:`advanced-features` - Download control and filtering options
- :doc:`howto/api` - Python API for repository extraction
