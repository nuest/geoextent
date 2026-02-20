Content Providers
==================

Geoextent supports extracting geospatial data from 30 research data repositories (including 10 Dataverse instances), Wikidata, any STAC catalog, and any CKAN instance. All providers support URL-based extraction, and return merged geometries when processing multiple resources.

Overview
--------

All content providers support:

- **DOI-based extraction** - Use DOIs directly or via resolver URLs
- **URL-based extraction** - Use direct repository URLs
- **Merged geometry output** - Multiple resources combined into single extent
- **Download size limiting** - Control bandwidth with ``--max-download-size``
- **File filtering** - Skip non-geospatial files with ``--download-skip-nogeo``
- **Parallel downloads** - Speed up multi-file downloads with ``--max-download-workers``
- **Metadata-first strategy** - Try metadata extraction first, fall back to data download with ``--metadata-first``

Metadata-First Extraction
~~~~~~~~~~~~~~~~~~~~~~~~~

Some providers (Arctic Data Center, Figshare, 4TU.ResearchData, Senckenberg, PANGAEA, BGR, SEANOE, UKCEH, GBIF, DEIMS-SDR, HALO DB, GDI-DE, STAC, CKAN, Wikidata) can extract geospatial extents directly from repository metadata without downloading data files. The ``--metadata-first`` flag leverages this for a smart two-phase strategy:

1. **Phase 1 (metadata):** If the provider supports metadata extraction, try metadata-only extraction first (fast, no file downloads).
2. **Phase 2 (fallback):** If metadata didn't yield the requested extents, or if the provider doesn't support metadata, fall back to downloading and processing data files.

This is especially useful when processing multiple providers in batch:

.. code-block:: bash

   # Senckenberg has metadata → uses metadata (fast); Zenodo has no metadata → downloads data
   python -m geoextent -b --metadata-first 10.12761/sgn.2018.10225 10.5281/zenodo.4593540

.. code-block:: python

   import geoextent.lib.extent as geoextent

   result = geoextent.fromRemote(
       '10.12761/sgn.2018.10225',
       bbox=True, metadata_first=True
   )
   print(result['extraction_method'])  # 'metadata' or 'download'

The result includes an ``extraction_method`` field indicating which strategy was used: ``"metadata"`` (fast, from repository metadata) or ``"download"`` (full data download and extraction).

**Note:** ``--metadata-first`` and ``--no-download-data`` are mutually exclusive. Use ``--no-download-data`` if you want metadata-only extraction without any fallback.

Automatic Metadata Fallback
~~~~~~~~~~~~~~~~~~~~~~~~~~~

When downloading data files from a provider, some repositories may have files disabled or unavailable (e.g., GEO Knowledge Hub packages with ``"files": {"enabled": false}``). In these cases, the download succeeds but yields an empty folder, and no spatial extent can be extracted.

By default, geoextent automatically detects this situation and falls back to metadata-only extraction if the provider supports it. This happens transparently without any user action required.

.. code-block:: bash

   # GKHub package with files disabled -- automatically uses metadata fallback
   python -m geoextent -b https://gkhub.earthobservations.org/packages/msaw9-hzd25

.. code-block:: python

   import geoextent.lib.extent as geoextent

   result = geoextent.fromRemote(
       'https://gkhub.earthobservations.org/packages/msaw9-hzd25',
       bbox=True
   )
   print(result['extraction_method'])  # 'metadata_fallback'

The result includes ``extraction_method: "metadata_fallback"`` to indicate that the automatic fallback was used.

To disable this behavior, use ``--no-metadata-fallback`` on the CLI or ``metadata_fallback=False`` in the Python API:

.. code-block:: bash

   python -m geoextent -b --no-metadata-fallback https://gkhub.earthobservations.org/packages/msaw9-hzd25

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
| RADAR             | 10.35097            | 10.35097/tvn5vujqfvf99f32              |
+-------------------+---------------------+----------------------------------------+
| Arctic Data Center| 10.18739            | 10.18739/A2Z892H2J                     |
+-------------------+---------------------+----------------------------------------+
| SEANOE            | 10.17882            | 10.17882/105467                        |
+-------------------+---------------------+----------------------------------------+
| UKCEH (EIDC)      | 10.5285             | 10.5285/dd35316a-...                   |
+-------------------+---------------------+----------------------------------------+
| GDI-DE            | UUIDs / URLs        | geoportal.de/Metadata/{uuid}           |
+-------------------+---------------------+----------------------------------------+
| STAC              | Collection URLs     | https://{host}/collections/{id}        |
+-------------------+---------------------+----------------------------------------+
| CKAN (any)        | Dataset URLs        | https://{host}/dataset/{id}            |
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

**Description:** Online open access repository for preserving and sharing research outputs with DOI assignment and altmetrics. Provides 20GB free private space and unlimited public sharing. Figshare also powers many institutional research data portals.

**Website:** https://figshare.com/

**DOI Prefix:** ``10.6084/m9.figshare``

**Supported Identifier Formats:**

- DOI: ``10.6084/m9.figshare.12345678``
- DOI URL: ``https://doi.org/10.6084/m9.figshare.12345678``
- Figshare URL: ``https://figshare.com/articles/dataset/title/12345678``
- Institutional portal URL: ``https://springernature.figshare.com/articles/dataset/title/12345678``
- Institutional portal URL: ``https://ices-library.figshare.com/articles/dataset/title/12345678``
- API URL: ``https://api.figshare.com/v2/articles/12345678``

**Example (Data Download):**

.. code-block:: bash

   # Download data files and extract spatial extent from their contents
   python -m geoextent -b -t https://figshare.com/articles/dataset/London_boroughs/11373984

   # Institutional portal (ICES Library - shapefiles archive)
   python -m geoextent -b https://ices-library.figshare.com/articles/dataset/HELCOM_request_2022_for_spatial_data_layers_on_effort_fishing_intensity_and_fishing_footprint_for_the_years_2016-2021/20310255

**Example (Metadata Only):**

.. code-block:: bash

   # Extract temporal extent from repository metadata without downloading data files
   python -m geoextent -b -t --no-download-data https://figshare.com/articles/dataset/Country_centroids/5902369

   # USDA Ag Data Commons - has geospatial metadata (GeoJSON in custom fields)
   python -m geoextent -b --no-download-data https://api.figshare.com/v2/articles/30753383

**Python API Examples:**

.. code-block:: python

   import geoextent.lib.extent as geoextent

   # Data download mode: downloads files and extracts extent from file contents
   result = geoextent.fromRemote(
       'https://figshare.com/articles/dataset/London_boroughs/11373984',
       bbox=True, tbox=True, download_data=True
   )

   # Metadata-only mode: uses published_date for temporal extent
   result = geoextent.fromRemote(
       'https://figshare.com/articles/dataset/Country_centroids/5902369',
       bbox=True, tbox=True, download_data=False
   )

   # Metadata-first strategy: tries metadata first, falls back to data download
   result = geoextent.fromRemote(
       'https://figshare.com/articles/dataset/Country_centroids/5902369',
       bbox=True, tbox=True, metadata_first=True
   )

**Special Notes:**

- Full support for size limiting and file filtering
- API-based file metadata retrieval
- Supports private and public datasets (public only accessible)
- Supports ``--no-download-data`` for metadata-only extraction (temporal extent from ``published_date``; spatial extent available when portals provide geolocation metadata)
- Supports ``--metadata-first`` strategy for smart metadata-then-download extraction
- Recognizes institutional portal URLs (``*.figshare.com``), e.g. ``springernature.figshare.com``, ``ices-library.figshare.com``
- Some institutional portals (e.g. USDA Ag Data Commons) provide rich geospatial metadata including GeoJSON coverage polygons in ``custom_fields``

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
   python -m geoextent -b https://data.4tu.nl/datasets/3035126d-ee51-4dbd-a187-5f6b0be85e9f/1

**Example (Metadata Only):**

.. code-block:: bash

   # Extract extent from repository metadata without downloading data files
   python -m geoextent -b --no-download-data https://data.4tu.nl/articles/_/12707150/1
   python -m geoextent -b --no-download-data https://data.4tu.nl/datasets/3035126d-ee51-4dbd-a187-5f6b0be85e9f/1

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

RADAR
^^^^^

**Description:** Cross-disciplinary research data repository operated by FIZ Karlsruhe for archiving and publishing German research data. Assigns DOIs via DataCite and delivers all datasets as ``.tar`` archives.

**Website:** https://www.radar-service.eu/

**DOI Prefix:** ``10.35097``

**Supported Identifier Formats:**

- DOI: ``10.35097/tvn5vujqfvf99f32``
- DOI URL: ``https://doi.org/10.35097/tvn5vujqfvf99f32``
- RADAR URL: ``https://www.radar-service.eu/radar/en/dataset/tvn5vujqfvf99f32``
- KIT URL: ``https://radar.kit.edu/radar/en/dataset/tvn5vujqfvf99f32``

**Example:**

.. code-block:: bash

   python -m geoextent -b -t 10.35097/tvn5vujqfvf99f32

**Special Notes:**

- All datasets are delivered as a single ``.tar`` archive (no individual file downloads)
- Backend API provides file listing before download for size estimation and geospatial file detection
- Supports download size limiting and geospatial file filtering
- Multiple hosting domains: ``www.radar-service.eu`` and ``radar.kit.edu``

Arctic Data Center
^^^^^^^^^^^^^^^^^^

**Description:** The primary data and software repository for NSF-funded Arctic research, operated by the National Center for Ecological Analysis and Synthesis (NCEAS). Built on DataONE/Metacat infrastructure with rich structured geospatial and temporal metadata in its Solr index.

**Website:** https://arcticdata.io/

**DOI Prefix:** ``10.18739``

**Supported Identifier Formats:**

- DOI: ``10.18739/A2Z892H2J``
- DOI URL: ``https://doi.org/10.18739/A2Z892H2J``
- Catalog URL: ``https://arcticdata.io/catalog/view/doi%3A10.18739%2FA2Z892H2J``
- URN UUID: ``urn:uuid:054b4c9a-8be1-4d28-8724-5e2beb0ce4e6``

**Example:**

.. code-block:: bash

   python -m geoextent -b -t 10.18739/A2Z892H2J

**Special Notes:**

- Supports metadata-only extraction (every dataset has bounding coordinates and temporal coverage in its Solr index)
- Supports both DOI and URN UUID identifiers
- Individual file downloads via DataONE object endpoint
- Parallel downloads supported

SEANOE
^^^^^^

**Description:** SEANOE (SEA scieNtific Open data Edition) is a marine science data repository operated by Ifremer/SISMER (France). It publishes open-access oceanographic, marine biology, and geoscience datasets with DOI prefix 10.17882.

**Website:** https://www.seanoe.org/

**DOI Prefix:** ``10.17882``

**Supported Identifier Formats:**

- DOI: ``10.17882/105467``
- DOI URL: ``https://doi.org/10.17882/105467``
- SEANOE URL: ``https://www.seanoe.org/data/00943/105467/``

**Example (Metadata Only):**

.. code-block:: bash

   # French Mediterranean CTD data — bbox and temporal extent from SEANOE metadata
   python -m geoextent -b -t --no-download-data 10.17882/105467

   # Bowhead whale biologging — open in geojson.io
   python -m geoextent -b -t --geojsonio --no-download-data 10.17882/112127

**Example (Data Download):**

.. code-block:: bash

   # Ireland coastline REI — download data files and extract extent
   python -m geoextent -b 10.17882/109463

**Python API Examples:**

.. code-block:: python

   import geoextent.lib.extent as geoextent

   # Metadata-only: uses SEANOE REST API for bbox and temporal extent
   result = geoextent.fromRemote(
       '10.17882/105467',
       bbox=True, tbox=True, download_data=False
   )

   # Data download mode: downloads open-access files and extracts extent
   result = geoextent.fromRemote(
       '10.17882/109463',
       bbox=True, download_data=True
   )

**Special Notes:**

- Rich structured metadata via ``https://www.seanoe.org/api/find-by-id/{id}`` REST API
- Supports ``--no-download-data`` for metadata-only extraction (geographic bounding boxes and temporal ranges from API)
- Data files can be downloaded and processed for more precise extent extraction
- Only open-access files are downloaded; restricted files are automatically skipped
- Full support for download size limiting, geospatial file filtering, and parallel downloads

UKCEH (EIDC)
^^^^^^^^^^^^^

**Description:** UKCEH (UK Centre for Ecology & Hydrology) operates the Environmental Information Data Centre (EIDC), publishing environmental science datasets including water chemistry, land cover, biomass, and atmospheric data. The catalogue provides structured metadata via a JSON API with bounding boxes and temporal extents.

**Website:** https://catalogue.ceh.ac.uk/

**DOI Prefix:** ``10.5285``

**Supported Identifier Formats:**

- DOI: ``10.5285/dd35316a-cecc-4f6d-9a21-74a0f6599e9e``
- DOI URL: ``https://doi.org/10.5285/dd35316a-cecc-4f6d-9a21-74a0f6599e9e``
- Catalogue URL: ``https://catalogue.ceh.ac.uk/documents/dd35316a-cecc-4f6d-9a21-74a0f6599e9e``

**Example (Metadata Only):**

.. code-block:: bash

   # Blelham Tarn water chemistry — bbox and temporal extent from catalogue metadata
   python -m geoextent -b -t --no-download-data 10.5285/dd35316a-cecc-4f6d-9a21-74a0f6599e9e

**Example (Data Download):**

.. code-block:: bash

   # Blelham Tarn water chemistry — download CSV data and extract extent
   python -m geoextent -b -t 10.5285/dd35316a-cecc-4f6d-9a21-74a0f6599e9e

**Python API Examples:**

.. code-block:: python

   import geoextent.lib.extent as geoextent

   # Metadata-only: uses catalogue JSON API for bbox and temporal extent
   result = geoextent.fromRemote(
       '10.5285/dd35316a-cecc-4f6d-9a21-74a0f6599e9e',
       bbox=True, tbox=True, download_data=False
   )

   # Data download mode: downloads files and extracts extent
   result = geoextent.fromRemote(
       '10.5285/dd35316a-cecc-4f6d-9a21-74a0f6599e9e',
       bbox=True, tbox=True, download_data=True
   )

**Special Notes:**

- Dual download pattern: Apache datastore directory listing (selective file download) or data-package ZIP (all-or-nothing)
- Datastore listing tried first to enable selective file download and size filtering; falls back to data-package ZIP
- Supports ``--no-download-data`` for metadata-only extraction (bounding boxes and temporal ranges from catalogue API)
- Full support for download size limiting, geospatial file filtering, and parallel downloads
- Dataset identifiers are UUIDs (e.g., ``dd35316a-cecc-4f6d-9a21-74a0f6599e9e``)

GDI-DE (geoportal.de)
^^^^^^^^^^^^^^^^^^^^^

**Description:** GDI-DE (Geodateninfrastruktur Deutschland / Spatial Data Infrastructure Germany) is the national spatial data infrastructure catalogue with 771,000+ records, aggregating metadata from German federal, state, and municipal agencies (BKG, DWD, DLR, etc.).

**Website:** https://www.geoportal.de/

**Identifier Format:** UUIDs or geoportal.de URLs (no DOIs)

**Supported Identifier Formats:**

- Landing page URL: ``https://www.geoportal.de/Metadata/{uuid}``
- CSW URL: ``https://gdk.gdi-de.org/gdi-de/srv/eng/csw?...Id={uuid}``
- Bare UUID: ``75987CE0-AA66-4445-AC44-068B98390E89``

**Example (Metadata Only):**

.. code-block:: bash

   # Heavy rain hazard map — bbox from GDI-DE catalogue metadata
   python -m geoextent -b --no-download-data https://www.geoportal.de/Metadata/75987CE0-AA66-4445-AC44-068B98390E89

   # Forest canopy cover loss — bbox and temporal extent from bare UUID
   python -m geoextent -b -t --no-download-data cdb2c209-7e08-4f4c-b500-69de926e3023

**Python API Examples:**

.. code-block:: python

   import geoextent.lib.extent as geoextent

   # Metadata-only: uses GDI-DE CSW 2.0.2 API for bbox and temporal extent
   result = geoextent.fromRemote(
       'https://www.geoportal.de/Metadata/75987CE0-AA66-4445-AC44-068B98390E89',
       bbox=True, tbox=True, download_data=False
   )

**Special Notes:**

- **Metadata-only provider**: GDI-DE is a catalogue pointing to external WMS/WFS/Atom services; no data files are downloaded
- Uses OGC CSW 2.0.2 endpoint with ISO 19115/19139 metadata (same standard as BGR, BAW, MDI-DE)
- The ``--no-download-data`` flag is accepted but has no effect (there are no data files)
- Supports bare UUIDs verified against the GDI-DE CSW catalog

STAC (SpatioTemporal Asset Catalog)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Description:** STAC (SpatioTemporal Asset Catalog) is an OGC Community Standard for describing geospatial information. STAC Collections contain pre-computed aggregate bounding boxes and temporal intervals, making them ideal for fast metadata-only extraction. Geoextent supports any STAC-compliant API.

**Website:** https://stacspec.org/

**Identifier Format:** STAC Collection URLs (no DOIs)

**Supported Identifier Formats:**

- Collection URL: ``https://{host}/stac/v1/collections/{id}``
- Collection URL: ``https://{host}/collections/{id}``
- Known STAC API hosts are matched instantly (Element84, DLR, Terradue, WorldPop, Lantmateriet, etc.)
- Unknown hosts with ``/stac/`` in the URL path are also matched
- Fallback: any URL returning JSON with a ``stac_version`` field

**Example (Metadata Only):**

.. code-block:: bash

   # US National Agriculture Imagery (Element84 Earth Search)
   python -m geoextent -b -t https://earth-search.aws.element84.com/v1/collections/naip

   # German forest structure (DLR EOC STAC API)
   python -m geoextent -b -t https://geoservice.dlr.de/eoc/ogc/stac/v1/collections/FOREST_STRUCTURE_DE_COVER_P1Y

   # Switzerland population data (WorldPop)
   python -m geoextent -b -t https://api.stac.worldpop.org/collections/CHE

   # Swedish orthophoto (Lantmateriet)
   python -m geoextent -b -t https://api.lantmateriet.se/stac-bild/v1/collections/orto-f2-2014

   # San Andreas Fault SAR data (Terradue)
   python -m geoextent -b -t https://gep-supersites-stac.terradue.com/collections/csk-san-andrea-supersite

**Python API Examples:**

.. code-block:: python

   import geoextent.lib.extent as geoextent

   # Extract bbox and temporal extent from STAC Collection
   result = geoextent.fromRemote(
       'https://earth-search.aws.element84.com/v1/collections/naip',
       bbox=True, tbox=True
   )
   print(result['bbox'])   # [17.0, -160.0, 50.0, -67.0] (NAIP US coverage)
   print(result['tbox'])   # ['2010-01-01', '2022-12-31']

   # Open-ended temporal range (end date is null)
   result = geoextent.fromRemote(
       'https://geoservice.dlr.de/eoc/ogc/stac/v1/collections/FOREST_STRUCTURE_DE_COVER_P1Y',
       bbox=True, tbox=True
   )
   print(result['tbox'])   # ['2017-01-01', None]

**Special Notes:**

- **Metadata-only provider**: Extracts pre-computed ``extent.spatial.bbox`` and ``extent.temporal.interval`` directly from STAC Collection JSON — no data files are downloaded
- The ``--no-download-data`` flag is accepted but has no effect (there are no data files)
- Supports content negotiation: if a URL returns HTML (e.g. OGC API with content negotiation), retries with ``?f=application/json``
- Handles open-ended temporal ranges where the end date is ``null`` (ongoing data collection)
- Supports STAC API v1.0 and v1.1

CKAN (Generic)
^^^^^^^^^^^^^^

**Description:** Generic provider for any CKAN (Comprehensive Knowledge Archive Network) instance. CKAN is the world's most widely-used open-source data management system, powering government open data portals and research data repositories worldwide. The generic CKAN provider supports metadata-only extraction (spatial extent from GeoJSON geometries, temporal extent from various field naming conventions) and data file downloads.

**Website:** https://ckan.org/

**Identifier Format:** Dataset URLs (no DOIs)

**Known CKAN Instances:**

+----------------------------+----------------------------------------------+
| Instance                   | Host                                         |
+============================+==============================================+
| GeoKur (TU Dresden)        | geokur-dmp.geo.tu-dresden.de                 |
+----------------------------+----------------------------------------------+
| UK data.gov.uk             | ckan.publishing.service.gov.uk               |
+----------------------------+----------------------------------------------+
| GovData.de                 | ckan.govdata.de                              |
+----------------------------+----------------------------------------------+
| Canada Open Data           | open.canada.ca                               |
+----------------------------+----------------------------------------------+
| Australia Open Data        | data.gov.au                                  |
+----------------------------+----------------------------------------------+
| US data.gov                | catalog.data.gov                             |
+----------------------------+----------------------------------------------+
| Ireland Open Data          | data.gov.ie                                  |
+----------------------------+----------------------------------------------+
| Singapore Open Data        | data.gov.sg                                  |
+----------------------------+----------------------------------------------+

Unknown CKAN hosts are automatically detected by probing the ``/api/3/action/status_show`` endpoint.

**Supported Identifier Formats:**

- Dataset URL: ``https://{ckan-host}/dataset/{dataset_id_or_name}``
- Subpath URL: ``https://{host}/data/en/dataset/{id}`` (e.g. Canada)

**Example (Metadata Only):**

.. code-block:: bash

   # GeoKur cropland extent — bbox and temporal from CKAN metadata (GeoJSON geometry + temporal_start/end)
   python -m geoextent -b -t --no-download-data https://geokur-dmp.geo.tu-dresden.de/dataset/cropland-extent

   # UK data.gov.uk — bbox from bbox-* extras pattern
   python -m geoextent -b --no-download-data https://ckan.publishing.service.gov.uk/dataset/bishkek-spatial-data

   # German GovData — spatial GeoJSON and temporal extent
   python -m geoextent -b -t --no-download-data https://ckan.govdata.de/dataset/a-spatially-distributed-sampling-of-rhine-surface-water-for-non-target-screening

**Example (Data Download):**

.. code-block:: bash

   # Ireland libraries — download Shapefile and extract bbox from file contents
   python -m geoextent -b https://data.gov.ie/dataset/libraries-dlr

   # Australia Gisborne — download GeoJSON and extract bbox from file contents
   python -m geoextent -b https://data.gov.au/dataset/gisborne-neighbourhood-character-precincts

**Python API Examples:**

.. code-block:: python

   import geoextent.lib.extent as geoextent

   # Metadata-only: uses CKAN API for bbox and temporal extent
   result = geoextent.fromRemote(
       'https://geokur-dmp.geo.tu-dresden.de/dataset/cropland-extent',
       bbox=True, tbox=True, download_data=False
   )

   # Data download: downloads files and extracts extent
   result = geoextent.fromRemote(
       'https://data.gov.ie/dataset/libraries-dlr',
       bbox=True, tbox=True, download_data=True
   )

   # Metadata-first strategy: tries metadata first, falls back to data download
   result = geoextent.fromRemote(
       'https://ckan.govdata.de/dataset/a-spatially-distributed-sampling-of-rhine-surface-water-for-non-target-screening',
       bbox=True, tbox=True, metadata_first=True
   )

**Special Notes:**

- **Recommended:** Use ``--metadata-first`` for CKAN datasets — many have rich catalogue metadata but data files may not contain geospatial content
- Spatial metadata supports: GeoJSON geometries (Polygon, MultiPolygon, Point), ``bbox-*`` extras (UK pattern), and ``west/south/east/north`` dict fields
- Temporal metadata supports 5 naming conventions across instances: ``temporal_start/end``, ``temporal-extent-begin/end``, ``temporal_coverage-from/to``, ``temporal_coverage_from/to``, ``time_period_coverage_start/end``
- Complex GeoJSON geometries are preserved for convex hull calculations (not simplified to bounding box rectangles)
- Automatic metadata fallback: if downloaded data files have no geospatial content, automatically falls back to catalogue metadata
- Senckenberg (``dataportal.senckenberg.de``) has a dedicated provider and is excluded from generic CKAN matching

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
