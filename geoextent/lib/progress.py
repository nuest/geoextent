"""Progress callback API for geoextent operations.

Provides structured progress events that decouple the library from any
specific UI framework.  The three public API functions (``from_file``,
``from_directory``, ``from_remote``) accept a ``progress_callback``
parameter — a callable that receives :class:`ProgressEvent` instances.

Built-in callbacks:

* :class:`TqdmProgressCallback` — renders tqdm progress bars (used by CLI)
* :class:`LoggingProgressCallback` — writes events to the ``geoextent`` logger
* :class:`CollectingProgressCallback` — collects events into a list (testing)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Optional
import logging

logger = logging.getLogger("geoextent")


class ProgressPhase(Enum):
    """Phases of geoextent processing."""

    RESOLVE = "resolve"
    DOWNLOAD = "download"
    EXTRACT = "extract"
    PROCESS_FILE = "process_file"
    PROCESS_DIR = "process_dir"
    SPATIAL = "spatial"
    TEMPORAL = "temporal"
    MERGE = "merge"
    PLACENAME = "placename"


@dataclass(frozen=True)
class ProgressEvent:
    """Immutable progress event emitted by geoextent operations."""

    phase: ProgressPhase
    message: str
    current: int = 0
    total: int = 0
    detail: Optional[str] = None
    bytes_current: int = 0
    bytes_total: int = 0

    @property
    def fraction(self) -> float:
        """Return progress fraction (0.0–1.0), or -1.0 if indeterminate."""
        return self.current / self.total if self.total > 0 else -1.0

    @property
    def is_indeterminate(self) -> bool:
        """Return True when total is unknown."""
        return self.total <= 0


ProgressCallback = Callable[[ProgressEvent], None]


# ---------------------------------------------------------------------------
# Built-in callback implementations
# ---------------------------------------------------------------------------


class TqdmProgressCallback:
    """Render tqdm progress bars per phase.

    Each distinct phase gets its own bar.  Bars are created lazily on first
    event and closed when a new phase starts or when :meth:`close` is called.
    """

    def __init__(self, leave: bool = False):
        self._leave = leave
        self._bars = {}  # phase -> tqdm bar
        self._current_phase = None

    def __call__(self, event: ProgressEvent) -> None:
        from tqdm import tqdm

        phase = event.phase

        # If phase changed, close the old bar
        if phase != self._current_phase and self._current_phase in self._bars:
            self._bars[self._current_phase].close()
            del self._bars[self._current_phase]

        self._current_phase = phase

        if phase not in self._bars:
            # Determine unit
            if phase == ProgressPhase.DOWNLOAD and event.bytes_total > 0:
                self._bars[phase] = tqdm(
                    total=event.bytes_total,
                    desc=event.message,
                    unit="B",
                    unit_scale=True,
                    leave=self._leave,
                )
            elif event.total > 0:
                unit = {
                    ProgressPhase.PROCESS_DIR: "item",
                    ProgressPhase.PROCESS_FILE: "task",
                    ProgressPhase.PLACENAME: "point",
                }.get(phase, "it")
                self._bars[phase] = tqdm(
                    total=event.total,
                    desc=event.message,
                    unit=unit,
                    leave=self._leave,
                )
            else:
                # Indeterminate
                self._bars[phase] = tqdm(
                    desc=event.message,
                    unit="it",
                    leave=self._leave,
                )

        bar = self._bars[phase]

        # Update bar
        if event.detail:
            bar.set_postfix_str(event.detail)

        if phase == ProgressPhase.DOWNLOAD and event.bytes_total > 0:
            # Byte-level progress
            increment = event.bytes_current - bar.n
            if increment > 0:
                bar.update(increment)
        elif event.total > 0:
            # Step-level progress
            increment = event.current - bar.n
            if increment > 0:
                bar.update(increment)

    def close(self):
        """Close all open progress bars."""
        for bar in self._bars.values():
            bar.close()
        self._bars.clear()


class LoggingProgressCallback:
    """Log progress events to the ``geoextent`` logger at INFO level."""

    def __init__(self, level: int = logging.INFO):
        self._level = level
        self._logger = logging.getLogger("geoextent")

    def __call__(self, event: ProgressEvent) -> None:
        parts = [f"[{event.phase.value}] {event.message}"]
        if event.total > 0:
            parts.append(f"({event.current}/{event.total})")
        if event.detail:
            parts.append(f"- {event.detail}")
        self._logger.log(self._level, " ".join(parts))


class CollectingProgressCallback:
    """Collect events into a list.  Useful for testing."""

    def __init__(self):
        self.events: List[ProgressEvent] = []

    def __call__(self, event: ProgressEvent) -> None:
        self.events.append(event)
