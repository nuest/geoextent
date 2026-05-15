"""Tests for ``geoextent.lib.text_extraction.mime.is_text_file``.

The handler-dispatch loop in ``extent.from_file`` calls
``handle_text.check_file_supported`` first; that delegates to
``is_text_file``. Real-world inputs include extensionless files
(``README``, ``LICENSE``), files with unrecognised extensions
(``.log``, ``.adoc``, ``.org``), and source code mislabelled as text by
stdlib ``mimetypes`` (``text/x-python`` for ``.py`` etc.). These tests
codify the contract the consolidated mime/sniff implementation is
expected to satisfy.
"""

import os

import pytest

from geoextent.lib.text_extraction.mime import (
    TEXT_EXTENSIONS,
    is_text_file,
    _sniff_text_content,
)


def _write(tmp_path, name, content_bytes):
    path = tmp_path / name
    path.write_bytes(content_bytes)
    return str(path)


# --- Fast-path: explicit extension lists --------------------------------------


@pytest.mark.parametrize("ext", sorted(TEXT_EXTENSIONS))
def test_known_text_extensions_are_claimed(tmp_path, ext):
    path = _write(tmp_path, f"file{ext}", b"plain text")
    assert is_text_file(path) is True


@pytest.mark.parametrize(
    "ext",
    [".csv", ".tsv", ".json", ".geojson", ".xml", ".html", ".htm"],
)
def test_structured_data_extensions_not_text(tmp_path, ext):
    """Structured data goes to its own handler — handle_text must never
    claim it, even if the bytes happen to be valid ASCII text."""
    path = _write(tmp_path, f"file{ext}", b"col1,col2\n1,2")
    assert is_text_file(path) is False


@pytest.mark.parametrize("ext", [".py", ".js", ".ts", ".sh", ".rb", ".go", ".rs"])
def test_source_code_not_treated_as_text(tmp_path, ext):
    """stdlib ``mimetypes`` labels these ``text/*``, but running NER on
    source code is almost never what the user wants. ``_EXCLUDE_EXTENSIONS``
    short-circuits before the mimetypes path."""
    path = _write(tmp_path, f"script{ext}", b"def f():\n    return 'Berlin'")
    assert is_text_file(path) is False


@pytest.mark.parametrize("ext", [".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"])
def test_config_files_not_treated_as_text(tmp_path, ext):
    path = _write(tmp_path, f"config{ext}", b"key: value\n")
    assert is_text_file(path) is False


@pytest.mark.parametrize(
    "ext", [".jpg", ".png", ".pdf", ".zip", ".docx", ".mp3", ".tif"]
)
def test_binary_media_extensions_not_text(tmp_path, ext):
    """Cheap reject so a directory walk doesn't even open these."""
    path = _write(tmp_path, f"media{ext}", b"")
    assert is_text_file(path) is False


# --- Extensionless filenames --------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "README",
        "LICENSE",
        "LICENCE",
        "COPYING",
        "AUTHORS",
        "CHANGELOG",
        "NEWS",
        "INSTALL",
        "NOTES",
        "TODO",
    ],
)
def test_extensionless_project_filenames_are_text(tmp_path, name):
    """README, LICENSE, CHANGELOG, etc. should be NER candidates without
    requiring the user to know they need a ``.txt`` rename."""
    path = _write(tmp_path, name, b"# Some plain text content.\n")
    assert is_text_file(path) is True


def test_extensionless_filenames_case_insensitive(tmp_path):
    """``readme`` vs ``README`` vs ``Readme`` — accept all casings."""
    for name in ("README", "readme", "Readme", "ReadMe"):
        path = _write(tmp_path, name, b"hi")
        assert is_text_file(path) is True, name


# --- Content sniffing ---------------------------------------------------------


def test_unknown_extension_with_text_content_is_claimed(tmp_path):
    """``.dat`` is not in either list; content sniff says it's UTF-8
    text — claim it."""
    path = _write(tmp_path, "strange.dat", b"Sediment cores in Munich, 2024.")
    assert is_text_file(path) is True


def test_unknown_extension_with_binary_content_rejected(tmp_path):
    """``.dat`` not in either list; content has NULL bytes ⇒ binary."""
    path = _write(tmp_path, "blob.dat", b"\x00\x01\x02\xff\xfe\x00data")
    assert is_text_file(path) is False


def test_no_extension_text_content_sniffed_as_text(tmp_path):
    """An unfamiliar extensionless filename still passes via sniff if
    the bytes look like text."""
    path = _write(tmp_path, "field_notes", b"Survey in Berlin and Reykjavik.")
    assert is_text_file(path) is True


def test_no_extension_binary_content_rejected(tmp_path):
    """A PNG without an extension — sniff must say binary."""
    path = _write(tmp_path, "blob", b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0d")
    assert is_text_file(path) is False


def test_utf8_multibyte_text_sniffs_as_text(tmp_path):
    """Non-ASCII UTF-8 text (München) must decode cleanly."""
    path = _write(tmp_path, "field", "Sediment cores in München".encode("utf-8"))
    assert is_text_file(path) is True


def test_utf16_with_bom_sniffs_as_text(tmp_path):
    """UTF-16 has interleaved NULLs — the BOM check must rescue it
    before the NULL-byte heuristic kicks in."""
    path = _write(tmp_path, "win", "Workshops in Köln".encode("utf-16"))
    assert is_text_file(path) is True


def test_latin1_text_sniffs_as_text(tmp_path):
    """cp1252/latin-1 plaintext: not valid UTF-8 but >85% printable
    bytes ⇒ text."""
    path = _write(tmp_path, "old", "Cores in Münster".encode("latin-1"))
    assert is_text_file(path) is True


def test_partial_utf8_at_sample_boundary(tmp_path):
    """UTF-8 multibyte sequence straddling the 8 KB sample cutoff should
    not produce a false negative. Build a payload ending in the first
    byte of ``é`` (0xC3) at position 8191."""
    chunk = (b"a" * 8191) + b"\xc3\xa9 trailing"
    path = _write(tmp_path, "boundary", chunk)
    assert is_text_file(path) is True


def test_empty_file_is_text(tmp_path):
    """Empty file ⇒ no NER hits anyway, but classify as text so handler
    dispatch stays consistent."""
    path = _write(tmp_path, "empty", b"")
    assert is_text_file(path) is True


def test_missing_file_returns_false(tmp_path):
    """Don't crash on missing files; just decline."""
    assert is_text_file(str(tmp_path / "does_not_exist")) is False


# --- Direct sniff helper ------------------------------------------------------


def test_sniff_short_circuit_on_null_byte(tmp_path):
    path = _write(tmp_path, "x", b"hello\x00world" + b"a" * 8000)
    assert _sniff_text_content(path) is False
