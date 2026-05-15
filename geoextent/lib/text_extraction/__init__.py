"""Text-based extraction backends (NER, etc.) for geoextent.

This package provides pluggable text extractors that turn free text into
structured place-name and date mentions. The default backend is spaCy NER.
"""

from .base import TextExtractor, PlaceMention, DateMention

_REGISTRY = {}


def register_extractor(name: str, factory):
    """Register a TextExtractor factory under ``name``."""
    _REGISTRY[name] = factory


def get_extractor(name: str, **config) -> TextExtractor:
    """Instantiate the named extractor with the given configuration."""
    if name not in _REGISTRY:
        raise ValueError(
            f"Unsupported text extraction method: {name!r}. "
            f"Available: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[name](**config)


def available_methods():
    return list(_REGISTRY.keys())


# Lazy NER registration: only attempt to import spaCy when ner is requested.
def _ner_factory(**config):
    from .ner import NerExtractor

    return NerExtractor(**config)


register_extractor("ner", _ner_factory)

__all__ = [
    "TextExtractor",
    "PlaceMention",
    "DateMention",
    "get_extractor",
    "register_extractor",
    "available_methods",
]
