"""Abstract interface for text extractors."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PlaceMention:
    """A place name found in text."""

    name: str
    label: str  # e.g. "LOC" or "GPE"
    char_start: int
    char_end: int
    score: Optional[float] = None


@dataclass
class DateMention:
    """A date or time expression found in text."""

    text: str
    label: str  # e.g. "DATE" or "TIME"
    char_start: int
    char_end: int


@dataclass
class ExtractionResult:
    places: List[PlaceMention] = field(default_factory=list)
    dates: List[DateMention] = field(default_factory=list)
    # Named time-period mentions (issue #112). Forward reference avoids a
    # circular import with .periods.PeriodMention.
    periods: List["object"] = field(default_factory=list)


class TextExtractor:
    """Abstract base class for text extractors."""

    def extract(self, text: str) -> ExtractionResult:
        raise NotImplementedError

    @property
    def model_name(self) -> str:
        return ""
