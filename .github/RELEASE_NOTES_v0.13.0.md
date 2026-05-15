# geoextent v0.13.0

The biggest release since the project went public: 79 commits, 23+ new content providers, a new plain-text source backed by spaCy NER, journal article landing-page support, and EPSG:4326-native coordinate order on by default.

Cite: [`10.5281/zenodo.3925693`](https://doi.org/10.5281/zenodo.3925693) · PyPI: [`geoextent 0.13.0`](https://pypi.org/project/geoextent/0.13.0/) · Docs: <https://nuest.github.io/geoextent/>

## Highlights

### 🆕 Plain-text source via spaCy NER (#112)

A new `handle_text` handler runs spaCy NER over plain-text inputs, resolves place mentions through a gazetteer (Nominatim by default — no API key), and resolves named geological time periods through a bundled ICS GTS2020 chart (178 eons, eras, periods, epochs, ages). Calendar dates, decade and century envelopes, range expressions (`"between 2010 and 2015"`), and deep-time periods (Holocene, Mesozoic Era, Late Cretaceous) all flow into `bbox` / `tbox`. Pre-CE temporal extents use signed ISO 8601 year strings.

- New optional install extra: `pip install geoextent[nlp]`
- New `from_text()` API; new `--text STRING` / `-` (stdin) / file / directory inputs
- New `--annotate {auto,ansi,brackets,off}` for in-terminal match highlighting
- Standoff offsets contract: every mention carries `char_start`/`char_end` indices into an NFC-normalised `source_text` echo

See the [text extraction how-to](https://nuest.github.io/geoextent/howto/text-extraction.html) and the [highlighting how-to](https://nuest.github.io/geoextent/howto/highlighting.html).

### 🆕 Journal landing-page support: `journals/` umbrella (#76)

A new `journals/` content-provider package extracts spatial and temporal extent from journal article landing pages with the [`ojsGeo`](https://github.com/nuest/ojsGeo) (Open Journal Systems) or [`janeway_geometadata`](https://github.com/GeoinformationSystems/janeway_geometadata/) plugins. Source-preference priority is **richer-geometry-first**: JSON-LD `spatialCoverage` → `<link rel="alternate" type="application/geo+json">` → `DC.SpatialCoverage` (GeoJSON / WKT) → `DC.box` → ISO 19139 `EX_GeographicBoundingBox` → OJS `administrativeUnits` → ICBM / `geo.position` points.

The existing `Pensoft` provider was refactored into the same hierarchy (public API unchanged). Article DOIs are lifted from the HTML head — JSON-LD `identifier`, `citation_doi`, `prism.doi`, `DC.Identifier` — and fed into `--external-metadata` enrichment so a user can pass a journal article **URL** (not a DOI) and still get CrossRef / DataCite records.

See the [journals examples page](https://nuest.github.io/geoextent/examples_journals.html).

### 🆕 28 new content providers

Repositories: **InvenioRDM** (generalised from Zenodo, covers CaltechDATA, TU Wien, Frei-Data, GEO Knowledge Hub, TU Graz, Materials Cloud Archive, FDAT, DataPLANT ARChive, KTH, Prism, NYU Ultraviolet) · **B2SHARE** (EUDAT) · **Mendeley Data** · **4TU.ResearchData** · **RADAR** · **NSF Arctic Data Center** · **DEIMS-SDR** (follows external DOIs) · **HALO DB** · **GBIF** · **SEANOE** · **UKCEH** · **NFDI4Earth Knowledge Hub** · **DataONE** (covers KNB, PISCO, EDI/LTER, NEON, BCO-DMO, ESS-DIVE …) · **Wikidata** (via SPARQL) · **Dataverse instances**: ioerDATA, heiDATA, Edmond · **CSW-based**: BAW, MDI-DE, GDI-DE · **STAC** (any compliant Collection) · **Generic CKAN** (data.gov.uk, GovData.de, data.gov.au, …) · **GitHub**, **GitLab**, **Forgejo/Gitea**, **Software Heritage** · **GeoScienceWorld** · **`journals/` umbrella** (OJS, Janeway, Pensoft re-folded)

### 🆕 New file-format support

- **Cloud Optimized GeoTIFF (COG)** over HTTP(S) via GDAL `/vsicurl/` — header-only metadata extraction without downloading the file (#11)
- **Point clouds** (LAS/LAZ) via laspy — header-only bbox extraction and temporal extent from creation date
- **Esri File Geodatabase** (`.gdb`) via GDAL's OpenFileGDB driver
- **Zarr** (`.zarr`) V2 and V3 via GDAL's Zarr driver (#9)

### 🆕 Other features

- **`--metadata-first`** smart strategy: try metadata-only extraction, fall back to data download. Automatic metadata fallback after empty data downloads is on by default (opt out with `--no-metadata-fallback`).
- **`--time-format`** for configurable temporal output: date-only (default), ISO 8601, or any `strftime` (#39)
- **`-p` / `--parallel`** thread-based parallel file extraction within directories; `workers=N` API parameter (#34)
- **`progress_callback`** structured progress for `from_file()` / `from_directory()` / `from_remote()` — three built-in callbacks (tqdm, logging, list-collecting) (#80)
- **`--map`, `--preview`, `--map-dim`** for static map preview on OpenStreetMap tiles (terminal display via term-image; `pip install geoextent[preview]`) (#35)
- **`--join`** to merge multiple `--output` exports into one file (GPKG / GeoJSON / CSV)
- **AppImage** for portable Linux distribution — single-file executable bundling Python + GDAL + PROJ via conda-forge + appimagetool; built on every tag push (#40)
- **Interactive download-size confirmation** (`--max-download-size` with `download_size_soft_limit=True`)
- **Temporal extent from raster files**: NetCDF CF time dimensions, GeoTIFF `TIFFTAG_DATETIME`, ACDD `time_coverage_start/end`, band-level `ACQUISITIONDATETIME` (#22)
- **GeoCSV format**: `CoordX`/`CoordY` columns, `.prj` sidecars, WKT geometry columns, EarthScope `#`-prefixed metadata (#52)

## ⚠️ Breaking changes

- **Default coordinate order is now EPSG:4326 native `[lat, lon]`** for plain bounding boxes. Output bbox is `[minlat, minlon, maxlat, maxlon]` instead of `[minlon, minlat, maxlon, maxlat]`. GeoJSON output continues to use `[lon, lat]` per RFC 7946. Pass `--legacy` (or `legacy=True` in the API) to keep the previous `[lon, lat]` order for plain bboxes.
- **API renamed to snake_case (PEP 8)**: `from_file()`, `from_directory()`, `from_remote()`. The camelCase aliases (`fromFile`, `fromDirectory`, `fromRemote`) and `from_repository()` are removed. Internal handler modules and functions are also snake_case.
- **Drop support for bare numeric Zenodo record IDs** (e.g. `820562`); use the DOI (`10.5281/zenodo.820562`) or URL (`https://zenodo.org/records/820562`).
- **`--placename` default service** changed from `geonames` (which requires `GEONAMES_USERNAME`) to `nominatim` (no API key). Use `--placename-service geonames` to opt back.

## Selected bug fixes

- Reject raster / vector files whose coordinates are projected but falsely declared WGS84
- Validate bboxes against WGS84 ranges before merging
- `--convex-hull` strips multi-hundred-KB admin polygons from `place_names` provenance after consuming them
- `--placename` runs only on the final merged extent (no more per-file duplicate warnings)
- Fix `convex_hull_merge` for degenerate single-point and two-point line-segment hulls
- Text-file detection now combines extension, MIME, basename allowlist (`README`, `LICENSE`, `CHANGELOG`) and a content sniff — runs NER on extensionless project files while explicitly skipping source code (`.py`, `.js`, `.sh`, `.yaml`, …)
- `--geojsonio` now reports the precise endpoint and cause when the geojson.io Gist fallback fails (commonly anonymous-gist 401)

Full diff: https://github.com/nuest/geoextent/compare/v0.12.0...v0.13.0
Full changelog: https://nuest.github.io/geoextent/changelog.html#id1

## Install

```bash
pip install geoextent==0.13.0
# Optional extras
pip install 'geoextent[nlp]==0.13.0'         # spaCy NER for text inputs
pip install 'geoextent[preview]==0.13.0'     # static map / terminal preview
```

AppImage: see the [Linux AppImage how-to](https://nuest.github.io/geoextent/howto/appimage.html).

---
*Citing this release: Nüst, Daniel; Garzón, Sebastian; Drechsler, Lars and Qamaz, Yousef. (2026, May 15). geoextent (Version v0.13.0). Zenodo. <https://doi.org/10.5281/zenodo.3925693>*
