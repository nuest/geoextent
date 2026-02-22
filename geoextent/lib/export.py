"""Export geoextent extraction results to file formats (GeoPackage, GeoJSON, CSV).

This module provides functions to write extraction results to disk in various
geospatial formats.  It is called from the CLI (``--output``) and exposed as
``geoextent.export_to_file()`` in the public API.

All coordinates are expected in **internal order** ``[longitude, latitude]``,
which is the correct axis order for GeoPackage (traditional GIS), GeoJSON
(RFC 7946), and CSV/WKT.
"""

import csv
import datetime
import json
import logging
import os
import warnings

from osgeo import ogr, osr

from . import helpfunctions as hf

logger = logging.getLogger("geoextent")

# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

_EXT_TO_DRIVER = {
    ".gpkg": "GPKG",
    ".geojson": "GeoJSON",
    ".json": "GeoJSON",
    ".csv": "CSV",
}


def _detect_output_format(path):
    """Map file extension to an OGR driver name.

    Falls back to ``"GPKG"`` with a warning for unrecognised extensions.
    """
    ext = os.path.splitext(path)[1].lower()
    driver = _EXT_TO_DRIVER.get(ext)
    if driver is None:
        warnings.warn(
            f"Unrecognised output extension '{ext}', falling back to GeoPackage",
            stacklevel=2,
        )
        driver = "GPKG"
    return driver


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _bbox_or_hull_to_geometry(result):
    """Convert a ``result["bbox"]`` value to an OGR Polygon geometry.

    Handles three shapes:

    1. **4-element list** ``[minlon, minlat, maxlon, maxlat]`` -> rectangle
    2. **Coordinate array** ``[[lon, lat], ...]`` when ``result.get("convex_hull")``
       is truthy -> polygon from points
    3. **GeoJSON Polygon dict** ``{"type": "Polygon", "coordinates": [...]}``
       -> polygon via OGR's GeoJSON parser

    Returns ``None`` when the bbox is missing or unusable.
    """
    bbox = result.get("bbox")
    if bbox is None:
        return None

    try:
        # Case 3: GeoJSON Polygon dict
        if isinstance(bbox, dict) and bbox.get("type") == "Polygon":
            geom = ogr.CreateGeometryFromJson(json.dumps(bbox))
            if geom is not None:
                geom.FlattenTo2D()
            return geom

        if not isinstance(bbox, list) or len(bbox) == 0:
            return None

        # Case 2: coordinate array (convex hull)
        if isinstance(bbox[0], list):
            ring = ogr.Geometry(ogr.wkbLinearRing)
            for coord in bbox:
                ring.AddPoint(float(coord[0]), float(coord[1]))
            ring.CloseRings()
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(ring)
            poly.FlattenTo2D()
            return poly

        # Case 1: simple bbox [minlon, minlat, maxlon, maxlat]
        if len(bbox) == 4:
            minlon, minlat, maxlon, maxlat = (float(v) for v in bbox)
            ring = ogr.Geometry(ogr.wkbLinearRing)
            ring.AddPoint(minlon, minlat)
            ring.AddPoint(maxlon, minlat)
            ring.AddPoint(maxlon, maxlat)
            ring.AddPoint(minlon, maxlat)
            ring.CloseRings()
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(ring)
            poly.FlattenTo2D()
            return poly

    except Exception:
        logger.debug("Failed to build geometry from bbox: %s", bbox, exc_info=True)

    return None


# ---------------------------------------------------------------------------
# Temporal helpers
# ---------------------------------------------------------------------------

_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
]


def _parse_tbox(tbox):
    """Parse a tbox list into ``(start_date, end_date)`` as ``datetime.date``.

    *tbox* is typically ``["2020-01-01", "2020-12-31"]``.
    Returns ``(None, None)`` when *tbox* is ``None`` or unparseable.
    """
    if not tbox or not isinstance(tbox, list) or len(tbox) < 2:
        return (None, None)

    def _to_date(val):
        if val is None:
            return None
        s = str(val)
        for fmt in _DATE_FORMATS:
            try:
                return datetime.datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return None

    return (_to_date(tbox[0]), _to_date(tbox[1]))


# ---------------------------------------------------------------------------
# Feature building
# ---------------------------------------------------------------------------


def _flatten_details(details):
    """Recursively flatten a ``details`` dict into a list of (filename, file_dict) tuples."""
    items = []
    for name, file_dict in details.items():
        if file_dict is None:
            items.append((name, None))
        else:
            items.append((name, file_dict))
            # Recurse into nested folders
            if file_dict.get("format") == "folder" and "details" in file_dict:
                items.extend(_flatten_details(file_dict["details"]))
    return items


def _build_features(output, inputs, version):
    """Convert an extraction result dict into a list of feature dicts.

    Each feature dict has keys: ``filename``, ``handler``, ``format``,
    ``tbox_start`` (date), ``tbox_end`` (date), ``crs``, ``geometry`` (OGR Geometry).

    For multi-file results (``details`` present) a summary feature is appended
    with ``handler="geoextent:<version>"``.
    """
    features = []

    if "details" not in output:
        # Single-file result
        tbox_start, tbox_end = _parse_tbox(output.get("tbox"))
        geom = _bbox_or_hull_to_geometry(output)
        features.append(
            {
                "filename": inputs[0] if inputs else "",
                "handler": output.get("geoextent_handler", ""),
                "format": output.get("format", ""),
                "tbox_start": tbox_start,
                "tbox_end": tbox_end,
                "crs": output.get("crs", ""),
                "geometry": geom,
            }
        )
    else:
        # Multi-file result: one feature per file
        for name, file_dict in _flatten_details(output["details"]):
            if file_dict is None:
                ext = os.path.splitext(name)[1][1:]
                features.append(
                    {
                        "filename": name,
                        "handler": None,
                        "format": ext if ext else "undetected",
                        "tbox_start": None,
                        "tbox_end": None,
                        "crs": None,
                        "geometry": None,
                    }
                )
            else:
                tbox_start, tbox_end = _parse_tbox(file_dict.get("tbox"))
                geom = _bbox_or_hull_to_geometry(file_dict)
                features.append(
                    {
                        "filename": name,
                        "handler": file_dict.get("geoextent_handler", ""),
                        "format": file_dict.get("format", ""),
                        "tbox_start": tbox_start,
                        "tbox_end": tbox_end,
                        "crs": file_dict.get("crs", ""),
                        "geometry": geom,
                    }
                )

        # Summary feature (merged extent)
        tbox_start, tbox_end = _parse_tbox(output.get("tbox"))
        geom = _bbox_or_hull_to_geometry(output)
        handler = f"geoextent:{version}" if version else "geoextent"
        features.append(
            {
                "filename": inputs[0] if inputs and len(inputs) == 1 else str(inputs),
                "handler": handler,
                "format": output.get("format", ""),
                "tbox_start": tbox_start,
                "tbox_end": tbox_end,
                "crs": output.get("crs", ""),
                "geometry": geom,
            }
        )

    return features


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def _write_gpkg(features, path):
    """Write features to a GeoPackage file."""
    sr4326 = osr.SpatialReference()
    sr4326.ImportFromEPSG(4326)

    if os.path.exists(path):
        os.remove(path)
        logger.warning("Overwriting %s", path)

    ds = ogr.GetDriverByName("GPKG").CreateDataSource(path)
    lyr = ds.CreateLayer("files", geom_type=ogr.wkbPolygon, srs=sr4326)
    lyr.CreateField(ogr.FieldDefn("filename", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("handler", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("format", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("tbox_start", ogr.OFTDate))
    lyr.CreateField(ogr.FieldDefn("tbox_end", ogr.OFTDate))
    lyr.CreateField(ogr.FieldDefn("crs", ogr.OFTString))

    for f in features:
        feat = ogr.Feature(lyr.GetLayerDefn())
        feat["filename"] = f["filename"] or ""
        feat["handler"] = f["handler"] or ""
        feat["format"] = f["format"] or ""
        feat["crs"] = f["crs"] or ""

        if f["tbox_start"] is not None:
            d = f["tbox_start"]
            feat.SetField("tbox_start", d.year, d.month, d.day, 0, 0, 0, 0)
        if f["tbox_end"] is not None:
            d = f["tbox_end"]
            feat.SetField("tbox_end", d.year, d.month, d.day, 0, 0, 0, 0)

        if f["geometry"] is not None:
            feat.SetGeometry(f["geometry"])

        lyr.CreateFeature(feat)

    ds = None  # flush & close


def _write_geojson(features, path):
    """Write features to a GeoJSON file (FeatureCollection)."""
    fc = {"type": "FeatureCollection", "features": []}

    for f in features:
        geom_json = None
        if f["geometry"] is not None:
            geom_json = json.loads(f["geometry"].ExportToJson())

        props = {
            "filename": f["filename"],
            "handler": f["handler"],
            "format": f["format"],
            "tbox_start": f["tbox_start"].isoformat() if f["tbox_start"] else None,
            "tbox_end": f["tbox_end"].isoformat() if f["tbox_end"] else None,
            "crs": f["crs"],
        }
        fc["features"].append(
            {
                "type": "Feature",
                "geometry": geom_json,
                "properties": props,
            }
        )

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(fc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def _write_csv(features, path, geometry_format="wkt"):
    """Write features to a CSV file.

    *geometry_format*: ``"wkt"`` (default) or ``"wkb"`` (hex-encoded little-endian).
    """
    columns = [
        "filename",
        "handler",
        "format",
        "tbox_start",
        "tbox_end",
        "crs",
        "geometry",
    ]

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(columns)

        for f in features:
            geom_str = ""
            if f["geometry"] is not None:
                if geometry_format == "wkb":
                    geom_str = f["geometry"].ExportToWkb(ogr.wkbNDR).hex()
                else:
                    geom_str = f["geometry"].ExportToWkt()

            writer.writerow(
                [
                    f["filename"] or "",
                    f["handler"] or "",
                    f["format"] or "",
                    f["tbox_start"].isoformat() if f["tbox_start"] else "",
                    f["tbox_end"].isoformat() if f["tbox_end"] else "",
                    f["crs"] or "",
                    geom_str,
                ]
            )


# ---------------------------------------------------------------------------
# Coordinate order helpers
# ---------------------------------------------------------------------------


def _swap_bbox_to_lonlat(bbox):
    """Swap a bbox from native EPSG:4326 [lat, lon] back to [lon, lat].

    Handles:
    - 4-element list ``[minlat, minlon, maxlat, maxlon]`` -> ``[minlon, minlat, maxlon, maxlat]``
    - Coordinate array ``[[lat, lon], ...]`` -> ``[[lon, lat], ...]``
    - GeoJSON Polygon dict with ``[lat, lon]`` -> ``[lon, lat]``
    """
    if bbox is None:
        return None
    if isinstance(bbox, dict) and bbox.get("type") == "Polygon":
        new_coords = []
        for ring in bbox.get("coordinates", []):
            new_coords.append([[coord[1], coord[0]] for coord in ring])
        return {"type": "Polygon", "coordinates": new_coords}
    if isinstance(bbox, list) and len(bbox) > 0:
        if isinstance(bbox[0], list):
            return [[coord[1], coord[0]] for coord in bbox]
        if len(bbox) == 4:
            return [bbox[1], bbox[0], bbox[3], bbox[2]]
    return bbox


def _swap_output_to_lonlat(output):
    """Deep-swap all bboxes in an output dict from [lat, lon] to [lon, lat].

    Returns a shallow copy with swapped bbox values (does not mutate input).
    """
    result = dict(output)
    if "bbox" in result:
        result["bbox"] = _swap_bbox_to_lonlat(result["bbox"])

    if "details" in result and isinstance(result["details"], dict):
        new_details = {}
        for key, val in result["details"].items():
            if isinstance(val, dict):
                new_details[key] = _swap_output_to_lonlat(val)
            else:
                new_details[key] = val
        result["details"] = new_details

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_results(
    output, path, inputs=None, version=None, geometry_format="wkt", native_order=False
):
    """Export extraction results to a file.

    Parameters
    ----------
    output : dict
        The extraction result dict (as returned by ``from_file``, ``from_directory``,
        or ``from_remote``).
    path : str
        Destination file path.  Format is auto-detected from the extension.
    inputs : list[str] | None
        Original input paths/identifiers (used for filenames in the output).
    version : str | None
        geoextent version string for the summary feature.
    geometry_format : str
        ``"wkt"`` or ``"wkb"`` — only affects CSV output.
    native_order : bool
        If True, coordinates in *output* are in native EPSG:4326 order
        ``[lat, lon]`` and will be swapped to ``[lon, lat]`` for file output.
        Default False (coordinates already in ``[lon, lat]``).
    """
    path = hf.path_output(path)

    if inputs is None:
        inputs = []

    # All output formats need [lon, lat]; swap if input is in [lat, lon]
    if native_order:
        output = _swap_output_to_lonlat(output)

    driver = _detect_output_format(path)
    features = _build_features(output, inputs, version)

    if driver == "GPKG":
        _write_gpkg(features, path)
    elif driver == "GeoJSON":
        _write_geojson(features, path)
    elif driver == "CSV":
        _write_csv(features, path, geometry_format=geometry_format)


# ---------------------------------------------------------------------------
# Readers (for join_files)
# ---------------------------------------------------------------------------


def _read_features_gpkg(path):
    """Read features from a GeoPackage file exported by geoextent.

    Returns a list of feature dicts matching the writer schema.
    """
    ds = ogr.Open(path)
    if ds is None:
        raise ValueError(f"Cannot open GeoPackage: {path}")

    lyr = ds.GetLayerByName("files")
    if lyr is None:
        raise ValueError(f"No 'files' layer in GeoPackage: {path}")

    defn = lyr.GetLayerDefn()
    ts_idx = defn.GetFieldIndex("tbox_start")
    te_idx = defn.GetFieldIndex("tbox_end")

    features = []
    for feat in lyr:
        geom = feat.GetGeometryRef()
        geom_clone = geom.Clone() if geom is not None else None

        tbox_start = None
        if not feat.IsFieldNull(ts_idx) and feat.IsFieldSet(ts_idx):
            dt = feat.GetFieldAsDateTime(ts_idx)
            tbox_start = datetime.date(dt[0], dt[1], dt[2])

        tbox_end = None
        if not feat.IsFieldNull(te_idx) and feat.IsFieldSet(te_idx):
            dt = feat.GetFieldAsDateTime(te_idx)
            tbox_end = datetime.date(dt[0], dt[1], dt[2])

        features.append(
            {
                "filename": feat["filename"] or "",
                "handler": feat["handler"] or "",
                "format": feat["format"] or "",
                "tbox_start": tbox_start,
                "tbox_end": tbox_end,
                "crs": feat["crs"] or "",
                "geometry": geom_clone,
            }
        )

    ds = None
    return features


def _read_features_geojson(path):
    """Read features from a GeoJSON file exported by geoextent.

    Returns a list of feature dicts matching the writer schema.
    """
    with open(path, encoding="utf-8") as fh:
        fc = json.load(fh)

    features = []
    for gj_feat in fc.get("features", []):
        props = gj_feat.get("properties", {})
        geom_json = gj_feat.get("geometry")
        geom = None
        if geom_json is not None:
            geom = ogr.CreateGeometryFromJson(json.dumps(geom_json))

        tbox_start = _to_date_or_none(props.get("tbox_start"))
        tbox_end = _to_date_or_none(props.get("tbox_end"))

        features.append(
            {
                "filename": props.get("filename", ""),
                "handler": props.get("handler", ""),
                "format": props.get("format", ""),
                "tbox_start": tbox_start,
                "tbox_end": tbox_end,
                "crs": props.get("crs", ""),
                "geometry": geom,
            }
        )

    return features


def _read_features_csv(path):
    """Read features from a CSV file exported by geoextent.

    Returns a list of feature dicts matching the writer schema.
    """
    features = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            geom = None
            geom_str = row.get("geometry", "").strip()
            if geom_str:
                if geom_str.upper().startswith(
                    "POLYGON"
                ) or geom_str.upper().startswith("POINT"):
                    geom = ogr.CreateGeometryFromWkt(geom_str)
                else:
                    # Try WKB hex
                    try:
                        geom = ogr.CreateGeometryFromWkb(bytes.fromhex(geom_str))
                    except (ValueError, RuntimeError):
                        logger.debug(
                            "Cannot parse geometry from CSV: %s", geom_str[:40]
                        )

            tbox_start = _to_date_or_none(row.get("tbox_start", "").strip() or None)
            tbox_end = _to_date_or_none(row.get("tbox_end", "").strip() or None)

            features.append(
                {
                    "filename": row.get("filename", ""),
                    "handler": row.get("handler", ""),
                    "format": row.get("format", ""),
                    "tbox_start": tbox_start,
                    "tbox_end": tbox_end,
                    "crs": row.get("crs", ""),
                    "geometry": geom,
                }
            )

    return features


def _to_date_or_none(val):
    """Parse a date string into ``datetime.date`` or return ``None``."""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _read_exported_features(path):
    """Read features from an exported file (GPKG, GeoJSON, or CSV).

    Dispatches to the correct reader based on file extension.
    """
    driver = _detect_output_format(path)
    if driver == "GPKG":
        return _read_features_gpkg(path)
    elif driver == "GeoJSON":
        return _read_features_geojson(path)
    elif driver == "CSV":
        return _read_features_csv(path)
    else:
        raise ValueError(f"Unsupported format for reading: {path}")


def _is_summary_feature(feature):
    """Return True if the feature is a summary row (handler starts with 'geoextent:')."""
    handler = feature.get("handler") or ""
    return handler.startswith("geoextent:") or handler == "geoextent"


def join_files(input_paths, output_path, geometry_format="wkt"):
    """Join multiple exported files into a single file.

    Reads features from each input file, filters out summary features
    (where handler starts with ``"geoextent:"``), and writes all remaining
    individual-file features to the output.

    Parameters
    ----------
    input_paths : list[str]
        Paths to exported files (GPKG, GeoJSON, or CSV).
    output_path : str
        Destination file path. Format is auto-detected from extension.
    geometry_format : str
        ``"wkt"`` or ``"wkb"`` — only affects CSV output.
    """
    output_path = hf.path_output(output_path)
    all_features = []

    for path in input_paths:
        try:
            features = _read_exported_features(path)
        except Exception as e:
            logger.warning("Cannot read %s: %s", path, e)
            continue

        for f in features:
            if not _is_summary_feature(f):
                all_features.append(f)

    driver = _detect_output_format(output_path)
    if driver == "GPKG":
        _write_gpkg(all_features, output_path)
    elif driver == "GeoJSON":
        _write_geojson(all_features, output_path)
    elif driver == "CSV":
        _write_csv(all_features, output_path, geometry_format=geometry_format)

    logger.debug(
        "Joined %d features from %d files into %s",
        len(all_features),
        len(input_paths),
        output_path,
    )


def export_to_file(output, path, inputs=None, geometry_format="wkt", native_order=True):
    """Export extraction results to a file (public API).

    This is a convenience wrapper around :func:`export_results` that
    auto-detects the geoextent version.

    Parameters
    ----------
    output : dict
        Extraction result dict from ``geoextent.from_file``, ``from_directory``,
        or ``from_remote``.  By default these return coordinates in native
        EPSG:4326 order ``[lat, lon]``; set *native_order* accordingly.
    path : str
        Destination file path.  Format is auto-detected from the extension:
        ``.gpkg`` (GeoPackage), ``.geojson``/``.json`` (GeoJSON), ``.csv`` (CSV).
    inputs : list[str] | None
        Original input paths/identifiers.
    geometry_format : str
        ``"wkt"`` (default) or ``"wkb"`` — only affects CSV output.
    native_order : bool
        If True (default), coordinates are in native EPSG:4326 ``[lat, lon]``
        order (as returned by the public API) and will be swapped to
        ``[lon, lat]`` for file output.  Set to False if coordinates are
        already in ``[lon, lat]`` order (e.g. from ``legacy=True``).
    """
    import geoextent

    export_results(
        output,
        path,
        inputs=inputs,
        version=geoextent.__version__,
        geometry_format=geometry_format,
        native_order=native_order,
    )
