"""Map preview rendering for geoextent spatial extents.

Requires the ``preview`` optional dependency group::

    pip install geoextent[preview]
"""

import logging
import os
import shutil
import subprocess
import sys
import tempfile

from pathlib import Path

logger = logging.getLogger("geoextent")

# Terminals known to not support OSC 8 hyperlinks
_OSC8_BLOCKLIST = {"dumb", "linux"}


def _supports_osc8(stream=None):
    """Check whether *stream* likely supports OSC 8 hyperlinks.

    Returns ``True`` when the stream is a TTY and the ``TERM`` value is
    not in the blocklist.  This is a heuristic — there is no reliable
    capability query for OSC 8.
    """
    if stream is None:
        stream = sys.stderr
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False
    term = os.environ.get("TERM", "")
    return term not in _OSC8_BLOCKLIST


def _osc8_link(url, text):
    """Return *text* wrapped in an OSC 8 hyperlink escape sequence."""
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


def file_uri(path):
    """Convert a filesystem path to a ``file://`` URI."""
    return Path(path).resolve().as_uri()


def render_map(bbox, convex_hull_coords=None, width=600, height=400):
    """Render a map image with the spatial extent overlaid on OSM tiles.

    Parameters
    ----------
    bbox : list
        4-element list ``[minlon, minlat, maxlon, maxlat]`` (internal GIS order).
    convex_hull_coords : list or None
        List of ``[lon, lat]`` pairs (internal GIS order), or ``None``.
    width, height : int
        Image dimensions in pixels.

    Returns
    -------
    PIL.Image.Image
        Rendered map image with attribution bar.
    """
    try:
        from staticmap import StaticMap, Polygon
    except ImportError:
        raise ImportError(
            "The 'staticmap' package is required for map preview. "
            "Install it with: pip install geoextent[preview]"
        )

    m = StaticMap(width, height, padding_x=16, padding_y=16)

    if convex_hull_coords is not None:
        # convex_hull_coords is a list of [lon, lat] pairs
        coords = [tuple(c) for c in convex_hull_coords]
        polygon = Polygon(coords, fill_color="#3388ff40", outline_color="#3388ff")
        m.add_polygon(polygon)
    elif bbox is not None and len(bbox) == 4:
        minlon, minlat, maxlon, maxlat = bbox
        coords = [
            (minlon, minlat),
            (maxlon, minlat),
            (maxlon, maxlat),
            (minlon, maxlat),
            (minlon, minlat),
        ]
        polygon = Polygon(coords, fill_color="#3388ff40", outline_color="#3388ff")
        m.add_polygon(polygon)
    else:
        raise ValueError("Either bbox or convex_hull_coords must be provided")

    image = m.render()
    image = _add_attribution_bar(image)
    return image


def _add_attribution_bar(image):
    """Add a semi-transparent attribution bar at the bottom of the image.

    Parameters
    ----------
    image : PIL.Image.Image
        The rendered map image.

    Returns
    -------
    PIL.Image.Image
        Image with attribution overlay (RGB mode for PNG saving).
    """
    from PIL import Image, ImageDraw, ImageFont

    import geoextent

    version = geoextent.__version__
    text = f"Created with geoextent {version} | (c) OpenStreetMap contributors"

    image = image.convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    bar_height = 20
    y_start = image.size[1] - bar_height
    draw.rectangle(
        [(0, y_start), (image.size[0], image.size[1])],
        fill=(0, 0, 0, 160),
    )

    font = ImageFont.load_default()
    draw.text((4, y_start + 3), text, fill=(255, 255, 255, 255), font=font)

    image = Image.alpha_composite(image, overlay)
    return image.convert("RGB")


def save_map(output, map_path=None, dimensions=(600, 400), native_order=False):
    """Render and save a map preview from extraction output.

    Parameters
    ----------
    output : dict
        The extraction result dict (after coordinate swap at API boundary).
    map_path : str or None
        File path for the PNG output. If ``None``, a temporary file is used.
    dimensions : tuple
        ``(width, height)`` in pixels.
    native_order : bool
        If ``True``, bbox is in ``[lat, lon]`` order and needs reversing
        to internal ``[lon, lat]`` order for rendering.

    Returns
    -------
    str
        The file path where the map image was saved.
    """
    bbox_raw = output.get("bbox")
    is_convex_hull = output.get("convex_hull", False)

    convex_hull_coords = None
    bbox = None

    if (
        is_convex_hull
        and isinstance(bbox_raw, list)
        and len(bbox_raw) > 0
        and isinstance(bbox_raw[0], list)
    ):
        # Convex hull: list of coordinate pairs
        if native_order:
            convex_hull_coords = [[c[1], c[0]] for c in bbox_raw]
        else:
            convex_hull_coords = bbox_raw
    elif isinstance(bbox_raw, list) and len(bbox_raw) == 4:
        if native_order:
            # Swap from [minlat, minlon, maxlat, maxlon] to [minlon, minlat, maxlon, maxlat]
            bbox = [bbox_raw[1], bbox_raw[0], bbox_raw[3], bbox_raw[2]]
        else:
            bbox = bbox_raw
    else:
        raise ValueError("No valid spatial extent found in output")

    width, height = dimensions
    image = render_map(bbox, convex_hull_coords, width, height)

    if map_path is None:
        # Use a temp file that persists for the user
        fd, map_path = tempfile.mkstemp(suffix=".png", prefix="geoextent_map_")
        # Close the fd — we'll write via PIL
        import os

        os.close(fd)

    image.save(map_path, "PNG")
    logger.info("Map preview saved to: %s", map_path)
    return map_path


def format_map_saved_message(image_path, stream=None):
    """Format the 'Map preview saved to' message.

    When *stream* supports OSC 8 hyperlinks the message includes the plain
    path followed by a clickable ``[open]`` link.  Otherwise only the plain
    path is shown.

    Parameters
    ----------
    image_path : str
        Absolute or relative path to the saved PNG.
    stream : file-like or None
        The output stream (defaults to ``sys.stderr``).

    Returns
    -------
    str
        Formatted message ready for ``print(..., file=stream)``.
    """
    abs_path = str(Path(image_path).resolve())
    if _supports_osc8(stream):
        uri = file_uri(abs_path)
        link = _osc8_link(uri, "open")
        return f"🗺️ Map preview saved to: {abs_path} [{link}]"
    return f"🗺️ Map preview saved to: {abs_path}"


def _display_with_term_image(image_path):
    """Try to display an image using the term-image Python library.

    term-image auto-detects the best terminal graphics protocol
    (Kitty, iTerm2, Sixel) and falls back to Unicode block characters.

    Returns
    -------
    bool
        ``True`` if display succeeded, ``False`` otherwise.
    """
    try:
        from term_image.image import from_file

        image = from_file(image_path)
        image.draw()
        return True
    except ImportError:
        return False
    except Exception as e:
        logger.debug("term-image display failed: %s", e)
        return False


def display_in_terminal(image_path):
    """Display an image in the terminal.

    Fallback chain:

    1. ``term-image`` Python library (auto-detects Kitty/iTerm2/Sixel,
       falls back to Unicode block characters)
    2. External CLI tools: ``chafa``, ``timg``, ``catimg``
    3. Print the file path

    Parameters
    ----------
    image_path : str
        Path to the PNG image to display.

    Returns
    -------
    bool
        ``True`` if an image viewer was used, ``False`` if only the path was printed.
    """
    if _display_with_term_image(image_path):
        return True

    for tool in ("chafa", "timg", "catimg"):
        path = shutil.which(tool)
        if path is not None:
            try:
                subprocess.run([path, image_path], check=True)
                return True
            except (subprocess.CalledProcessError, OSError):
                continue

    print(f"Map preview: {image_path}")
    return False
