"""Text-file detection by extension, filename, and content sniffing.

``mimetypes.guess_type`` is just another extension lookup over a stdlib
table, so a pure-MIME approach misses common cases (``README``,
``LICENSE``, ``.log``, ``.adoc``) and over-matches source code that
``mimetypes`` happens to label ``text/x-python`` etc. This module does
three things in order — extension fast-paths first (cheap, no I/O),
then ``mimetypes`` as a confirming-only hint, then a small content
sniff for everything else. The content sniff reads at most 8 KB.
"""

import logging
import mimetypes
import os

logger = logging.getLogger("geoextent")

#: Plain-text extensions geoextent considers NER candidates. Single
#: source of truth — also consumed by ``handle_csv`` (deferral rule) and
#: ``features.py`` (``--list-features`` listing). Add new plain-text
#: extensions here only.
TEXT_EXTENSIONS = frozenset({".txt", ".md", ".markdown", ".rst", ".text"})

#: Extensions that are textual at the byte level but not what users mean
#: by "plain text for NER" — either structured data already handled by
#: dedicated handlers, source code, or config formats. Listing them here
#: short-circuits both the ``mimetypes`` and content-sniff paths so we
#: don't accidentally claim e.g. a ``.py`` file (which ``mimetypes`` does
#: label ``text/x-python``).
_EXCLUDE_EXTENSIONS = frozenset(
    {
        # Structured data — own handlers (vector, raster) or handle_csv
        ".csv",
        ".tsv",
        ".json",
        ".geojson",
        ".xml",
        ".html",
        ".htm",
        # Source code — text bytes but irrelevant for geographic NER
        ".py",
        ".pyi",
        ".pyc",
        ".js",
        ".mjs",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".kt",
        ".scala",
        ".c",
        ".cc",
        ".cpp",
        ".cxx",
        ".h",
        ".hpp",
        ".hxx",
        ".m",
        ".swift",
        ".rs",
        ".go",
        ".rb",
        ".pl",
        ".php",
        ".lua",
        ".r",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
        # Serialisation / config
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".properties",
        ".env",
        ".lock",
        # Binary media — extensionless content sniff would correctly reject
        # most of these, but a fast-path avoids the I/O for full directory
        # traversals over user photo libraries etc.
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".bmp",
        ".ico",
        ".tif",
        ".tiff",  # raster handler claims these
        ".mp3",
        ".mp4",
        ".wav",
        ".flac",
        ".ogg",
        ".avi",
        ".mkv",
        ".mov",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".7z",
        ".xz",
        ".rar",
        ".pdf",
        ".doc",
        ".docx",
        ".ppt",
        ".pptx",
        ".xls",
        ".xlsx",
        ".odt",
    }
)

#: Common extensionless filenames that ship with most software projects
#: and should be treated as plain text without a content sniff. Names are
#: matched case-insensitively. The actual basename may have a suffix
#: like ``LICENSE.txt`` — that case is already handled by the ``.txt``
#: fast-path so we only need the bare names here.
_TEXT_BASENAMES = frozenset(
    {
        "README",
        "LICENSE",
        "LICENCE",
        "COPYING",
        "COPYRIGHT",
        "AUTHORS",
        "CONTRIBUTORS",
        "MAINTAINERS",
        "CHANGELOG",
        "CHANGES",
        "HISTORY",
        "NEWS",
        "INSTALL",
        "NOTES",
        "TODO",
        "MANIFEST",
    }
)


def is_text_file(filepath: str) -> bool:
    """Return True if *filepath* should be treated as a plain-text file.

    Decision order:

    1. ``_EXCLUDE_EXTENSIONS`` → False (cheap reject for code, configs,
       binary media, and structured-data extensions handled by other
       geoextent modules).
    2. ``TEXT_EXTENSIONS`` → True (the curated explicit yes list).
    3. ``_TEXT_BASENAMES`` (e.g. ``README``, ``LICENSE``) → True.
    4. ``mimetypes.guess_type`` returning ``text/*`` → True (confirming-
       only hint; we never trust ``mimetypes`` for a "no" answer because
       its table is sparse and platform-dependent).
    5. Content sniff on the first 8 KB → True iff the file looks like
       UTF-8 / UTF-16 / mostly-printable single-byte encoded text.
    """
    base = os.path.basename(filepath)
    ext = os.path.splitext(base)[1].lower()

    if ext in _EXCLUDE_EXTENSIONS:
        return False
    if ext in TEXT_EXTENSIONS:
        return True
    if not ext and base.upper() in _TEXT_BASENAMES:
        return True

    mime, _ = mimetypes.guess_type(filepath)
    if mime is not None and mime.startswith("text/"):
        # Trust mimetypes only for the text/* → True direction.
        # ``text/x-python`` etc. are already filtered above by the
        # _EXCLUDE_EXTENSIONS fast-path, so anything reaching here is a
        # legitimate text/* hit (e.g. ``text/x-tex`` for ``.tex``,
        # ``text/x-bibtex`` for ``.bib``, ``text/calendar`` for ``.ics``).
        return True

    return _sniff_text_content(filepath)


# Bytes always considered "text-friendly" when judging a file by its raw
# bytes — printable ASCII + common whitespace, plus the upper-half range
# (latin-1 / cp1252 supersets).
_TEXT_BYTES = (
    set(range(0x20, 0x7F))  # printable ASCII
    | {0x09, 0x0A, 0x0D, 0x0C, 0x08}  # \t \n \r \f \b
    | set(range(0xA0, 0x100))  # latin-1 high range
)


def _sniff_text_content(filepath: str, sample_size: int = 8192) -> bool:
    """Read at most *sample_size* bytes and decide whether the content
    looks like plain text. NULL bytes are a strong binary signal; UTF-8
    decodability is a strong text signal; otherwise fall back to a
    printable-byte ratio over the latin-1 range.

    Returns False on any I/O error — callers treat the file as non-text
    rather than crashing the whole directory walk.
    """
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(sample_size)
    except OSError as e:
        logger.debug("Could not sniff %s for text content: %s", filepath, e)
        return False

    if not chunk:
        # Empty file — no NER hits to extract anyway, but it's textual
        # rather than binary. Keep True so empty-file handling stays
        # consistent across handler modules.
        return True

    # UTF-16 BOM → has interleaved NULLs by design; check before the
    # NULL-byte heuristic below.
    if chunk[:2] in (b"\xff\xfe", b"\xfe\xff"):
        try:
            chunk.decode("utf-16")
            return True
        except UnicodeDecodeError:
            return False

    # NULL bytes in the first 8 KB ⇒ very likely binary.
    if b"\x00" in chunk:
        return False

    # UTF-8 (which subsumes ASCII) is the dominant text encoding today.
    # Trim a possible trailing partial multibyte sequence before decoding
    # so we don't false-negative on a file that happens to have a
    # multibyte character straddling the 8 KB boundary.
    trimmed = _trim_trailing_partial_utf8(chunk)
    try:
        trimmed.decode("utf-8")
        return True
    except UnicodeDecodeError:
        pass

    # Last resort — count "text-friendly" bytes; >85% ⇒ text. Catches
    # cp1252 / latin-1 plaintext while rejecting most binary noise.
    ratio = sum(1 for b in chunk if b in _TEXT_BYTES) / len(chunk)
    return ratio > 0.85


def _trim_trailing_partial_utf8(chunk: bytes) -> bytes:
    """Drop a trailing partial UTF-8 multibyte sequence so a decode
    attempt of the sample doesn't fail solely because the 8 KB cut went
    through a character. Looks back at most 3 bytes — UTF-8 sequences
    are at most 4 bytes long."""
    for i in range(1, min(4, len(chunk)) + 1):
        b = chunk[-i]
        if b < 0x80:
            return chunk  # ASCII boundary — nothing to trim
        if 0xC0 <= b <= 0xFD:
            # Leading byte of a multibyte sequence at position -i.
            # Expected sequence length:
            if b >= 0xF0:
                expected = 4
            elif b >= 0xE0:
                expected = 3
            else:
                expected = 2
            if i < expected:
                return chunk[:-i]
            return chunk
        # 0x80-0xBF: continuation byte; keep walking back.
    return chunk
