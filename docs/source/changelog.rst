
Changelog
=========

0.9.0 (unreleased)
^^^^^^^^^^^^^^^^^^

- **New Content Providers**

  - Add Senckenberg Biodiversity and Climate Research Centre data portal provider
  - **Senckenberg is primarily a metadata repository** - most datasets contain rich geospatial and temporal metadata but limited/restricted data files
  - **Recommended usage**: Always use ``--no-download-data`` (metadata-only mode) for Senckenberg datasets to extract spatial and temporal extents from metadata without downloading files
  - Support for CKAN-based repositories via new ``CKANProvider`` base class
  - Senckenberg provider supports:

    - DOI format: ``10.12761/sgn.YYYY.NNNNN``
    - Dataset URLs: ``https://dataportal.senckenberg.de/dataset/{id}``
    - Dataset IDs (name slugs and UUIDs)
    - JSON-LD URLs: ``.jsonld`` metadata format

  - Extracts both spatial extent (bounding box) and temporal extent (date ranges) from CKAN metadata
  - Temporal extent extraction: Supports ``rangeOfDates`` (begin/end dates) and ``singleDateTime`` fields
  - Handles both open access and metadata-only restricted datasets
  - Full support for download size limiting, file filtering, and parallel downloads (when data files are available)
  - Example datasets:

    - ``10.12761/sgn.2018.10268`` - Complete spatial and temporal metadata (Ecuador, 2014-2015)
    - ``10.12761/sgn.2018.10225`` - Metadata with global extent
    - ``as-sahabi-1`` - Dataset with downloadable geospatial files

- **External Metadata Retrieval**

  - Add ``--ext-metadata`` option to retrieve bibliographic metadata for DOIs from CrossRef and DataCite APIs
  - Add ``--ext-metadata-method`` option to control metadata source selection:
    - ``auto`` (default): Try CrossRef first, then DataCite if CrossRef fails
    - ``all``: Query all sources and return all results
    - ``crossref``: Query CrossRef only
    - ``datacite``: Query DataCite only
  - Metadata fields extracted: title, authors, publisher, publication year, URL, license
  - Supports DOI input in multiple formats: plain DOI, DOI URL (https://doi.org/...), or doi: prefix
  - External metadata always returned as array structure (even if empty or single source)
  - New dependencies: ``crossref-commons``, ``datacite``
  - Integration tests included for real API connectivity

- **Multiple Remote Resource Extraction**

  - ``fromRemote()`` now accepts both single identifiers (string) and multiple identifiers (list)
  - Returns merged bounding box and temporal extent across all resources (same as directory extraction)
  - Individual resource details available in ``details`` field for diagnostics and error tracking
  - Supports all remote provider features: download limits, file filtering, parallel downloads
  - CLI already supports multiple remote identifiers (can be mixed with local files)
  - Example: ``geoextent -b -t 10.5281/zenodo.123 10.25532/OPARA-456 https://osf.io/abc123/``
  - **Architecture improvement**: Single resource processing is now a special case of multi-resource processing
  - Maintains full backward compatibility with existing code
  - Reduces code duplication and ensures consistent behavior

- **Output Enhancements**

  - Add extraction metadata to GeoJSON output with ``geoextent_extraction`` field containing:
    - ``version``: geoextent version used for the extraction
    - ``inputs``: list of input files, directories, or remote resources processed
    - ``statistics``: processing statistics including files processed, files with valid extent, and total size in human-readable format using flexible units (bytes, KiB, MiB, GiB, etc.)
    - ``format``: format of the processed data (moved from feature properties)
    - ``geoextent_handler``: handler used for processing (moved from feature properties)
    - ``crs``: coordinate reference system (moved from feature properties)
    - ``extent_type``: type of extent extracted - bounding_box, convex_hull, or point (moved from feature properties)
  - Add ``--no-metadata`` option to exclude extraction metadata from GeoJSON output
  - Reorganize GeoJSON structure: extraction properties moved from feature.properties to top-level geoextent_extraction
  - Feature properties now minimal, containing only placename and custom user properties
  - Metadata automatically included in all GeoJSON output (not added to WKT or WKB formats)

- **Visualization Features**

  - Add ``--browse`` option to automatically open geojson.io visualizations in default web browser
  - Use ``--browse`` alone to open visualization without printing URL, or combine with ``--geojsonio`` to print URL and open browser
  - Works with all spatial extent extractions (files, directories, remote repositories)
  - Compatible with other options like ``--convex-hull``, ``--quiet``, and different output formats

- **Performance and Infrastructure Improvements**

  - Refactor CI workflows to use custom GDAL installation script instead of pygdal
  - Remove deprecated pygdal dependency from GitHub Actions for improved build reliability
  - Add file filtering and parallel downloads to improve performance (:issue:`75`)
  - Implement ``--download-skip-nogeo`` option to skip downloading non-geospatial files
  - Add ``--max-download-size`` and ``--max-download-workers`` options for download control
  - Enhance ``--max-download-method`` with new ``smallest`` and ``largest`` file selection options
    - ``smallest``: prioritizes smallest files first to maximize file coverage within size limits
    - ``largest``: prioritizes largest files first for maximum data volume
    - ``ordered``: processes files in the order returned by the content provider (existing default)
    - ``random``: random file selection with reproducible seeding (existing option)
  - Optimize file download process using parallel downloads for multi-file datasets
  - Add comprehensive test refactoring to eliminate duplication and focus on single aspects

- **Placename Lookup Feature** (:issue:`74`)

  - Add ``--placename`` option for automatic geographic placename lookup using gazetteer services
  - Support for GeoNames, Nominatim, and Photon gazetteer services
  - Placenames added to GeoJSON feature properties for meaningful location context
  - Environment variable support for API keys via ``.env`` files
  - Intelligent sampling of geometry points for optimal placename identification
  - Add ``--placename-escape`` option for Unicode character escaping in placenames
  - Shared component algorithm for extracting common location components
  - Progress bar integration for gazetteer API calls
  - Optimize gazetteer queries to avoid duplicate API calls for closed polygon points (first and last point)

- **Repository Support Enhancements**

  - Add TU Dresden Opara content provider supporting DSpace 7.x repositories
    - Supports multiple URL variants: direct item URLs, DOI resolver URLs, handle URLs, and bare DOIs/UUIDs
    - Full API integration with DSpace 7.x REST API for metadata and file access
    - Handles ZIP files with nested directories and multiple shapefiles
    - Compatible with all size filtering and geospatial file filtering options
  - Add GFZ Data Services as content provider (:issue:`17`)
  - Add download size limiting for repositories (:issue:`70`)
  - Enhance content provider support for Dryad and OSF with full filtering capabilities
    - Dryad provider now supports ``/stash/dataset/`` URL format with ``doi:`` prefix (e.g., ``https://datadryad.org/stash/dataset/doi:10.5061/dryad.0k6djhb7x``)
  - Add support for OSF (Open Science Framework) repository extraction (:pr:`19`)
  - Enhance PANGAEA provider with non-tabular data support
    - Support for datasets without tabular data (e.g., GeoTIFF, GeoJSON, Shapefile files)
    - Automatic fallback to direct file download when tabular data unavailable
    - Downloads and extracts ZIP archives containing geospatial files
    - Full compatibility with size filtering and file filtering options
  - Add Dataverse repository support for data extraction (:issue:`57`)
  - Add ``--no-data-download`` option for metadata-only extraction from selected repositories
  - Restructure regex patterns for better repository candidate detection

- **Bug Fixes**

  - Fix GML bounding box coordinate order for GDAL >= 3.2 — the version check was inverted, causing incorrect coordinate swapping
  - Fix Figshare URL validation to reject incomplete URLs without a valid record ID instead of using unsafe fallback parsing

- **Format and Processing Improvements**

  - Add ``--no-subdirs`` option to control recursive processing of subdirectories (:issue:`55`)
  - Add WKT and WKB output format support for spatial extents (:issue:`46`)
  - Add FlatGeobuf format support (:issue:`43`)
  - Add support for processing multiple files with automatic extent merging
  - Run code formatter to improve code consistency (:issue:`54`)
  - Skip GDAL auxiliary files (``.ovr``, ``.aux.xml``, ``.msk``, etc.) during directory processing
  - Harden CSV handler: force CSV GDAL driver to prevent misidentification as gridded datasets, add extension-based pre-filtering for known vector/raster formats, and improve geometry column detection with prioritized pattern matching

- **User Experience Enhancements**

  - Add progress bars for file and directory processing with ``--no-progress`` option to disable (:issue:`32`)
  - Add ``--quiet`` option to suppress all console messages including warnings and progress bars
  - Add comprehensive test coverage for multiple providers
  - Add geopy, python-dotenv, and filesizelib dependencies for enhanced functionality

- **Features API**

  - Add ``--list-features`` CLI option to display machine-readable JSON with supported file formats and content providers
  - Add ``get_supported_features()`` Python API function for programmatic access to geoextent capabilities
  - Add ``validate_remote_identifier()`` and ``validate_file_format()`` validation functions
  - All 9 content providers include description (2-sentence overview) and website URL
  - Enables external tools to discover capabilities and validate inputs before processing
  - JSON output includes version, file format handlers with capabilities, and content provider details

0.8.0
^^^^^

- Move configuration from ``setup.py` to ``pyproject.toml``

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
