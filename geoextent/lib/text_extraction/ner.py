"""spaCy-based named entity recognition for place and date mentions."""

import logging
from typing import Iterable, Optional, Set

from .base import DateMention, ExtractionResult, PlaceMention, TextExtractor

logger = logging.getLogger("geoextent")

DEFAULT_MODEL = "en_core_web_sm"
DEFAULT_PLACE_LABELS = frozenset({"LOC", "GPE"})
DEFAULT_DATE_LABELS = frozenset({"DATE", "TIME"})

_NLP_CACHE = {}


def _try_import_spacy():
    try:
        import spacy
    except ImportError as e:
        raise ImportError(
            "spaCy is required for text NER extraction. "
            "Install with: pip install 'geoextent[nlp]' "
            "and download a model: python -m spacy download en_core_web_sm"
        ) from e
    return spacy


def _load_model(model_name: str, auto_download: bool):
    """Load a spaCy model, optionally downloading it on first use."""
    if model_name in _NLP_CACHE:
        return _NLP_CACHE[model_name]
    spacy = _try_import_spacy()
    try:
        nlp = spacy.load(model_name)
    except OSError:
        if not auto_download:
            raise OSError(
                f"spaCy model {model_name!r} is not installed. "
                f"Run: python -m spacy download {model_name} "
                f"(or pass --no-auto-download=False)"
            )
        logger.info(
            "spaCy model %r not found locally, downloading (one-time)...",
            model_name,
        )
        from spacy.cli import download as spacy_download

        spacy_download(model_name)
        nlp = spacy.load(model_name)
    _NLP_CACHE[model_name] = nlp
    return nlp


class NerExtractor(TextExtractor):
    """Extract place and date mentions using spaCy NER."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        place_labels: Optional[Iterable[str]] = None,
        date_labels: Optional[Iterable[str]] = None,
        score_threshold: Optional[float] = None,
        auto_download: bool = True,
        period_gazetteer=None,
        period_resolution: bool = True,
    ):
        self._model_name = model
        self._place_labels: Set[str] = (
            set(place_labels) if place_labels else set(DEFAULT_PLACE_LABELS)
        )
        self._date_labels: Set[str] = (
            set(date_labels) if date_labels else set(DEFAULT_DATE_LABELS)
        )
        self._score_threshold = score_threshold
        self._auto_download = auto_download
        self._period_gazetteer = period_gazetteer
        self._period_resolution = period_resolution
        self._nlp = None
        self._phrase_matcher = None

    @property
    def model_name(self) -> str:
        return self._model_name

    def _ensure_loaded(self):
        if self._nlp is None:
            self._nlp = _load_model(self._model_name, self._auto_download)
        return self._nlp

    def _ensure_matcher(self):
        if not self._period_resolution or self._period_gazetteer is None:
            return None
        if self._phrase_matcher is None:
            from .periods import build_phrase_matcher

            self._phrase_matcher = build_phrase_matcher(
                self._ensure_loaded(), self._period_gazetteer
            )
        return self._phrase_matcher

    def extract(self, text: str) -> ExtractionResult:
        result = ExtractionResult()
        if not text or not text.strip():
            return result

        nlp = self._ensure_loaded()
        doc = nlp(text)

        # Period spans win over overlapping NER entities (issue #112).
        from .periods import extract_periods as _extract_periods

        matcher = self._ensure_matcher()
        period_spans = _extract_periods(doc, matcher) if matcher is not None else []
        result.periods = period_spans
        period_ranges = [(p.char_start, p.char_end) for p in period_spans]

        def _overlaps_period(ent_start: int, ent_end: int) -> bool:
            for ps, pe in period_ranges:
                if ent_start < pe and ps < ent_end:
                    return True
            return False

        # spaCy NER does not emit per-entity confidence scores by default.
        # If a future model attaches them as ent._.score we will pick them up.
        threshold_skipped = 0
        for ent in doc.ents:
            score = getattr(getattr(ent, "_", None), "score", None)
            if (
                self._score_threshold is not None
                and score is not None
                and score < self._score_threshold
            ):
                threshold_skipped += 1
                continue

            # PhraseMatcher wins over NER for bundled period names
            # (e.g. "Holocene" mislabelled as ORG, "Bronze Age" as PERSON):
            # skip entities whose span overlaps a matched period.
            if _overlaps_period(ent.start_char, ent.end_char):
                continue

            if ent.label_ in self._place_labels:
                result.places.append(
                    PlaceMention(
                        name=ent.text,
                        label=ent.label_,
                        char_start=ent.start_char,
                        char_end=ent.end_char,
                        score=score,
                    )
                )
            elif ent.label_ in self._date_labels:
                result.dates.append(
                    DateMention(
                        text=ent.text,
                        label=ent.label_,
                        char_start=ent.start_char,
                        char_end=ent.end_char,
                    )
                )

        if self._score_threshold is not None and threshold_skipped:
            logger.debug(
                "%d entities below score threshold %s",
                threshold_skipped,
                self._score_threshold,
            )
        if self._score_threshold is not None and not any(
            getattr(getattr(e, "_", None), "score", None) is not None for e in doc.ents
        ):
            logger.debug(
                "Score threshold set but model %r emits no per-entity scores; "
                "threshold ignored.",
                self._model_name,
            )
        return result
