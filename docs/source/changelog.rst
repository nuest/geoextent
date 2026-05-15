
Changelog
=========

0.13.0
^^^^^^

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
  - Add GeoScienceWorld as metadata-only content provider for geoscience journal articles, extracting geographic coordinates from GeoRef metadata (WKT POLYGON/POINT) embedded in article landing pages; supports article URLs, GeoRef record URLs, and DOIs from multiple publisher prefixes (10.1190, 10.1144, etc.); uses ``curl_cffi`` with TLS fingerprint impersonation for Cloudflare-protected pages (:issue:`109`)
  - Add SEANOE (SEA scieNtific Open data Edition) as content provider for marine science data from Ifremer/SISMER, with metadata-only extraction from the REST API (geographic bounding boxes, temporal extents) and data download of open-access files; supports DOI prefix 10.17882 and seanoe.org landing page URLs (:issue:`104`)
  - Add UKCEH (UK Centre for Ecology & Hydrology) EIDC as content provider with metadata-only extraction from the catalogue JSON API (bounding boxes, temporal extents) and dual data download pattern (Apache datastore listing or data-package ZIP); supports DOI prefix 10.5285 and catalogue.ceh.ac.uk URLs (:issue:`103`)
  - Add GDI-DE (Geodateninfrastruktur Deutschland / geoportal.de) as metadata-only content provider for the national German spatial data infrastructure catalogue (771,000+ records), with CSW 2.0.2 metadata extraction via OWSLib; supports geoportal.de landing page URLs and bare UUIDs (:issue:`84`)
  - Add generic CKAN content provider supporting any CKAN instance via dataset URL matching, with known-host fast matching and dynamic API discovery; includes GeoJSON spatial metadata parsing with geometry preservation for convex hull, multi-format temporal field support, and UK ``bbox-*`` extras pattern; known hosts include GeoKur TU Dresden, data.gov.uk, GovData.de, data.gov.au, and catalog.data.gov (:issue:`98`)
  - Add STAC (SpatioTemporal Asset Catalog) as metadata-only content provider, extracting spatial bounding boxes and temporal intervals directly from STAC Collection JSON; supports known STAC API hosts (Element84, DLR, Terradue, WorldPop, Lantmateriet, etc.), ``/stac/`` URL path patterns, JSON content-inspection fallback, and content negotiation for HTML/JSON servers (:issue:`25`)
  - Add NFDI4Earth Knowledge Hub as metadata-only content provider for the Cordra-based digital object repository (1.3M+ datasets), with SPARQL endpoint extraction (spatial WKT, temporal ranges) and Cordra REST API fallback; supports OneStop4All landing page URLs and direct Cordra object URLs; follows ``landingPage`` to other supported providers (:issue:`100`)
  - Add GitHub as content provider for extracting geospatial extent from public GitHub repositories, with ``GitHostProvider`` abstract base class for git hosting platforms; uses Git Trees API (2 API calls per repo) and raw file downloads; supports repository root, branch, and subdirectory URLs; preserves directory structure for co-located files (e.g. shapefile components); optional ``GITHUB_TOKEN`` for higher rate limits (:issue:`96`)
  - Add GitLab as content provider for extracting geospatial extent from public GitLab repositories on gitlab.com and self-hosted instances; uses paginated Repository Tree API and raw file API; supports repository root, branch, and subdirectory URLs with nested namespace paths (``group/subgroup/project``); three-stage instance detection (known hosts, hostname heuristic, API probe); optional ``GITLAB_TOKEN`` for higher rate limits (:issue:`97`)
  - Add Forgejo/Gitea as content provider for extracting geospatial extent from public Forgejo and Gitea repositories (including Codeberg.org and Helmholtz DataHub); uses Gitea REST API v1 for paginated tree listing and raw file downloads; three-stage instance detection (known hosts, hostname heuristic containing "forgejo" or "gitea", ``/api/v1/version`` probe); optional ``FORGEJO_TOKEN`` for higher rate limits
  - Add Software Heritage as content provider for extracting geospatial extent from the universal software archive (Inria + UNESCO); supports persistent SWHIDs (``swh:1:dir:...``, ``swh:1:ori:...``, ``swh:1:rev:...``, ``swh:1:cnt:...``), browse URLs (``archive.softwareheritage.org``), and SWHID qualifiers (``origin=``, ``path=``); subpath optimization for targeted subdirectory extraction; optional ``SWH_TOKEN`` for higher rate limits (1200 req/hr vs 120 anonymous)
  - Add DataONE (Data Observation Network for Earth) as metadata-only content provider, extracting pre-computed spatial bounding boxes and temporal ranges from the Coordinating Node Solr API; covers ~20 member node repositories (KNB, PISCO, EDI/LTER, NEON, BCO-DMO, ESS-DIVE, etc.) through a single API; supports DOI prefixes ``10.5063/`` (KNB), ``10.6085/`` (PISCO), and ``search.dataone.org`` URLs; defers Arctic Data Center, PANGAEA, and Dryad datasets to their dedicated providers (:issue:`15`)

- **New Features — Text source (spaCy NER, issue** :issue:`112` **)**

  - **New text source.** spaCy-based named entity recognition extracts geospatial and temporal information from plain-text inputs. New optional ``[nlp]`` extra (``pip install geoextent[nlp]``) installs spaCy; the default ``en_core_web_sm`` model is auto-downloaded on first use (suppress with ``--no-auto-download``). New ``handle_text`` handler module routes text files (mime ``text/*``: ``.txt``, ``.md``, ``.markdown``, ``.rst``, ``.text``) automatically; new public ``from_text()`` API processes in-memory strings. CLI: ``--text-method`` (``"ner"`` is the default; ``"none"`` disables the text handler entirely) plus ``--text STRING``, ``-`` (stdin), single text files, directories of text files, and mixed inputs (text + geospatial in one call) — all inputs in a multi-input run are merged into a single envelope / convex hull by default, matching the existing files-only behaviour. When the ``[nlp]`` extra is not installed, the handler silently declines so that pre-existing workflows that happen to include ``README.md`` keep working.
  - **Place names from text.** Detected ``LOC``/``GPE`` entities are forward-geocoded via the configured gazetteer (Nominatim, GeoNames, or Photon) and contribute to the ``bbox``. Each detected name is recorded in a ``place_names`` provenance list carrying ``gazetteer_id`` and ``gazetteer_url`` (e.g. ``osm:relation:62422`` → ``https://www.openstreetmap.org/relation/62422``). **Areal hits use their administrative boundary** when the gazetteer provides one — Nominatim returns ``Polygon`` / ``MultiPolygon`` for states, counties, parks, etc., so ``"Field campaign in Saxony"`` now yields the state's polygon envelope instead of a centroid point. GeoNames and Photon are point-only; the same code path falls back to the centroid in those cases. CLI: ``--place-geometry {auto,boundary,point}`` (default ``auto``) overrides per call; ``--ner-model``, ``--ner-labels`` (default ``LOC,GPE``), ``--ner-score-threshold``, ``--ner-gazetteer`` (**default: Nominatim**, no API key required; falls back to ``--placename-service`` if that was set), ``--ner-ambiguity {drop,top}`` (``drop`` is default and defensive: ambiguous names like "Paris" or "Springfield" are skipped rather than guessed; use ``top`` to keep the highest-ranked candidate). When a name is dropped under the ``drop`` policy, geoextent logs a one-shot WARNING to stderr naming the place, the candidate hits, and the exact ``--ner-ambiguity top`` / ``ner_ambiguity='top'`` switch to flip the policy. An in-memory ``(service, query)`` cache amortises duplicate lookups within a run.
  - **Convex hull on mixed geometries.** ``--convex-hull`` now consumes polygon boundaries when the gazetteer supplies them: a single polygon hit yields the polygon's convex hull (acting as a polygon simplification for irregular outlines); a polygon hit plus an outside point extends the hull to enclose both; two or more point-only hits keep the line / polygon-of-points behaviour from before. ``--place-geometry point`` forces a centroid-only hull. See :doc:`howto/text-extraction` for examples.
  - **List the bundled period gazetteer.** New ``--list-periods`` CLI flag (with ``--list-periods-format {json,text}`` and ``--list-periods-filter SUBSTR``) and ``geoextent.lib.period_gazetteer.list_periods()`` API expose the full ICS GTS2020 chart that ships with geoextent. The output carries a versioned metadata block (``schema_version``, ``source``, ``source_url``, ``source_revision``, ``source_revision_date``, ``license``, ``license_url``, ``attribution``, ``built_at``, ``built_by``, ``period_count``) so downstream UIs can attribute the data and detect refreshes. Useful for autocomplete widgets and reference panels.
  - **Calendar dates from text.** ``DATE``/``TIME`` entities (parsed by :mod:`dateutil`) are joined with new structured parsing for ranges and granularities: year-only (``"1987"`` → ``1987-01-01..1987-12-31``), decades (``"the 1990s"`` → ``1990-01-01..1999-12-31``), centuries (``"the 19th century"`` → ``1801-01-01..1900-12-31``), and range expressions captured by spaCy as a single span (``"between 2010 and 2015"``, ``"from 1820 to 1850"``, ``"1820–1850"``, ``"January to March 2024"``). Splitter handles ASCII hyphens, en-dashes, em-dashes, and ``to``/``until``/``through``/``and`` connectors.
  - **Named time periods from text.** New spaCy ``PhraseMatcher`` built from a bundled ICS International Chronostratigraphic Chart (GTS2020, CC0; 178 geological eons, eras, periods, epochs, and ages) detects mentions like ``"Holocene"``, ``"Pleistocene"``, ``"Mesozoic Era"``, or ``"Late Cretaceous"`` independently of how spaCy NER classifies them (research shows ``en_core_web_sm`` labels ``Holocene`` as ``ORG``, ``Bronze Age`` as ``PERSON``, and misses ``Pleistocene`` entirely; the matcher is therefore authoritative). Each match resolves to a ``[start, end]`` pair via the bundled period gazetteer (new :mod:`geoextent.lib.period_gazetteer`, mirroring the place-gazetteer pattern). CLI: ``--period-gazetteer {bundled,none}``, ``--period-ambiguity {drop,top}``, ``--no-period-resolution``. PhraseMatcher always wins over overlapping NER place spans (``Cambrian`` is treated as a period, not a place). Bundled data is produced by ``tools/build_periods_data.py`` from the upstream Turtle and committed for reproducibility; a follow-up (:issue:`113`) will add an optional online Wikidata backend for archaeological / historical periods.
  - **Signed ISO 8601 extended year output for deep-time temporal extents.** Python's ``datetime`` cannot represent negative or year-0 dates, so geological mentions are emitted as signed ISO year strings (``-9750-01-01`` for the start of the Holocene, ``-251900050-01-01`` for the base of the Mesozoic). New helpers ``signed_iso_format``, ``parse_signed_iso``, ``signed_iso_min``, ``signed_iso_max`` provide numeric ordering (lexicographic compare is wrong on signed strings). ``tbox_merge`` automatically falls back to numeric signed-year comparison when any mention is pre-CE; CE-only output continues to honour ``--time-format`` exactly as before. The ``tbox`` for inputs containing only CE dates is unchanged byte-for-byte.
  - **Standoff offsets contract for downstream highlighting.** Every place / date / period mention carries ``char_start`` and ``char_end`` indices into the source string. Result dicts now echo the source via three new fields: ``source_text`` (NFC-normalised; BOM stripped), ``source_offset_unit`` (always ``"python_codepoint"``), and ``source_normalisation`` (always ``"nfc"``). The pipeline normalises input to NFC before tokenising so offsets are stable regardless of whether the caller passed NFD-composed characters (München vs München). ``--no-source-text`` / ``include_source_text=False`` opt out of the echo for privacy or output-size concerns; offsets are still emitted.
  - **In-terminal and pipe-friendly match highlighting.** New ``--annotate {auto,ansi,brackets,off}`` CLI flag (and ``geoextent.lib.annotate.render_annotated_text()`` library helper) prints the source text with matched place names, dates, and named time periods highlighted after the JSON output. ``ansi`` uses terminal SGR colours (default: places cyan, dates yellow, periods magenta); ``brackets`` uses textual markers (``[[Berlin|place]]``, ``[[Holocene|period]]``, ``[[2024-05-12|date]]``) for log capture, pipelines, and chat clients. ``auto`` (default) picks ``ansi`` when stdout is a TTY else ``brackets``, mirroring ``grep --color=auto``. Override colours with ``--annotate-classes "place=red,date=green,period=blue"``. Overlapping spans resolve greedy-longest-wins. ``--quiet`` only suppresses the ``auto`` default; explicit ``--annotate`` modes still emit. HTML rendering and Web Annotation Data Model JSON-LD export are tracked in a follow-up (:issue:`114`).
  - **Documentation.** New how-to guide at :doc:`howto/highlighting` walks through the standoff offset contract, source-text echo, ``--annotate`` modes, a Python consumer snippet, and a JavaScript/Java re-encoding recipe for callers that count UTF-16 code units. Examples in the README cover place-name extraction, range/decade/century parsing, geological periods, signed-ISO output, and ``--annotate brackets`` invocation. CLAUDE.md gains a "Standoff Annotation Contract" section and a "Temporal Output Format" section describing the signed-ISO convention. ``--formats`` / ``--list-features`` now lists "Text (NER)" with its capability metadata.

- **New Features**

  - Add Cloud Optimized GeoTIFF (COG) support: direct HTTP(S) URLs to GeoTIFF files are opened via GDAL ``/vsicurl/`` for efficient header-only metadata extraction without downloading the full file (:issue:`11`)
  - Add point cloud support for LAS/LAZ files via laspy, extracting bounding boxes from file headers and temporal extent from creation dates (:issue:`10`)
  - Add ``--join`` CLI flag and ``join_files()`` Python API to merge multiple export files (from ``--output``) into a single file, dropping summary rows and keeping only individual-file features; supports cross-format joins (GPKG, GeoJSON, CSV)
  - Enhanced ``--output`` export: support single-file input, auto-detect GeoJSON/CSV format from extension, ``export_to_file()`` Python API, proper date fields (``tbox_start``/``tbox_end``), convex hull geometry export, ``--format`` interaction for CSV (:issue:`21`)
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
  - Add support for Zarr format (``.zarr``) via GDAL's Zarr driver (V2 and V3), including directory-based dataset handling in CLI and directory extraction (:issue:`9`)
  - All content providers now support interactive download size confirmation via ``--max-download-size``. When the total download exceeds the limit, the CLI prompts for confirmation instead of silently truncating. API: ``download_size_soft_limit=True`` in ``from_remote()``.
  - Add ``-p`` / ``--parallel`` CLI flag and ``workers`` API parameter for parallel file extraction within directories using thread-based parallelism. ``-p`` auto-detects CPU count, ``-p N`` uses N workers. API: ``from_directory(..., workers=N)`` and ``from_remote(..., workers=N)``. (:issue:`34`)
  - Add ``progress_callback`` parameter to ``from_file()``, ``from_directory()``, and ``from_remote()`` for structured progress reporting. Callbacks receive ``ProgressEvent`` dataclass instances with phase, message, current/total counters, and byte-level download progress. Three built-in callbacks: ``TqdmProgressCallback`` (tqdm bars), ``LoggingProgressCallback`` (logger), ``CollectingProgressCallback`` (list collection for testing). See :doc:`howto/api` for usage. (:issue:`80`)
  - Add ``--map``, ``--preview``, and ``--map-dim`` CLI flags for static map preview of extracted spatial extents on OpenStreetMap tiles (requires ``pip install geoextent[preview]``). ``--map`` saves a PNG to a temporary file, ``--map FILE`` saves to a specific path, ``--preview`` displays in the terminal using ``term-image`` (auto-detects Kitty/iTerm2/Sixel, falls back to Unicode blocks) or external tools, ``--map-dim WxH`` sets image dimensions. The saved path is printed to stderr unless ``--quiet`` is used. (:issue:`35`)
  - Add AppImage packaging for portable Linux distribution: single-file executable bundling Python, GDAL, PROJ, and all dependencies via conda-forge + appimagetool with zstd compression; CI workflow builds on tag push and attaches to GitHub Releases (:issue:`40`)

- **Breaking Changes**

  - Drop support for bare numeric Zenodo record IDs (e.g., ``820562``); use DOI (``10.5281/zenodo.820562``) or URL (``https://zenodo.org/records/820562``) instead

- **Bug Fixes**

  - Skip raster files with pixel-based coordinates (outside WGS84 bounds) instead of merging them into geographic extents
  - Validate bounding boxes against WGS84 coordinate ranges before including in results
  - Reject vector files with projected coordinates falsely reported as WGS84 (e.g., GeoJSON files without CRS declaration)
  - ``--geojsonio`` (CLI) now distinguishes "no spatial extent in output" from "geojson.io service call failed" and surfaces the underlying reason (commonly ``401 Requires authentication`` because anonymous GitHub Gist uploads — used by ``geojsonio`` for GeoJSON above 150 KB — now require auth). geojson.io itself does not document a maximum payload size (`API.md <https://github.com/mapbox/geojson.io/blob/main/API.md>`__); 150 KB is purely the `geojsonio library's MAX_URL_LEN threshold <https://github.com/jwass/geojsonio.py/blob/master/geojsonio/geojsonio.py>`__ above which it switches to a Gist fallback. ``helpfunctions.generate_geojsonio_url(raise_on_error=True)`` raises a new ``GeojsonioUrlError`` so library callers can react. The warning now names the precise endpoint (``geojsonio.make_url → GitHub Gist API``), reports the payload size in bytes, cites the 150 KB threshold, and — when the payload is over the threshold — hints at ``--convex-hull`` as the user-actionable fix.
  - ``--placename`` default service changed from ``geonames`` (which requires the ``GEONAMES_USERNAME`` env var) to ``nominatim`` (no API key needed). Use ``--placename-service geonames`` to opt back into GeoNames.
  - ``--convex-hull`` now strips ``boundary`` polygons from the ``place_names`` provenance after consuming them for the hull. The hull already encodes the spatial extent; carrying multi-hundred-KB admin polygons next to it pushed every NER-driven GeoJSON past the geojson.io URL-fragment limit, forcing the failing anonymous-gist fallback. Output shrinks from ~325 KB to ~2.5 KB for a typical ``Berlin + Reykjavik`` convex hull.
  - All placename / gazetteer warnings now name the service and endpoint (e.g. ``Nominatim reverse-geocoding via nominatim.openstreetmap.org failed for (52.3, 13.4): timeout``) so error scope is unambiguous when multiple services may have been queried.
  - ``--placename`` runs only once on the final merged extent now. Previously each per-file ``from_file`` call inside ``from_directory`` also attempted reverse-geocoding, producing duplicate / spurious "No geometry provided for placename extraction" warnings for inputs that produced no individual bbox.
  - ``--place-geometry point`` suppresses the boundary polygon in the ``place_names`` provenance (only the centroid lat/lon is kept). The user has asked for point treatment, so emitting a redundant full polygon next to the point is misleading and bloats the response.
  - Ambiguous-place-name warning now uses ``;`` between candidates (e.g. ``Paris, Île-de-France, France; Paris, Lamar County, Texas``) so the boundary between candidates stays readable when individual names contain commas.
  - Fix a latent ``NameError`` in ``handle_text.get_convex_hull`` (referenced ``place_geometry`` without declaring it in the signature) that surfaced when text files were processed inside ``from_directory`` with ``--convex-hull``.
  - ``--text`` (and ``-`` stdin) inputs are now merged with positional file inputs by default, matching the behaviour of multi-file runs. Previously, a command like ``geoextent -b --convex-hull --text "Travelling from Denmark to Belgium in 2021 and 2023" tests/text/cities.txt`` silently dropped the bbox and emitted only the merged tbox.
  - Fix ``convex_hull_merge`` to handle degenerate-hull inputs (single-point and two-point line-segment hulls) instead of silently dropping them. Previously a 2-vertex hull from ``--text "A to B"`` produced no geometry and the merge returned ``None``; degenerate hulls are now promoted to thin rectangles so they survive the union with peer geometries.
  - Text-file detection is no longer purely extension-based. ``text_extraction.mime.is_text_file`` now combines (1) explicit ``TEXT_EXTENSIONS`` / ``_EXCLUDE_EXTENSIONS`` fast-paths, (2) a ``_TEXT_BASENAMES`` list for common extensionless project files (``README``, ``LICENSE``, ``CHANGELOG``, etc.), (3) ``mimetypes.guess_type`` as a confirming hint, and (4) a small content sniff over the first 8 KB (NULL-byte heuristic, UTF-8 / UTF-16 BOM decode attempt, printable-byte ratio for legacy 8-bit encodings). Net result: ``README``, ``LICENSE``, ``.log``, ``.adoc``, ``.org`` files and extensionless text files are now correctly NER candidates; source code that ``mimetypes`` happens to label ``text/x-python`` etc. (``.py``, ``.js``, ``.sh``, ``.yaml``, …) is explicitly excluded so directory walks don't accidentally run NER on code.

- **API Changes**

  - Rename all public API functions from camelCase to snake_case per PEP 8: ``from_file()``, ``from_directory()``, ``from_remote()`` (:issue:`31`)
  - Remove old camelCase aliases (``fromFile``, ``fromDirectory``, ``fromRemote``)
  - Rename internal handler modules: ``handleCSV`` → ``handle_csv``, ``handleRaster`` → ``handle_raster``, ``handleVector`` → ``handle_vector``
  - Rename all internal handler functions to snake_case (e.g., ``checkFileSupported`` → ``check_file_supported``, ``getBoundingBox`` → ``get_bounding_box``)

- **Improvements**

  - Document installation with uv, conda/mamba, Poetry, and pipx (:issue:`4`, :issue:`5`, :issue:`41`)
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
