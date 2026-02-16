
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

- **New Features**

  - Add metadata-only extraction for InvenioRDM instances (``metadata.locations`` GeoJSON, ``metadata.dates``)
  - Implement metadata-only extraction for Figshare provider (``download_data=False`` / ``--no-data-download``), supporting ``--metadata-first`` strategy (:issue:`68`)
  - Expand Figshare provider to support institutional portal URLs (``*.figshare.com``, e.g. ``springernature.figshare.com``, ``monash.figshare.com``)
  - Add ``--time-format`` CLI option and ``time_format`` API parameter for configurable temporal extent output format: date-only (default), ISO 8601, or custom strftime strings (:issue:`39`)
  - Add ``--metadata-first`` CLI flag and ``metadata_first`` API parameter for smart metadata-then-download extraction strategy: tries metadata-only extraction first if the provider supports it, falls back to data download if metadata yields no results
  - Extract temporal extent from raster files: NetCDF CF time dimensions, GeoTIFF ``TIFFTAG_DATETIME``, ACDD ``time_coverage_start/end`` global attributes, and band-level ``ACQUISITIONDATETIME`` (IMAGERY domain) (:issue:`22`)
  - Add ``--assume-wgs84`` CLI flag and ``assume_wgs84`` API parameter to explicitly enable WGS84 fallback for ungeoreferenced rasters (disabled by default)
  - Add support for Esri File Geodatabase (``.gdb``) format via GDAL's OpenFileGDB driver

- **Bug Fixes**

  - Skip raster files with pixel-based coordinates (outside WGS84 bounds) instead of merging them into geographic extents
  - Validate bounding boxes against WGS84 coordinate ranges before including in results
  - Reject vector files with projected coordinates falsely reported as WGS84 (e.g., GeoJSON files without CRS declaration)

- **Improvements**

  - Use GDAL CSV driver open options for coordinate column detection, supporting GDAL column naming conventions (``X``/``Y``, ``Easting``/``Northing``) and CSVT sidecar files (:issue:`53`)
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
