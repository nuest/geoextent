"""Build geoextent/lib/data/periods.json from the ICS GTS2020 Turtle.

This script is invoked once per data refresh. It fetches the ICS
International Chronostratigraphic Chart (CGI-IUGS/timescale-data, CC0)
in Turtle, parses geological-time concepts with rdflib, converts Ma BP
ages to signed ISO year strings, and writes a compact JSON used at
runtime by ``geoextent.lib.period_gazetteer``.

Usage::

    python tools/build_periods_data.py

The script requires ``rdflib`` and ``requests`` and writes to
``geoextent/lib/data/periods.json``.

Source: https://github.com/CGI-IUGS/timescale-data (License: CC0)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import requests
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, SKOS

ICS_TTL_URL = (
    "https://raw.githubusercontent.com/CGI-IUGS/timescale-data/master/rdf/isc2020.ttl"
)
ICS_API_URL = (
    "https://api.github.com/repos/CGI-IUGS/timescale-data/commits"
    "?path=rdf/isc2020.ttl&per_page=1"
)

# Schema version of the periods.json file format. Bump on breaking changes
# so downstream consumers can detect format shifts.
SCHEMA_VERSION = "1.0"

GTS = Namespace("http://resource.geosciml.org/ontology/timescale/gts#")
ISC = Namespace("http://resource.geosciml.org/classifier/ics/ischart/")
RANK = Namespace("http://resource.geosciml.org/ontology/timescale/rank/")

# Ma BP origin per the GTS2020 TRS definition.
MA_BP_ORIGIN_YEAR = 1950

# rdfs:comment patterns:
#   "older bound -174.1 +|-1.0 Ma"
#   "older bound -0.0117 Ma"
#   "older bound -541.0 +|-1.0 Ma"
_BOUND_RE = re.compile(
    r"^\s*(older|younger)\s+bound\s+(-?\d+(?:\.\d+)?)"
    r"(?:\s*\+\|-\s*\d+(?:\.\d+)?)?\s*Ma\s*$",
    re.IGNORECASE,
)


def _ma_to_year(ma_value: float) -> int:
    """Convert Ma BP (years × 10⁶ before 1950) to a signed CE year (int).

    Example: ``ma_value = -0.0117`` → year ``1950 - 11700 = -9750``.
    """
    years_before_1950 = -ma_value * 1_000_000
    return int(round(MA_BP_ORIGIN_YEAR - years_before_1950))


def _signed_iso(year: int, month: int = 1, day: int = 1) -> str:
    """Format a signed CE year as an ISO 8601 extended date string.

    Negative and zero years use a leading ``-``. Years with fewer than four
    digits are zero-padded to four digits to keep CE/BCE dates visually
    aligned. Large positive years are rendered as-is.
    """
    if year < 0:
        return f"-{abs(year):04d}-{month:02d}-{day:02d}"
    return f"{year:04d}-{month:02d}-{day:02d}"


def _parse_bounds(comments):
    """Pull `(older_year, younger_year)` from a concept's rdfs:comment list.

    Returns ``(None, None)`` if the bounds cannot be parsed.
    """
    older = younger = None
    for c in comments:
        m = _BOUND_RE.match(str(c))
        if not m:
            continue
        which, ma_text = m.group(1).lower(), m.group(2)
        try:
            ma = float(ma_text)
        except ValueError:
            continue
        year = _ma_to_year(ma)
        if which == "older":
            older = year
        else:
            younger = year
    return older, younger


def _english_labels(graph: Graph, subj: URIRef):
    """Return a ``(preferred, aliases)`` tuple of English-language labels."""
    pref = None
    aliases = set()
    for obj in graph.objects(subj, SKOS.prefLabel):
        if obj.language == "en":
            pref = str(obj)
            break
    for obj in graph.objects(subj, RDFS.label):
        if obj.language == "en":
            label = str(obj)
            if pref is None:
                pref = label
            else:
                aliases.add(label)
    if pref is None:
        # Fall back to the URI's local name (e.g. "Holocene").
        pref = subj.split("/")[-1]
    # ICS labels often end with their rank ("Aalenian Age"); add the bare
    # base name as an alias so phrase-matching catches plain "Aalenian".
    rank_suffixes = (" Age", " Epoch", " Period", " Era", " Eon")
    for suf in rank_suffixes:
        if pref.endswith(suf):
            aliases.add(pref[: -len(suf)])
            break
    aliases.discard(pref)
    return pref, sorted(aliases)


def _fetch_source_revision():
    """Return ``(commit_sha, commit_date)`` for the upstream Turtle file.

    Best-effort: returns ``(None, None)`` if the GitHub API is unreachable
    or rate-limited.
    """
    try:
        resp = requests.get(ICS_API_URL, timeout=30)
        resp.raise_for_status()
        commits = resp.json()
        if not commits:
            return None, None
        head = commits[0]
        return head.get("sha"), head.get("commit", {}).get("committer", {}).get("date")
    except Exception as e:
        print(
            f"Warning: could not fetch upstream commit metadata: {e}", file=sys.stderr
        )
        return None, None


def build(source_url: str = ICS_TTL_URL) -> dict:
    import datetime

    built_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    source_revision, source_revision_date = _fetch_source_revision()

    print(f"Fetching {source_url}", file=sys.stderr)
    resp = requests.get(source_url, timeout=60)
    resp.raise_for_status()
    ttl = resp.text
    source_last_modified = resp.headers.get("Last-Modified")

    print(f"Parsing {len(ttl):,} bytes of Turtle", file=sys.stderr)
    g = Graph()
    g.parse(data=ttl, format="turtle")

    # Concepts of interest: anything with a gts rank classification.
    targets = set()
    for subj in g.subjects(GTS.rank, None):
        if isinstance(subj, URIRef) and str(subj).startswith(str(ISC)):
            targets.add(subj)

    periods = []
    skipped = 0
    for subj in sorted(targets):
        comments = list(g.objects(subj, RDFS.comment))
        older, younger = _parse_bounds(comments)
        if older is None or younger is None:
            skipped += 1
            continue
        pref, aliases = _english_labels(g, subj)
        rank_obj = next(g.objects(subj, GTS.rank), None)
        rank = str(rank_obj).rsplit("/", 1)[-1] if rank_obj else None
        periods.append(
            {
                "name": pref,
                "aliases": aliases,
                "start": _signed_iso(older),
                "end": _signed_iso(younger),
                "id": f"ics:{subj.split('/')[-1]}",
                "url": str(subj),
                "source": "ICS GTS2020",
                "rank": rank,
            }
        )

    periods.sort(key=lambda p: p["name"].lower())
    return {
        # ---- metadata block ------------------------------------------------
        # Provenance and licensing for the bundled time-period gazetteer.
        # Schema is versioned; downstream consumers should inspect
        # ``schema_version`` before relying on the layout.
        "name": "geoextent bundled period gazetteer",
        "schema_version": SCHEMA_VERSION,
        "source": "ICS International Chronostratigraphic Chart (GTS2020)",
        "source_url": "https://github.com/CGI-IUGS/timescale-data",
        "source_file": source_url,
        "source_revision": source_revision,
        "source_revision_date": source_revision_date,
        "source_last_modified": source_last_modified,
        "license": "CC0-1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "attribution": (
            "International Chronostratigraphic Chart (ICS / IUGS), "
            "GTS2020 vocabulary, dedicated to the public domain (CC0-1.0). "
            "Distributed by CGI-IUGS at "
            "https://github.com/CGI-IUGS/timescale-data ."
        ),
        "built_at": built_at,
        "built_by": "geoextent tools/build_periods_data.py",
        "ma_bp_origin_year": MA_BP_ORIGIN_YEAR,
        "period_count": len(periods),
        "skipped_no_bounds": skipped,
        # --------------------------------------------------------------------
        "periods": periods,
    }


def main() -> int:
    data = build()
    out_path = (
        Path(__file__).resolve().parents[1]
        / "geoextent"
        / "lib"
        / "data"
        / "periods.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(
        f"Wrote {out_path} with {len(data['periods'])} periods "
        f"(skipped {data['skipped_no_bounds']} concepts without bounds)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
