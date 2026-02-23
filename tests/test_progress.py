"""Tests for the progress callback API (geoextent.lib.progress)."""

import pytest
from geoextent.lib.progress import (
    CollectingProgressCallback,
    LoggingProgressCallback,
    ProgressEvent,
    ProgressPhase,
    TqdmProgressCallback,
)

# ---------------------------------------------------------------------------
# ProgressEvent unit tests
# ---------------------------------------------------------------------------


class TestProgressEvent:
    def test_immutable(self):
        event = ProgressEvent(phase=ProgressPhase.SPATIAL, message="test")
        with pytest.raises(AttributeError):
            event.phase = ProgressPhase.TEMPORAL

    def test_fraction_with_total(self):
        event = ProgressEvent(
            phase=ProgressPhase.PROCESS_DIR, message="dir", current=3, total=10
        )
        assert event.fraction == pytest.approx(0.3)

    def test_fraction_indeterminate(self):
        event = ProgressEvent(phase=ProgressPhase.RESOLVE, message="resolving")
        assert event.fraction == -1.0
        assert event.is_indeterminate is True

    def test_fraction_zero_total(self):
        event = ProgressEvent(
            phase=ProgressPhase.MERGE, message="merge", current=0, total=0
        )
        assert event.fraction == -1.0
        assert event.is_indeterminate is True

    def test_defaults(self):
        event = ProgressEvent(phase=ProgressPhase.DOWNLOAD, message="dl")
        assert event.current == 0
        assert event.total == 0
        assert event.detail is None
        assert event.bytes_current == 0
        assert event.bytes_total == 0

    def test_all_phases_are_strings(self):
        for phase in ProgressPhase:
            assert isinstance(phase.value, str)


# ---------------------------------------------------------------------------
# CollectingProgressCallback tests
# ---------------------------------------------------------------------------


class TestCollectingProgressCallback:
    def test_collects_events(self):
        cb = CollectingProgressCallback()
        e1 = ProgressEvent(phase=ProgressPhase.RESOLVE, message="found provider")
        e2 = ProgressEvent(
            phase=ProgressPhase.DOWNLOAD,
            message="downloading",
            current=1,
            total=5,
        )
        cb(e1)
        cb(e2)
        assert len(cb.events) == 2
        assert cb.events[0] is e1
        assert cb.events[1] is e2


# ---------------------------------------------------------------------------
# LoggingProgressCallback tests
# ---------------------------------------------------------------------------


class TestLoggingProgressCallback:
    def test_logs_events(self, caplog):
        import logging

        cb = LoggingProgressCallback(level=logging.INFO)
        event = ProgressEvent(
            phase=ProgressPhase.SPATIAL,
            message="Processing file.tif",
            current=1,
            total=2,
            detail="bbox extracted",
        )
        with caplog.at_level(logging.INFO, logger="geoextent"):
            cb(event)
        assert "spatial" in caplog.text.lower()
        assert "Processing file.tif" in caplog.text


# ---------------------------------------------------------------------------
# TqdmProgressCallback tests
# ---------------------------------------------------------------------------


class TestTqdmProgressCallback:
    def test_creates_and_closes_bars(self):
        cb = TqdmProgressCallback(leave=False)
        cb(
            ProgressEvent(
                phase=ProgressPhase.PROCESS_DIR,
                message="Processing dir",
                current=1,
                total=3,
            )
        )
        assert ProgressPhase.PROCESS_DIR in cb._bars
        cb.close()
        assert len(cb._bars) == 0

    def test_phase_change_closes_old_bar(self):
        cb = TqdmProgressCallback(leave=False)
        cb(
            ProgressEvent(
                phase=ProgressPhase.PROCESS_DIR,
                message="dir",
                current=1,
                total=2,
            )
        )
        cb(
            ProgressEvent(
                phase=ProgressPhase.MERGE,
                message="merging",
            )
        )
        # Old phase should be closed
        assert ProgressPhase.PROCESS_DIR not in cb._bars
        assert ProgressPhase.MERGE in cb._bars
        cb.close()


# ---------------------------------------------------------------------------
# Integration: from_file with progress_callback
# ---------------------------------------------------------------------------


class TestFromFileProgressCallback:
    def test_from_file_emits_events(self):
        from geoextent.lib import extent

        cb = CollectingProgressCallback()
        result = extent.from_file(
            "tests/testdata/tif/wf_100m_klas.tif",
            bbox=True,
            tbox=True,
            show_progress=False,
            progress_callback=cb,
        )
        assert result is not None

        phases = [e.phase for e in cb.events]
        assert ProgressPhase.PROCESS_FILE in phases
        assert ProgressPhase.SPATIAL in phases

    def test_from_file_bbox_only(self):
        from geoextent.lib import extent

        cb = CollectingProgressCallback()
        result = extent.from_file(
            "tests/testdata/tif/wf_100m_klas.tif",
            bbox=True,
            tbox=False,
            show_progress=False,
            progress_callback=cb,
        )
        assert result is not None

        phases = [e.phase for e in cb.events]
        assert ProgressPhase.PROCESS_FILE in phases
        assert ProgressPhase.SPATIAL in phases
        # TEMPORAL should NOT appear since tbox=False
        assert ProgressPhase.TEMPORAL not in phases

    def test_from_file_no_callback(self):
        """Ensure from_file works without progress_callback (backward compat)."""
        from geoextent.lib import extent

        result = extent.from_file(
            "tests/testdata/tif/wf_100m_klas.tif",
            bbox=True,
            show_progress=False,
        )
        assert result is not None
        assert "bbox" in result

    def test_from_file_show_progress_true_no_callback(self):
        """When show_progress=True and no callback, auto-tqdm should work."""
        from geoextent.lib import extent

        result = extent.from_file(
            "tests/testdata/tif/wf_100m_klas.tif",
            bbox=True,
            show_progress=True,
        )
        assert result is not None
        assert "bbox" in result


# ---------------------------------------------------------------------------
# Integration: from_directory with progress_callback
# ---------------------------------------------------------------------------


class TestFromDirectoryProgressCallback:
    def test_from_directory_emits_events(self):
        from geoextent.lib import extent

        cb = CollectingProgressCallback()
        result = extent.from_directory(
            "tests/testdata/tif/",
            bbox=True,
            show_progress=False,
            progress_callback=cb,
        )
        assert result is not None

        phases = [e.phase for e in cb.events]
        assert ProgressPhase.PROCESS_DIR in phases
        assert ProgressPhase.MERGE in phases

    def test_from_directory_current_total_tracking(self):
        from geoextent.lib import extent

        cb = CollectingProgressCallback()
        extent.from_directory(
            "tests/testdata/tif/",
            bbox=True,
            show_progress=False,
            progress_callback=cb,
        )

        dir_events = [e for e in cb.events if e.phase == ProgressPhase.PROCESS_DIR]
        if dir_events:
            last = dir_events[-1]
            assert last.current == last.total
            assert last.total > 0

    def test_from_directory_no_callback(self):
        """Ensure from_directory works without progress_callback (backward compat)."""
        from geoextent.lib import extent

        result = extent.from_directory(
            "tests/testdata/tif/",
            bbox=True,
            show_progress=False,
        )
        assert result is not None
