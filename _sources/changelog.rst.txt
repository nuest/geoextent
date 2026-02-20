
Changelog
=========

Unreleased
^^^^^^^^^^

- **New Content Providers**

  - Generalise Zenodo provider into InvenioRDM base provider supporting CaltechDATA, TU Wien, Frei-Data, GEO Knowledge Hub, TU Graz, Materials Cloud Archive, FDAT, DataPLANT ARChive, KTH, Prism, and NYU Ultraviolet (:issue:`81`)
  - Add Mendeley Data as content provider (:issue:`58`)
  - Add ioerDATA (Leibniz IOER) Dataverse instance support (:issue:`85`)
  - Add heiDATA (Heidelberg University) Dataverse instance support (:issue:`94`)
  - Add Edmond (Max Planck Society) Dataverse instance support (:issue:`93`)
  - Add Wikidata as content provider for extracting geographic extents from Wikidata items via SPARQL (:issue:`83`)
  - Add 4TU.ResearchData as content provider with support for both data download and metadata-only extraction (:issue:`92`)
  - Add RADAR (FIZ Karlsruhe) as content provider for cross-disciplinary German research data (:issue:`87`)
  - Add NSF Arctic Data Center as content provider with metadata-only and data download support (:issue:`90`)
  - Add DEIMS-SDR (Dynamic Ecological Information Management System) as metadata-only content provider for long-term ecological research sites and datasets, with support for dataset and site URLs, WKT geometry parsing (POINT, POLYGON, MULTIPOLYGON), and temporal ranges (:issue:`101`)
  - Add BAW (Bundesanstalt für Wasserbau) Datenrepository as content provider with CSW 2.0.2 metadata extraction via OWSLib, supporting DOIs (``10.48437/*``), landing page URLs, and bare UUIDs (:issue:`89`)
  - Add B2SHARE (EUDAT) as InvenioRDM instance, supporting DOIs (``10.23728/b2share.*``), record URLs, and old-style hex DOIs (:issue:`16`)
  - Add MDI-DE (Marine Daten-Infrastruktur Deutschland) as content provider with CSW 2.0.2 metadata extraction via OWSLib, WFS-based data download, and direct file download; supports NOKIS landing page URLs and bare UUIDs (:issue:`86`)
  - Add HALO DB (DLR) as metadata-only content provider for the HALO research aircraft database, extracting flight track geometry from the GeoJSON search API and temporal extent from dataset HTML pages (:issue:`88`)
  - Add GBIF (Global Biodiversity Information Facility) as content provider with metadata-only extraction from the Registry API and optional Darwin Core Archive (DwC-A) data download from institutional IPT servers; supports DOI prefixes 10.15468, 10.15470, 10.15472, 10.25607, 10.71819, 10.82144 and gbif.org dataset URLs (:issue:`62`)
  - Add SEANOE (SEA scieNtific Open data Edition) as content provider for marine science data from Ifremer/SISMER, with metadata-only extraction from the REST API (geographic bounding boxes, temporal extents) and data download of open-access files; supports DOI prefix 10.17882 and seanoe.org landing page URLs (:issue:`104`)
  - Add UKCEH (UK Centre for Ecology & Hydrology) EIDC as content provider with metadata-only extraction from the catalogue JSON API (bounding boxes, temporal extents) and dual data download pattern (Apache datastore listing or data-package ZIP); supports DOI prefix 10.5285 and catalogue.ceh.ac.uk URLs (:issue:`103`)
  - Add GDI-DE (Geodateninfrastruktur Deutschland / geoportal.de) as metadata-only content provider for the national German spatial data infrastructure catalogue (771,000+ records), with CSW 2.0.2 metadata extraction via OWSLib; supports geoportal.de landing page URLs and bare UUIDs (:issue:`84`)
  - Add generic CKAN content provider supporting any CKAN instance via dataset URL matching, with known-host fast matching and dynamic API discovery; includes GeoJSON spatial metadata parsing with geometry preservation for convex hull, multi-format temporal field support, and UK ``bbox-*`` extras pattern; known hosts include GeoKur TU Dresden, data.gov.uk, GovData.de, data.gov.au, and catalog.data.gov (:issue:`98`)
  - Add STAC (SpatioTemporal Asset Catalog) as metadata-only content provider, extracting spatial bounding boxes and temporal intervals directly from STAC Collection JSON; supports known STAC API hosts (Element84, DLR, Terradue, WorldPop, Lantmateriet, etc.), ``/stac/`` URL path patterns, JSON content-inspection fallback, and content negotiation for HTML/JSON servers (:issue:`25`)
  - Add NFDI4Earth Knowledge Hub as metadata-only content provider for the Cordra-based digital object repository (1.3M+ datasets), with SPARQL endpoint extraction (spatial WKT, temporal ranges) and Cordra REST API fallback; supports OneStop4All landing page URLs and direct Cordra object URLs; follows ``landingPage`` to other supported providers (:issue:`100`)

- **New Features**

  - Add metadata-only extraction for InvenioRDM instances (``metadata.locations`` GeoJSON, ``metadata.dates``)
  - Implement metadata-only extraction for Figshare provider (``download_data=False`` / ``--no-data-download``), supporting ``--metadata-first`` strategy (:issue:`68`)
  - Expand Figshare provider to support institutional portal URLs (``*.figshare.com``, e.g. ``springernature.figshare.com``, ``monash.figshare.com``)
  - Add ``--time-format`` CLI option and ``time_format`` API parameter for configurable temporal extent output format: date-only (default), ISO 8601, or custom strftime strings (:issue:`39`)
  - Add ``--metadata-first`` CLI flag and ``metadata_first`` API parameter for smart metadata-then-download extraction strategy: tries metadata-only extraction first if the provider supports it, falls back to data download if metadata yields no results
  - Add automatic metadata fallback: when data download yields no files and the provider supports metadata extraction, automatically fall back to metadata-only extraction (enabled by default, disable with ``--no-metadata-fallback`` or ``metadata_fallback=False``)
  - DEIMS-SDR provider now follows external DOIs/URLs to other supported providers (e.g., Zenodo, PANGAEA) for actual data extent extraction. Disable with ``--no-follow`` or ``follow=False``.
  - Extract temporal extent from raster files: NetCDF CF time dimensions, GeoTIFF ``TIFFTAG_DATETIME``, ACDD ``time_coverage_start/end`` global attributes, and band-level ``ACQUISITIONDATETIME`` (IMAGERY domain) (:issue:`22`)
  - Add ``--assume-wgs84`` CLI flag and ``assume_wgs84`` API parameter to explicitly enable WGS84 fallback for ungeoreferenced rasters (disabled by default)
  - Add support for Esri File Geodatabase (``.gdb``) format via GDAL's OpenFileGDB driver
  - All content providers now support interactive download size confirmation via ``--max-download-size``. When the total download exceeds the limit, the CLI prompts for confirmation instead of silently truncating. API: ``download_size_soft_limit=True`` in ``fromRemote()``.

- **Breaking Changes**

  - Drop support for bare numeric Zenodo record IDs (e.g., ``820562``); use DOI (``10.5281/zenodo.820562``) or URL (``https://zenodo.org/records/820562``) instead

- **Bug Fixes**

  - Skip raster files with pixel-based coordinates (outside WGS84 bounds) instead of merging them into geographic extents
  - Validate bounding boxes against WGS84 coordinate ranges before including in results
  - Reject vector files with projected coordinates falsely reported as WGS84 (e.g., GeoJSON files without CRS declaration)

- **Improvements**

  - Fix and enable skipped multi-input CLI tests, add convex hull geometry tests for 2–5 file inputs, and add documentation for multiple input processing
  - Use GDAL CSV driver open options for coordinate column detection, supporting GDAL column naming conventions (``X``/``Y``, ``Easting``/``Northing``) and CSVT sidecar files (:issue:`53`)
  - Add GeoCSV format support: recognise ``CoordX``/``CoordY`` column names (giswiki.ch GeoCSV spec), ``.prj`` sidecar files for CRS information, WKT polygon geometry columns, and EarthScope GeoCSV ``#``-prefixed metadata header lines (:issue:`52`)
  - Move content provider metadata into provider classes (``provider_info()`` classmethod), eliminating duplication in ``features.py``
  - Verify bare UUIDs against BGR CSW catalog and Opara DSpace API before accepting, preventing misrouting between providers
  - Correct 4TU.ResearchData platform description: uses Djehuty, not Figshare
  - Automatically skip restricted files in Dataverse downloads

0.12.0
^^^^^^

- **Breaking Changes**

  - Default coordinate order for plain bounding boxes is now EPSG:4326 native axis order: **(latitude, longitude)**
  - Bounding boxes are returned as ``[minlat, minlon, maxlat, maxlon]`` instead of ``[minlon, minlat, maxlon, maxlat]``
  - GeoJSON output always uses ``[longitude, latitude]`` coordinate order per `RFC 7946 <https://www.rfc-editor.org/rfc/rfc7946>`_
  - Add ``--legacy`` CLI flag and ``legacy=True`` Python API parameter to restore the previous ``[lon, lat]`` order for plain bounding boxes (does not affect GeoJSON output)

- **New Content Providers**

  - Add Senckenberg Biodiversity and Climate Research Centre data portal provider (:issue:`66`)
  - Support for CKAN-based repositories via new ``CKANProvider`` base class
  - Add BGR Geoportal content provider with ISO 19139 metadata extraction (:issue:`61`)

- **New Features**

  - Add support for world files (``.wld``, ``.jgw``, ``.pgw``, ``.tfw``, etc.) (:issue:`36`)
  - Add ``--keep-files`` option to preserve downloaded files for debugging
  - Dynamically generated supported formats list
  - Explicitly remove temp files on cleanup (:issue:`82`)

- **Bug Fixes**

  - Skip layers with degenerate extent ``[0,0,0,0]`` and emit a user-visible warning instead of silently including invalid coordinates
  - Fix resource leak for GeoPackage/SQLite-backed files (unclosed database connections)

- **Improvements**

  - Enable parallel test execution by default using ``pytest-xdist`` (:issue:`38`)
  - Refactor CRS extraction into shared utility function
  - Harden CSV handler: force CSV GDAL driver to prevent misidentification, add extension-based pre-filtering, improve geometry column detection
  - Optimize gazetteer queries to avoid duplicate API calls for closed polygon points
  - Suppress noisy pandas date-parsing warnings during temporal extent detection

0.11.0
^^^^^^

- Add ``--ext-metadata`` option to retrieve bibliographic metadata for DOIs from CrossRef and DataCite APIs
- Add ``--ext-metadata-method`` option to control metadata source (``auto``, ``all``, ``crossref``, ``datacite``)
- Add display names to file format handlers
- Fix unwanted coordinate flipping for GML bounding boxes with GDAL >= 3.2

0.10.0
^^^^^^

- ``fromRemote()`` now accepts both single identifiers (string) and multiple identifiers (list)
- Add ``--list-features`` CLI option and ``get_supported_features()`` Python API for discovering supported file formats and content providers
- Add ``validate_remote_identifier()`` and ``validate_file_format()`` validation functions

0.9.0
^^^^^

- **Content Providers**

  - Add TU Dresden Opara content provider supporting DSpace 7.x repositories (:issue:`77`)
  - Add GFZ Data Services as content provider (:issue:`17`)
  - Add Dataverse repository support (:issue:`57`)
  - Add support for OSF (Open Science Framework) (:issue:`19`)
  - Add support for Dryad and Figshare repositories
  - Add support for Pensoft journals (:issue:`64`)
  - Enhance PANGAEA provider with non-tabular data support and ZIP archive handling
  - Add download size limiting for repositories (:issue:`70`)
  - Add ``--no-data-download`` option for metadata-only extraction
  - Add ``--download-skip-nogeo`` option to skip non-geospatial files
  - Add ``--max-download-size``, ``--max-download-workers``, and ``--max-download-method`` options
  - Restructure regex patterns for better repository candidate detection

- **Output and Visualization**

  - Add extraction metadata to GeoJSON output (``geoextent_extraction`` field)
  - Add ``--no-metadata`` option to exclude extraction metadata from GeoJSON output
  - Add geojson.io URL generation (``--geojsonio``)
  - Add ``--browse`` option to open visualizations in default web browser
  - Add WKT and WKB output format support (:issue:`46`)
  - Add convex hull extraction (``--convex-hull``) (:issue:`37`)

- **CLI and Processing**

  - Add ``--no-subdirs`` option to control recursive directory processing (:issue:`55`)
  - Add support for processing multiple files with automatic extent merging
  - Add progress bars with ``--no-progress`` option to disable (:issue:`32`)
  - Add ``--quiet`` option to suppress all console messages
  - Add ``--placename`` option for geographic placename lookup via GeoNames, Nominatim, and Photon (:issue:`74`)
  - Add file filtering and parallel downloads (:issue:`75`)
  - Add FlatGeobuf format support (:issue:`43`)

- **Infrastructure**

  - Refactor CI workflows to use custom GDAL installation script instead of pygdal
  - Run code formatter (:issue:`54`)
  - Skip GDAL auxiliary files during directory processing

- Fix Figshare URL validation and download handling

0.8.0
^^^^^

- Move configuration from ``setup.py`` to ``pyproject.toml``

0.7.1
^^^^^

- Add DOI-based retrieval functions for Zenodo (:pr:`100`)
- Add export function ``--output`` for folders, ZIP files and repositories (:pr:`124`)

0.6.0
^^^^^

- Add details option ``--details`` for folders and ZIP files (:pr:`116`)

0.5.0
^^^^^

- Add support for spatial extent for ``osgeo`` files (via OGR/GDAL) with generic vector (GeoPackage, Shapefile, GeoJSON, GML, GPX, KML) and raster handling (GeoTIFF) (:pr:`87`, :pr:`99`)

0.4.0
^^^^^

- Add support for ZIP files and folders (:pr:`79`)

0.3.0
^^^^^

- Add debug option ``--debug`` and environment variable ``GEOEXTENT_DEBUG`` (:pr:`73`)
- Remove need for ``-input=`` for passing input paths in CLI (:pr:`73`)
- Switch to ``pygdal`` and update docs (:pr:`73`)

0.2.0
^^^^^

- Add dependencies to required software (:pr:`59`, :commit:`364692964fc34c467c21a7072e1eefb9d354fbb8`)
- Update documentation, now uses Sphinx and is online at https://o2r.info/geoextent/ (:pr:`67`, :pr:`65`, :pr:`64`, :pr:`62`)

0.1.0
^^^^^

- Initial release with core functionality
