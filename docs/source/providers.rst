Content Providers
==================

Geoextent supports extracting geospatial data from 16 research data repositories (including 10 Dataverse instances) and Wikidata. All providers support URL-based extraction, and return merged geometries when processing multiple resources.

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
| 4TU.ResearchData  | 10.4121             | 10.4121/uuid:8ce9d22a-...             |
+-------------------+---------------------+----------------------------------------+
| Dryad             | 10.5061/dryad       | 10.5061/dryad.0k6djhb7x               |
+-------------------+---------------------+----------------------------------------+
| PANGAEA           | 10.1594/PANGAEA     | 10.1594/PANGAEA.734969                |
+-------------------+---------------------+----------------------------------------+
| OSF               | 10.17605/OSF.IO     | 10.17605/OSF.IO/ABC123                |
+-------------------+---------------------+----------------------------------------+
| Dataverse         | Varies by instance  | 10.7910/DVN/123456                    |
+-------------------+---------------------+----------------------------------------+
| ioerDATA          | 10.71830            | 10.71830/VDMUWW                        |
+-------------------+---------------------+----------------------------------------+
| heiDATA           | 10.11588/DATA       | 10.11588/DATA/TJNQZG                  |
+-------------------+---------------------+----------------------------------------+
| Edmond            | 10.17617            | 10.17617/3.QZGTDU                     |
+-------------------+---------------------+----------------------------------------+
| GFZ Data Services | 10.5880/GFZ         | 10.5880/GFZ.2.1.2020.001              |
+-------------------+---------------------+----------------------------------------+
| Pensoft           | 10.3897             | 10.3897/BDJ.13.e159973                |
+-------------------+---------------------+----------------------------------------+
| TU Dresden Opara  | 10.25532/OPARA      | 10.25532/OPARA-581                    |
+-------------------+---------------------+----------------------------------------+
| Senckenberg       | 10.12761/sgn        | 10.12761/sgn.2018.10225               |
+-------------------+---------------------+----------------------------------------+
| Mendeley Data     | 10.17632            | 10.17632/ybx6zp2rfp.1                 |
+-------------------+---------------------+----------------------------------------+
| Wikidata          | Q-numbers / URLs    | Q64                                    |
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

4TU.ResearchData
^^^^^^^^^^^^^^^^

**Description:** Research data repository of the four Dutch Universities of Technology (TU Delft, TU Eindhoven, University of Twente, Wageningen University & Research). Based on the open-source Djehuty platform with a Figshare-compatible API. Supports both metadata-only and full data download extraction.

**Website:** https://data.4tu.nl/

**DOI Prefix:** ``10.4121``

**Supported Identifier Formats:**

- DOI (legacy): ``10.4121/uuid:8ce9d22a-9aa4-41ea-9299-f44efa9c8b75``
- DOI (new-style): ``10.4121/19361018.v2``
- DOI URL: ``https://doi.org/10.4121/uuid:8ce9d22a-9aa4-41ea-9299-f44efa9c8b75``
- Dataset URL (new): ``https://data.4tu.nl/datasets/61e28011-f96d-4b01-900e-15145b77ee59/2``
- Article URL (legacy): ``https://data.4tu.nl/articles/_/12707150/1``

**Example (Data Download):**

.. code-block:: bash

   # Download data files and extract spatial extent from their contents
   python -m geoextent -b -t https://data.4tu.nl/articles/_/12707150/1

**Example (Metadata Only):**

.. code-block:: bash

   # Extract extent from repository metadata without downloading data files
   python -m geoextent -b --no-download-data https://data.4tu.nl/articles/_/12707150/1

**Python API Examples:**

.. code-block:: python

   import geoextent.lib.extent as geoextent

   # Data download mode: downloads files and extracts extent from file contents
   result = geoextent.fromRemote(
       'https://data.4tu.nl/articles/_/12707150/1',
       bbox=True, tbox=False, download_data=True
   )

   # Metadata-only mode: uses repository metadata (no file download)
   result = geoextent.fromRemote(
       'https://data.4tu.nl/articles/_/12707150/1',
       bbox=True, tbox=True, download_data=False
   )

**Special Notes:**

- Uses a Figshare-compatible API (Djehuty platform) but with its own domain and DOI prefix
- Handles both new-style UUID identifiers and legacy numeric article IDs
- Supports ``--no-download-data`` for metadata-only extraction (limited spatial information from repository metadata)
- Full support for download size limiting (``--max-download-size``), geospatial file filtering (``--download-skip-nogeo``), and parallel downloads (``--max-download-workers``)

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

**DOI Prefix:** Varies by Dataverse instance

**Supported Dataverse Instances:**

+----------------------------+------------------------------+--------------------+
| Instance                   | Host                         | DOI Prefix         |
+============================+==============================+====================+
| Harvard Dataverse          | dataverse.harvard.edu        | 10.7910/DVN        |
+----------------------------+------------------------------+--------------------+
| DataverseNL                | dataverse.nl                 | 10.34894           |
+----------------------------+------------------------------+--------------------+
| DataverseNO                | dataverse.no                 | 10.18710           |
+----------------------------+------------------------------+--------------------+
| UNC Dataverse              | dataverse.unc.edu            | 10.5064            |
+----------------------------+------------------------------+--------------------+
| UVA Library Dataverse      | data.library.virginia.edu    | (varies)           |
+----------------------------+------------------------------+--------------------+
| Recherche Data Gouv        | recherche.data.gouv.fr       | (varies)           |
+----------------------------+------------------------------+--------------------+
| ioerDATA                   | data.fdz.ioer.de             | 10.71830           |
+----------------------------+------------------------------+--------------------+
| heiDATA                    | heidata.uni-heidelberg.de    | 10.11588/DATA      |
+----------------------------+------------------------------+--------------------+
| Edmond                     | edmond.mpg.de                | 10.17617           |
+----------------------------+------------------------------+--------------------+
| Demo DataverseNL           | demo.dataverse.nl            | (varies)           |
+----------------------------+------------------------------+--------------------+

**Supported Identifier Formats:**

- DOI: ``10.7910/DVN/ABCDEF``
- DOI URL: ``https://doi.org/10.7910/DVN/ABCDEF``
- Dataverse URL: ``https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/ABCDEF``

**Example:**

.. code-block:: bash

   python -m geoextent -b -t 10.7910/DVN/ABCDEF

**Special Notes:**

- Supports 10 Dataverse instances (see table above)
- Automatically skips restricted files that require authentication
- Handles complex dataset structures
- API-based metadata and file retrieval

ioerDATA
^^^^^^^^

**Description:** Research data repository of the Leibniz Institute of Ecological Urban and Regional Development (IOER), hosted on Dataverse. Specializes in urban and regional development, land use monitoring, and spatial analysis data for Germany and Europe.

**Website:** https://data.fdz.ioer.de/

**DOI Prefix:** ``10.71830``

**Supported Identifier Formats:**

- DOI: ``10.71830/VDMUWW``
- DOI URL: ``https://doi.org/10.71830/VDMUWW``
- ioerDATA URL: ``https://data.fdz.ioer.de/dataset.xhtml?persistentId=doi:10.71830/VDMUWW``

**Example:**

.. code-block:: bash

   python -m geoextent -b 10.71830/VDMUWW

**Special Notes:**

- Standard Dataverse instance (uses Dataverse provider internally)
- Some datasets have restricted files requiring authentication; these are automatically skipped
- Specializes in German urban/regional development and land use data
- Uses the same Dataverse API as all other Dataverse instances

heiDATA
^^^^^^^

**Description:** Research data repository of Heidelberg University, hosted on Dataverse. Part of the NFDI4Earth initiative. Provides access to research data across multiple disciplines, with a focus on geosciences, environmental science, and digital humanities.

**Website:** https://heidata.uni-heidelberg.de/

**DOI Prefix:** ``10.11588/DATA``

**Supported Identifier Formats:**

- DOI: ``10.11588/DATA/TJNQZG``
- DOI URL: ``https://doi.org/10.11588/DATA/TJNQZG``
- heiDATA URL: ``https://heidata.uni-heidelberg.de/dataset.xhtml?persistentId=doi:10.11588/DATA/TJNQZG``

**Example:**

.. code-block:: bash

   python -m geoextent -b 10.11588/DATA/TJNQZG

**Special Notes:**

- Standard Dataverse instance (uses Dataverse provider internally)
- Has the NFDI4Earth Label for geoscience data
- Supports both open access and restricted datasets
- Uses the same Dataverse API as all other Dataverse instances

Edmond
^^^^^^

**Description:** Research data repository of the Max Planck Society, hosted on Dataverse. Provides open access to research data from Max Planck Institutes across all scientific disciplines, including earth sciences, chemistry, and biogeochemistry.

**Website:** https://edmond.mpg.de/

**DOI Prefix:** ``10.17617``

**Supported Identifier Formats:**

- DOI: ``10.17617/3.QZGTDU``
- DOI URL: ``https://doi.org/10.17617/3.QZGTDU``
- Edmond URL: ``https://edmond.mpg.de/dataset.xhtml?persistentId=doi:10.17617/3.QZGTDU``

**Example:**

.. code-block:: bash

   python -m geoextent -b 10.17617/3.QZGTDU

**Special Notes:**

- Standard Dataverse instance (uses Dataverse provider internally)
- Hosts data from Max Planck Institutes worldwide
- Uses the same Dataverse API as all other Dataverse instances

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

Senckenberg
^^^^^^^^^^^

**Description:** CKAN-based data portal for Senckenberg Biodiversity and Climate Research Centre providing access to biodiversity, climate, and geoscience research data. **Primarily a metadata repository** with rich geospatial and temporal metadata but limited/restricted data files.

**Website:** https://dataportal.senckenberg.de/

**DOI Prefix:** ``10.12761/sgn``

**Supported Identifier Formats:**

- DOI: ``10.12761/sgn.2018.10268``
- DOI URL: ``https://doi.org/10.12761/sgn.2018.10268``
- Dataset URL: ``https://dataportal.senckenberg.de/dataset/as-sahabi-1``
- Dataset ID (name slug): ``as-sahabi-1``
- Dataset ID (UUID): ``00dda005-68c0-4e92-96e5-ceb68034f3ba``
- JSON-LD URL: ``https://dataportal.senckenberg.de/dataset/as-sahabi-1.jsonld``

**Example (Recommended - Metadata Only):**

.. code-block:: bash

   # Extract spatial and temporal extent from metadata
   python -m geoextent -b -t --no-download-data 10.12761/sgn.2018.10268

**Output:** Bounding box for Ecuador region and temporal extent from 2014-05-01 to 2015-12-30

**Special Notes:**

- **Best Practice:** Always use ``--no-download-data`` for metadata-only extraction
- Built on CKAN (Comprehensive Knowledge Archive Network) platform
- Extracts both spatial extent (bounding box) and temporal extent (date ranges) from metadata
- Supports both open access and metadata-only restricted datasets
- Rich taxonomic, spatial, and temporal coverage metadata
- Metadata extraction is fast and does not require downloading data files
- Full filtering and size limiting capabilities available when data files exist

Mendeley Data
^^^^^^^^^^^^^

**Description:** Elsevier-hosted generalist research data repository and part of the NIH Generalist Repository Ecosystem Initiative (GREI). Supports sharing, discovering, and citing research data across all disciplines with DOI assignment.

**Website:** https://data.mendeley.com/

**DOI Prefix:** ``10.17632``

**Supported Identifier Formats:**

- DOI: ``10.17632/ybx6zp2rfp.1``
- DOI URL: ``https://doi.org/10.17632/ybx6zp2rfp.1``
- Mendeley Data URL: ``https://data.mendeley.com/datasets/ybx6zp2rfp/1``

**Example:**

.. code-block:: bash

   python -m geoextent -b 10.17632/ybx6zp2rfp.1

**Special Notes:**

- Uses unauthenticated public API (no OAuth tokens required)
- No geospatial metadata available; requires downloading data files for extent extraction
- Full support for download size limiting and geospatial file filtering
- Parallel downloads supported

Wikidata
^^^^^^^^

**Description:** Free, collaborative, multilingual knowledge base operated by the Wikimedia Foundation. Contains structured geographic data for millions of entities including countries, cities, parks, rivers, and other geographic features. Geoextent extracts bounding boxes from Wikidata's coordinate properties via the SPARQL endpoint.

**Website:** https://www.wikidata.org/

**Identifier Format:** Q-numbers (e.g., ``Q64``) or Wikidata URLs

**Supported Identifier Formats:**

- Q-number: ``Q64``
- Wiki URL: ``https://www.wikidata.org/wiki/Q64``
- Entity URI: ``http://www.wikidata.org/entity/Q64``

**Coordinate Extraction:**

1. **Extreme coordinates** (P1332-P1335): northernmost, southernmost, easternmost, westernmost points — used to construct a bounding box
2. **Coordinate location** (P625): single or multiple point locations — used as fallback when extreme coordinates are not available

**Example:**

.. code-block:: bash

   # Extract bbox for Berlin
   python -m geoextent -b Q64

   # Using Wikidata URL
   python -m geoextent -b https://www.wikidata.org/wiki/Q64

   # Multiple Wikidata items (merged bbox)
   python -m geoextent -b Q64 Q35 Q60786916

**Special Notes:**

- **Metadata-only provider**: Extracts coordinates from Wikidata SPARQL endpoint, no data files are downloaded
- The ``--no-download-data`` flag is accepted but has no effect (there are no data files)
- Supports multiple Wikidata items in a single call, returning a merged bounding box
- When only P625 point coordinates are available, the bounding box is computed from all available points
- For entities with a single P625 point, a zero-extent bounding box (point) is returned

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
