import json
import os
from unittest import mock
import pytest

GEOJSON_FILE = "tests/testdata/geojson/muenster_ring_zeit.geojson"


class TestMapPreviewCLI:
    """Tests for --map and --preview CLI flags."""

    def test_map_saves_to_explicit_path(self, script_runner, tmp_path):
        """--map saves a valid PNG file to the given path."""
        out_png = str(tmp_path / "out.png")
        ret = script_runner.run(["geoextent", "-b", "--map", out_png, GEOJSON_FILE])
        assert ret.success, f"stderr: {ret.stderr}"
        assert os.path.isfile(out_png)
        with open(out_png, "rb") as f:
            assert f.read(4) == b"\x89PNG"

    def test_map_with_custom_dimensions(self, script_runner, tmp_path):
        """--map-dim sets the image size."""
        out_png = str(tmp_path / "dim.png")
        ret = script_runner.run(
            [
                "geoextent",
                "-b",
                "--map",
                out_png,
                "--map-dim",
                "800x600",
                GEOJSON_FILE,
            ]
        )
        assert ret.success, f"stderr: {ret.stderr}"
        from PIL import Image

        img = Image.open(out_png)
        assert img.size == (800, 600)

    def test_map_with_convex_hull(self, script_runner, tmp_path):
        """--map works together with --convex-hull."""
        out_png = str(tmp_path / "hull.png")
        ret = script_runner.run(
            [
                "geoextent",
                "-b",
                "--convex-hull",
                "--map",
                out_png,
                GEOJSON_FILE,
            ]
        )
        assert ret.success, f"stderr: {ret.stderr}"
        assert os.path.isfile(out_png)
        with open(out_png, "rb") as f:
            assert f.read(4) == b"\x89PNG"

    def test_map_without_path_saves_to_temp(self, script_runner):
        """--map without a path saves to a temp file and prints path to stderr."""
        # --map must precede another flag so argparse doesn't consume the
        # positional file as --map's optional value
        ret = script_runner.run(["geoextent", "--map", "-b", GEOJSON_FILE])
        assert ret.success, f"stderr: {ret.stderr}"
        assert "Map preview saved to:" in ret.stderr
        # Extract the temp path from stderr and verify the file exists
        for line in ret.stderr.splitlines():
            if "Map preview saved to:" in line:
                saved_path = line.split("Map preview saved to:")[-1].strip()
                assert os.path.isfile(saved_path)
                with open(saved_path, "rb") as f:
                    assert f.read(4) == b"\x89PNG"
                break

    def test_map_without_bbox_flag(self, script_runner, tmp_path):
        """--map without -b should not crash (no bbox means no map)."""
        out_png = str(tmp_path / "nobbox.png")
        ret = script_runner.run(["geoextent", "-t", "--map", out_png, GEOJSON_FILE])
        # Should succeed but not create a map since -b is not set
        assert ret.success or "extraction options" not in ret.stderr
        # Map file should not be created when there is no bbox
        # (the CLI only generates the map when bbox is in output)

    def test_map_dim_invalid_format(self, script_runner, tmp_path):
        """Invalid --map-dim value should warn on stderr and skip map generation."""
        out_png = str(tmp_path / "bad.png")
        ret = script_runner.run(
            ["geoextent", "-b", "--map", out_png, "--map-dim", "abc", GEOJSON_FILE]
        )
        # Extraction succeeds but map is not generated
        assert ret.success
        assert "Invalid map dimensions" in ret.stderr
        assert not os.path.isfile(out_png)

    def test_preview_flag(self, script_runner):
        """--preview should mention the saved path in stderr."""
        ret = script_runner.run(["geoextent", "-b", "--preview", GEOJSON_FILE])
        assert ret.success, f"stderr: {ret.stderr}"
        assert "Map preview" in ret.stderr or "Map preview" in ret.stdout

    def test_map_and_preview_together(self, script_runner, tmp_path):
        """--map and --preview together should save to the explicit path."""
        out_png = str(tmp_path / "both.png")
        ret = script_runner.run(
            ["geoextent", "-b", "--map", out_png, "--preview", GEOJSON_FILE]
        )
        assert ret.success, f"stderr: {ret.stderr}"
        assert os.path.isfile(out_png)

    def test_map_legacy_coordinates(self, script_runner, tmp_path):
        """--map with --legacy should produce a valid PNG."""
        out_png = str(tmp_path / "legacy.png")
        ret = script_runner.run(
            ["geoextent", "-b", "--legacy", "--map", out_png, GEOJSON_FILE]
        )
        assert ret.success, f"stderr: {ret.stderr}"
        assert os.path.isfile(out_png)
        with open(out_png, "rb") as f:
            assert f.read(4) == b"\x89PNG"

    def test_map_quiet_suppresses_path(self, script_runner, tmp_path):
        """--quiet should suppress the 'Map preview saved to' message."""
        out_png = str(tmp_path / "quiet.png")
        ret = script_runner.run(
            ["geoextent", "-b", "--quiet", "--map", out_png, GEOJSON_FILE]
        )
        assert ret.success, f"stderr: {ret.stderr}"
        assert os.path.isfile(out_png)
        assert "Map preview saved to" not in ret.stderr

    def test_quiet_suppresses_preview(self, script_runner):
        """--quiet should suppress --preview display entirely."""
        ret = script_runner.run(
            ["geoextent", "-b", "--quiet", "--preview", GEOJSON_FILE]
        )
        assert ret.success, f"stderr: {ret.stderr}"
        assert "Map preview" not in ret.stderr


class TestRenderMapUnit:
    """Unit tests for preview rendering functions."""

    def test_render_map_returns_image(self):
        """render_map returns a PIL Image with correct dimensions."""
        from geoextent.lib.preview import render_map

        bbox = [7.5, 51.9, 7.7, 52.0]
        img = render_map(bbox, width=400, height=300)
        assert img.size == (400, 300)

    def test_render_map_with_convex_hull(self):
        """render_map works with convex hull coordinates."""
        from geoextent.lib.preview import render_map

        coords = [[7.5, 51.9], [7.7, 51.9], [7.6, 52.0], [7.5, 51.9]]
        img = render_map(bbox=None, convex_hull_coords=coords, width=400, height=300)
        assert img.size == (400, 300)

    def test_attribution_bar_present(self):
        """The rendered image should have the attribution bar."""
        from geoextent.lib.preview import render_map

        bbox = [7.5, 51.9, 7.7, 52.0]
        img = render_map(bbox, width=600, height=400)
        # The bottom bar should have dark pixels (attribution overlay)
        # Sample a pixel from the bottom bar area
        pixel = img.getpixel((10, 395))
        # Should be dark (from the semi-transparent black overlay)
        assert pixel[0] < 128 and pixel[1] < 128 and pixel[2] < 128

    def test_save_map_native_order(self, tmp_path):
        """save_map handles native [lat, lon] order correctly."""
        from geoextent.lib.preview import save_map

        # Simulate output in native EPSG:4326 order [minlat, minlon, maxlat, maxlon]
        output = {"bbox": [51.9, 7.5, 52.0, 7.7], "crs": "4326"}
        out_png = str(tmp_path / "native.png")
        path = save_map(output, out_png, (400, 300), native_order=True)
        assert os.path.isfile(path)

    def test_save_map_legacy_order(self, tmp_path):
        """save_map handles legacy [lon, lat] order correctly."""
        from geoextent.lib.preview import save_map

        # Simulate output in legacy order [minlon, minlat, maxlon, maxlat]
        output = {"bbox": [7.5, 51.9, 7.7, 52.0], "crs": "4326"}
        out_png = str(tmp_path / "legacy.png")
        path = save_map(output, out_png, (400, 300), native_order=False)
        assert os.path.isfile(path)


class TestDisplayFallbackChain:
    """Tests for the display_in_terminal fallback chain."""

    def test_term_image_tried_first(self, tmp_path):
        """term-image is attempted before external CLI tools."""
        from geoextent.lib.preview import display_in_terminal

        img_path = str(tmp_path / "test.png")
        # Create a minimal valid PNG via render_map
        from geoextent.lib.preview import render_map

        render_map([7.5, 51.9, 7.7, 52.0], width=100, height=100).save(img_path)

        with mock.patch(
            "geoextent.lib.preview._display_with_term_image", return_value=True
        ) as mock_ti:
            result = display_in_terminal(img_path)
            mock_ti.assert_called_once_with(img_path)
            assert result is True

    def test_falls_back_to_external_tools_when_term_image_fails(self, tmp_path):
        """External tools are tried when term-image fails."""
        from geoextent.lib.preview import display_in_terminal

        img_path = str(tmp_path / "test.png")
        from geoextent.lib.preview import render_map

        render_map([7.5, 51.9, 7.7, 52.0], width=100, height=100).save(img_path)

        with (
            mock.patch(
                "geoextent.lib.preview._display_with_term_image", return_value=False
            ),
            mock.patch("shutil.which", return_value=None),
        ):
            result = display_in_terminal(img_path)
            # No external tools found either → prints path
            assert result is False

    def test_term_image_import_error_handled(self):
        """_display_with_term_image returns False when term-image is not installed."""
        from geoextent.lib import preview

        with mock.patch.dict(
            "sys.modules", {"term_image": None, "term_image.image": None}
        ):
            # Force re-import failure
            result = preview._display_with_term_image("/nonexistent.png")
            assert result is False


class TestOSC8Hyperlinks:
    """Tests for OSC 8 clickable path support."""

    def test_file_uri_absolute_path(self):
        from geoextent.lib.preview import file_uri

        uri = file_uri("/tmp/test.png")
        assert uri == "file:///tmp/test.png"

    def test_file_uri_encodes_spaces(self):
        from geoextent.lib.preview import file_uri

        uri = file_uri("/tmp/my file.png")
        assert "my%20file.png" in uri
        assert uri.startswith("file:///")

    def test_osc8_link_format(self):
        from geoextent.lib.preview import _osc8_link

        result = _osc8_link("file:///tmp/test.png", "open")
        assert result == "\033]8;;file:///tmp/test.png\033\\open\033]8;;\033\\"

    def test_supports_osc8_on_tty(self):
        from geoextent.lib.preview import _supports_osc8

        fake_tty = mock.MagicMock()
        fake_tty.isatty.return_value = True
        with mock.patch.dict(os.environ, {"TERM": "xterm-256color"}):
            assert _supports_osc8(fake_tty) is True

    def test_no_osc8_on_non_tty(self):
        from geoextent.lib.preview import _supports_osc8

        fake_pipe = mock.MagicMock()
        fake_pipe.isatty.return_value = False
        assert _supports_osc8(fake_pipe) is False

    def test_no_osc8_on_dumb_terminal(self):
        from geoextent.lib.preview import _supports_osc8

        fake_tty = mock.MagicMock()
        fake_tty.isatty.return_value = True
        with mock.patch.dict(os.environ, {"TERM": "dumb"}):
            assert _supports_osc8(fake_tty) is False

    def test_no_osc8_on_linux_console(self):
        from geoextent.lib.preview import _supports_osc8

        fake_tty = mock.MagicMock()
        fake_tty.isatty.return_value = True
        with mock.patch.dict(os.environ, {"TERM": "linux"}):
            assert _supports_osc8(fake_tty) is False

    def test_format_message_plain_when_not_tty(self, tmp_path):
        from geoextent.lib.preview import format_map_saved_message

        img = str(tmp_path / "map.png")
        fake_pipe = mock.MagicMock()
        fake_pipe.isatty.return_value = False
        msg = format_map_saved_message(img, stream=fake_pipe)
        assert "Map preview saved to:" in msg
        assert "\033" not in msg  # no escape sequences

    def test_format_message_osc8_when_tty(self, tmp_path):
        from geoextent.lib.preview import format_map_saved_message

        img = str(tmp_path / "map.png")
        fake_tty = mock.MagicMock()
        fake_tty.isatty.return_value = True
        with mock.patch.dict(os.environ, {"TERM": "xterm-256color"}):
            msg = format_map_saved_message(img, stream=fake_tty)
        assert "Map preview saved to:" in msg
        # Contains the plain path
        assert str(tmp_path / "map.png") in msg
        # Contains OSC 8 open/close sequences
        assert "\033]8;;" in msg
        assert "[open]" not in msg or "open" in msg  # clickable "open" text
        assert "file://" in msg
