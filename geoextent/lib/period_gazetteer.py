"""Named time-period gazetteer (issue #112).

Resolves named geological/historical time period mentions (e.g. ``"Holocene"``,
``"Mesozoic Era"``) to a ``[start, end]`` pair of signed ISO 8601 date
strings, mirroring how :mod:`geoextent.lib.gazetteer` resolves place names to
coordinates.

This release ships a single backend, :class:`BundledPeriodGazetteer`, which
loads the offline data file ``geoextent/lib/data/periods.json`` built from
the ICS International Chronostratigraphic Chart (GTS2020, CC0). Online
backends (Wikidata, PeriodO) are tracked in a follow-up issue.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("geoextent")


class PeriodGazetteer:
    """Abstract interface for period-name gazetteers."""

    name = "abstract"

    def lookup(self, query: str, limit: int = 5) -> List[Dict]:
        """Return up to ``limit`` candidate hits for ``query``.

        Each hit is a dict with keys ``name``, ``start`` (signed ISO date),
        ``end`` (signed ISO date), ``id``, ``url``, and ``source``.
        """
        raise NotImplementedError

    def label_index(self) -> Dict[str, Dict]:
        """Return a ``{lowercase-label: representative-hit}`` index used to
        build a :class:`spacy.matcher.PhraseMatcher` over period names."""
        raise NotImplementedError


class BundledPeriodGazetteer(PeriodGazetteer):
    """Offline gazetteer backed by the bundled ICS GTS2020 JSON."""

    name = "ics"

    def __init__(self, data_path: Optional[str] = None):
        if data_path is None:
            data_path = os.path.join(os.path.dirname(__file__), "data", "periods.json")
        if not os.path.exists(data_path):
            raise FileNotFoundError(
                f"Bundled periods.json not found at {data_path}; "
                "run tools/build_periods_data.py to regenerate."
            )
        with open(data_path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

        # Build an index: lowercase label → list of records (one record per
        # period; duplicates are possible when a name + alias collide).
        self._index: Dict[str, List[Dict]] = {}
        for rec in self._data.get("periods", []):
            labels = [rec["name"]] + list(rec.get("aliases", []))
            for label in labels:
                key = label.strip().lower()
                if not key:
                    continue
                self._index.setdefault(key, []).append(rec)

    def lookup(self, query: str, limit: int = 5) -> List[Dict]:
        key = (query or "").strip().lower()
        if not key:
            return []
        return self._index.get(key, [])[:limit]

    def label_index(self) -> Dict[str, Dict]:
        # Use the first record per key as the representative for matcher
        # construction; lookup() above still returns the full candidate list.
        return {k: v[0] for k, v in self._index.items()}


def list_periods(
    *,
    name_filter: Optional[str] = None,
    include_metadata: bool = True,
) -> Dict:
    """Return the bundled named-time-period gazetteer as a structured dict.

    Downstream tools (UIs, autocomplete widgets, reference docs) can call
    this to enumerate every period geoextent recognises, together with the
    provenance / licensing metadata that ships with the data.

    Args:
        name_filter: optional case-insensitive substring; only periods whose
            ``name`` or any ``alias`` matches are returned. ``None`` (the
            default) returns the full list.
        include_metadata: when False, only the ``periods`` list is returned
            (without the provenance / licensing fields). Defaults to True
            so consumers get attribution out of the box.

    Returns:
        A dict shaped like the on-disk ``periods.json``. With the default
        flags::

            {
              "name": "geoextent bundled period gazetteer",
              "schema_version": "1.0",
              "source": "ICS International Chronostratigraphic Chart (GTS2020)",
              "source_url": "...",
              "source_revision": "...",
              "license": "CC0-1.0",
              "attribution": "...",
              "built_at": "2026-05-11T21:43:20Z",
              "period_count": 178,
              "periods": [{"name": "Holocene", "start": "-9750-01-01",
                           "end": "1950-01-01", "id": "ics:Holocene",
                           "url": "...", "rank": "Epoch",
                           "aliases": ["Holocene Epoch"]}, ...]
            }
    """
    # Load via the bundled gazetteer so we go through one filesystem path.
    gazetteer = BundledPeriodGazetteer()
    data = dict(gazetteer._data)  # shallow copy; periods list is reused

    periods = data.get("periods", [])
    if name_filter:
        needle = name_filter.strip().lower()

        def _matches(rec):
            if needle in rec.get("name", "").lower():
                return True
            return any(needle in (a or "").lower() for a in rec.get("aliases", []))

        periods = [rec for rec in periods if _matches(rec)]

    if not include_metadata:
        return {"periods": periods, "period_count": len(periods)}

    data["periods"] = periods
    data["period_count"] = len(periods)
    return data


def get_period_gazetteer(name: str) -> Optional[PeriodGazetteer]:
    """Instantiate a period gazetteer by name. Returns ``None`` for ``"none"``.

    Recognised names: ``"bundled"`` (default), ``"ics"`` (alias), ``"none"``.
    Future backends (``"wikidata"``, ``"chain"``) will be added in
    follow-up work.
    """
    if name in (None, "none"):
        return None
    if name in ("bundled", "ics"):
        return BundledPeriodGazetteer()
    raise ValueError(
        f"Unsupported period gazetteer: {name!r}. "
        "Supported: 'bundled' (default), 'none'."
    )


def forward_geocode_periods(
    names: List[str],
    gazetteer: Optional[PeriodGazetteer],
    ambiguity: str = "drop",
    cache: Optional[Dict[Tuple[str, str], List[Dict]]] = None,
    limit: int = 5,
) -> List[Tuple[str, Optional[Dict], List[Dict]]]:
    """Forward-resolve a list of period names.

    Mirrors :func:`geoextent.lib.gazetteer.forward_geocode_names`. Returns
    ``(name, chosen_hit, all_hits)`` tuples in input order. ``chosen_hit``
    is ``None`` when no hit is found, when an ambiguous result was dropped,
    or when ``gazetteer`` is ``None``.
    """
    if ambiguity not in ("drop", "top"):
        raise ValueError(f"Invalid ambiguity mode: {ambiguity!r} (use 'drop' or 'top')")
    if cache is None:
        cache = {}

    out: List[Tuple[str, Optional[Dict], List[Dict]]] = []
    for raw in names:
        name = (raw or "").strip()
        if not name:
            continue
        if gazetteer is None:
            out.append((name, None, []))
            continue
        key = (gazetteer.name, name.lower())
        if key in cache:
            hits = cache[key]
        else:
            hits = gazetteer.lookup(name, limit=limit)
            cache[key] = hits
        if not hits:
            out.append((name, None, hits))
            continue
        if ambiguity == "drop" and len(hits) > 1:
            logger.debug(
                "Dropping ambiguous period mention %r (%d hits)", name, len(hits)
            )
            out.append((name, None, hits))
            continue
        out.append((name, hits[0], hits))
    return out
