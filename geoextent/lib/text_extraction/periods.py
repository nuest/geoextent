"""spaCy PhraseMatcher over named time periods (issue #112).

The matcher catches geological and historical period names (e.g.
``"Holocene"``, ``"Mesozoic Era"``) regardless of how spaCy's NER classifies
them — research shows the default English models often emit ``ORG``,
``PERSON``, or no entity at all for these terms, so we cannot rely on
``DATE``-only filtering.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger("geoextent")


@dataclass
class PeriodMention:
    """A named time-period span detected in text."""

    text: str
    char_start: int
    char_end: int
    matched_label: str  # lowercase label that hit the matcher


def build_phrase_matcher(nlp, gazetteer):
    """Return a :class:`spacy.matcher.PhraseMatcher` built from ``gazetteer``.

    The matcher is case-insensitive (``attr="LOWER"``) and uses the union of
    each period's primary name plus its aliases as match patterns.
    """
    from spacy.matcher import PhraseMatcher

    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    index = gazetteer.label_index()
    if not index:
        return matcher

    # Make patterns from the canonical lowercase labels. We tokenise via the
    # same pipeline so the matcher's tokens align with the document's tokens.
    patterns = [nlp.make_doc(label) for label in index.keys()]
    matcher.add("PERIOD", patterns)
    return matcher


def extract_periods(doc, matcher) -> List[PeriodMention]:
    """Return non-overlapping :class:`PeriodMention` spans found in ``doc``.

    When two matches overlap (e.g. ``"Late Cretaceous"`` vs ``"Cretaceous"``),
    the longer span wins; ties resolve to the earlier start offset.
    """
    if matcher is None:
        return []
    matches = matcher(doc)
    if not matches:
        return []

    # Convert to spans, keep the longest per overlap-cluster.
    spans = []
    for _, start, end in matches:
        span = doc[start:end]
        spans.append(span)
    # Sort by length desc, then by start asc; greedy non-overlap select.
    spans.sort(key=lambda s: (-(s.end - s.start), s.start))
    selected = []
    consumed = set()
    for s in spans:
        token_indices = set(range(s.start, s.end))
        if token_indices & consumed:
            continue
        consumed |= token_indices
        selected.append(s)

    selected.sort(key=lambda s: s.start)
    return [
        PeriodMention(
            text=s.text,
            char_start=s.start_char,
            char_end=s.end_char,
            matched_label=s.text.lower(),
        )
        for s in selected
    ]
