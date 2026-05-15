"""Parse DATE/TIME mentions into ``(start_iso, end_iso)`` envelopes.

spaCy's DATE entity captures a wide variety of expressions; this module
converts them into signed ISO 8601 date strings suitable for geoextent's
``tbox``. Recognised shapes include:

- Year-only: ``"1987"`` → ``("1987-01-01", "1987-12-31")``
- Decade: ``"the 1990s"`` → ``("1990-01-01", "1999-12-31")``
- Century: ``"the 19th century"`` → ``("1801-01-01", "1900-12-31")``
- Ranges in a single span: ``"between 2010 and 2015"``, ``"1820-1850"``,
  ``"January to March 2024"``
- ISO and natural-language calendar dates (delegated to :mod:`dateutil`).

For deep-time / pre-CE inputs the module emits signed ISO strings via
:func:`geoextent.lib.helpfunctions.signed_iso_format` so the same downstream
machinery (``tbox_merge``) works for ICS-resolved geological periods.
"""

from __future__ import annotations

import logging
import re
from typing import Optional, Tuple

from dateutil import parser as date_parser

from .. import helpfunctions as hf

logger = logging.getLogger("geoextent")

# Range connectors used by spaCy DATE spans like "between 2010 and 2015"
# or "from 1820 to 1850" or "1820-1850" / "1820–1850".
_RANGE_SPLIT_RE = re.compile(
    r"""^\s*
        (?:between\s+|from\s+)?           # optional opener
        (?P<left>.+?)\s*                  # lazy left side
        (?:
            \s+(?:to|and|until|through)\s+
          | \s*[-–—]\s*                   # ASCII hyphen, en-dash, em-dash
        )
        (?P<right>.+?)\s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

_YEAR_RE = re.compile(r"^\s*(?:the\s+)?(\d{3,4})s?\s*$", re.IGNORECASE)
_DECADE_RE = re.compile(r"^\s*(?:the\s+)?(\d{3,4})0s\s*$", re.IGNORECASE)
_CENTURY_RE = re.compile(
    r"^\s*(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)\s+century\s*$",
    re.IGNORECASE,
)


def _year_envelope(year: int) -> Tuple[str, str]:
    return (hf.signed_iso_format(year, 1, 1), hf.signed_iso_format(year, 12, 31))


def _decade_envelope(decade_start: int) -> Tuple[str, str]:
    return (
        hf.signed_iso_format(decade_start, 1, 1),
        hf.signed_iso_format(decade_start + 9, 12, 31),
    )


def _century_envelope(century: int) -> Tuple[str, str]:
    # The Nth century spans years (N-1)*100+1 .. N*100 inclusive.
    start_year = (century - 1) * 100 + 1
    end_year = century * 100
    return (
        hf.signed_iso_format(start_year, 1, 1),
        hf.signed_iso_format(end_year, 12, 31),
    )


def _parse_single(text: str) -> Optional[Tuple[str, str]]:
    """Parse a single (non-range) DATE/TIME span into an envelope."""
    text = (text or "").strip()
    if not text:
        return None

    m = _CENTURY_RE.match(text)
    if m:
        return _century_envelope(int(m.group(1)))

    m = _DECADE_RE.match(text)
    if m:
        return _decade_envelope(int(m.group(1)) * 10)

    m = _YEAR_RE.match(text)
    if m and not text.lower().rstrip().endswith("s"):
        # Plain year ("1987") — span the whole year.
        return _year_envelope(int(m.group(1)))

    try:
        # Use two sentinels to detect which fields dateutil filled in:
        # if neither parse changed (year, month, day), the input was
        # purely relative ("today") and we can't pin it to a date.
        sentinel_a = date_parser.parse(
            text, default=__import__("datetime").datetime(1, 1, 1)
        )
        sentinel_b = date_parser.parse(
            text, default=__import__("datetime").datetime(2, 2, 2)
        )
    except (ValueError, OverflowError):
        return None

    fields = {
        "year": sentinel_a.year if sentinel_a.year == sentinel_b.year else None,
        "month": sentinel_a.month if sentinel_a.month == sentinel_b.month else None,
        "day": sentinel_a.day if sentinel_a.day == sentinel_b.day else None,
    }
    if fields["year"] is None:
        # Pure time-of-day or fully relative — skip.
        return None
    year = fields["year"]
    month = fields["month"] or None
    day = fields["day"] or None

    if month is None:
        return _year_envelope(year)
    if day is None:
        # Month precision — expand to that month.
        import calendar

        last = calendar.monthrange(year, month)[1]
        return (
            hf.signed_iso_format(year, month, 1),
            hf.signed_iso_format(year, month, last),
        )
    return (hf.signed_iso_format(year, month, day),) * 2


def parse_date_entity(text: str) -> Optional[Tuple[str, str]]:
    """Convert a single DATE/TIME mention text to ``(start_iso, end_iso)``.

    Returns ``None`` for purely relative ("today") or unparseable spans.
    Range expressions like ``"between 2010 and 2015"`` are split and the
    envelope spans both sides.
    """
    text = (text or "").strip()
    if not text:
        return None

    # Try as a single mention first to avoid greedily splitting "May 12, 2024"
    # on its comma-less hyphen-free shape; also handles isolated centuries
    # and decades cleanly.
    single = _parse_single(text)
    if single is not None:
        return single

    # Try range split.
    m = _RANGE_SPLIT_RE.match(text)
    if not m:
        return None
    left_text = m.group("left").strip()
    right_text = m.group("right").strip()
    left = _parse_single(left_text)
    right = _parse_single(right_text)
    if left is None and right is None:
        return None
    # If only the right side is parseable, the left may inherit its
    # year-context (e.g. "January to March 2024" → left="January",
    # right="March 2024").
    if left is None and right is not None:
        rparsed = hf.parse_signed_iso(right[0])
        if rparsed is None:
            return None
        try:
            inferred = f"{left_text} {rparsed[0]}"
            left = _parse_single(inferred)
        except Exception:
            left = None
    if right is None and left is not None:
        return (left[0], left[1])
    if left is None or right is None:
        return None
    start = hf.signed_iso_min([left[0], right[0]])
    end = hf.signed_iso_max([left[1], right[1]])
    if start is None or end is None:
        return None
    return (start, end)
