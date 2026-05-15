"""Render extracted mentions back into the source text for human display.

Two modes are supported today (issue #112):

- ``ansi``: matches are wrapped in ANSI SGR colour codes (terminal display,
  same look as ``ripgrep``/``grep --color``).
- ``brackets``: matches are wrapped in ``[[surface|kind]]`` textual markers
  (pipelines, file redirects, plain log capture).

``auto`` picks ``ansi`` when stdout is a TTY and ``brackets`` otherwise, the
same heuristic as ``grep --color=auto``.

The renderer reads geoextent's standoff ``char_start``/``char_end`` offsets
(documented in :mod:`geoextent.lib.handle_text`) from ``place_names`` and
``date_entities``. Overlapping spans are resolved greedy-longest-wins.

A follow-up issue tracks HTML rendering and Web Annotation Data Model
export (see :issue:`113`+).
"""

from __future__ import annotations

import logging
import sys
from typing import Dict, List, Optional

logger = logging.getLogger("geoextent")

# ANSI SGR code names used in the default class map. Bright variants use the
# 90+ range; bold ("1;") is applied to all so matches stand out on dark or
# light terminals.
_ANSI_COLOURS = {
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "bright_black": "90",
    "bright_red": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_blue": "94",
    "bright_magenta": "95",
    "bright_cyan": "96",
    "bright_white": "97",
}

DEFAULT_CLASSES = {
    "place": "cyan",
    "date": "yellow",
    "period": "magenta",
}

_ANSI_RESET = "\033[0m"


def parse_classes(spec: Optional[str]) -> Dict[str, str]:
    """Parse a ``--annotate-classes`` string into a ``{kind: colour}`` dict.

    Example input: ``"place=cyan,date=yellow,period=magenta"``. Unknown
    colours are passed through; the caller decides what to do with them
    (the ANSI renderer falls back to bold-only).
    """
    result = dict(DEFAULT_CLASSES)
    if not spec:
        return result
    for pair in spec.split(","):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        kind, colour = pair.split("=", 1)
        result[kind.strip().lower()] = colour.strip().lower()
    return result


def _ansi_open(colour: str) -> str:
    code = _ANSI_COLOURS.get(colour, "")
    return f"\033[1;{code}m" if code else "\033[1m"


def _gather_spans(
    place_names: List[Dict],
    date_entities: List[Dict],
) -> List[Dict]:
    """Flatten provenance records into a list of standoff spans.

    Each span has ``start``, ``end``, ``kind``, ``surface``, and ``matched``.
    Records lacking offsets (rare; should not happen for text/NER but is
    handled defensively) are skipped.
    """
    spans: List[Dict] = []
    for rec in place_names or []:
        start = rec.get("char_start")
        end = rec.get("char_end")
        if start is None or end is None:
            continue
        spans.append(
            {
                "start": int(start),
                "end": int(end),
                "kind": "place",
                "surface": rec.get("name", ""),
                "matched": rec.get("matched", False),
            }
        )
    for rec in date_entities or []:
        start = rec.get("char_start")
        end = rec.get("char_end")
        if start is None or end is None:
            continue
        kind = rec.get("kind", "date")
        spans.append(
            {
                "start": int(start),
                "end": int(end),
                "kind": kind,
                "surface": rec.get("text", ""),
                "matched": rec.get("matched", False),
            }
        )
    return spans


def _resolve_overlaps(spans: List[Dict]) -> List[Dict]:
    """Greedy longest-span-wins; ties resolve to the earlier start."""
    if not spans:
        return []
    ordered = sorted(spans, key=lambda s: (-(s["end"] - s["start"]), s["start"]))
    consumed = []  # list of (start, end) of kept spans
    keep: List[Dict] = []
    for span in ordered:
        s, e = span["start"], span["end"]
        if any(not (e <= cs or s >= ce) for cs, ce in consumed):
            continue
        consumed.append((s, e))
        keep.append(span)
    keep.sort(key=lambda s: s["start"])
    return keep


def render_annotated_text(
    result: Dict,
    *,
    mode: str = "brackets",
    classes: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """Return the source text with matched spans wrapped per ``mode``.

    ``result`` must include ``source_text`` and the standoff fields populated
    by the text/NER pipeline. Returns ``None`` if ``mode == "off"`` or the
    source/spans are not available.
    """
    if mode == "off":
        return None
    if not isinstance(result, dict):
        return None
    text = result.get("source_text")
    if not text:
        return None
    spans = _gather_spans(
        result.get("place_names") or [],
        result.get("date_entities") or [],
    )
    spans = _resolve_overlaps(spans)
    if not spans:
        return text  # echo the source unchanged

    classes = dict(classes or DEFAULT_CLASSES)

    out: List[str] = []
    cursor = 0
    for span in spans:
        s, e = span["start"], span["end"]
        if s < cursor or s >= len(text) or e > len(text):
            logger.debug(
                "Skipping span (%d,%d) outside source bounds (len=%d)",
                s,
                e,
                len(text),
            )
            continue
        out.append(text[cursor:s])
        surface = text[s:e]
        if mode == "ansi":
            colour = classes.get(span["kind"], "white")
            out.append(_ansi_open(colour))
            out.append(surface)
            out.append(_ANSI_RESET)
        elif mode == "brackets":
            out.append(f"[[{surface}|{span['kind']}]]")
        else:
            raise ValueError(
                f"Unknown annotate mode: {mode!r} (use 'ansi', 'brackets', or 'off')"
            )
        cursor = e
    out.append(text[cursor:])
    return "".join(out)


def resolve_mode(mode: str, stream=None) -> str:
    """Resolve ``--annotate auto`` to ``ansi`` (TTY) or ``brackets`` (pipe)."""
    if mode != "auto":
        return mode
    stream = stream if stream is not None else sys.stdout
    try:
        is_tty = bool(stream.isatty())
    except Exception:
        is_tty = False
    return "ansi" if is_tty else "brackets"
