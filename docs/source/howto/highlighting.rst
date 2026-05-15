============================================
Highlighting matches from the text/NER source
============================================

When geoextent extracts an extent from free text (``--text-method ner`` /
:func:`geoextent.lib.extent.from_text`, see :issue:`112`), it returns enough
information for another tool — or a human reading the JSON — to point at
the exact words that produced each result. This page is the reference for
that contract.

Three surfaces are available today:

* **Standoff offsets** (always on): every place, date, and named-period
  mention carries ``char_start`` and ``char_end`` indices into the source
  string the extractor used. This is the machine-to-machine surface, and
  it matches the convention used by spaCy, Hugging Face NER pipelines,
  and the W3C Web Annotation Data Model.
* **Source-text echo** (on by default; disable with ``--no-source-text``):
  the result includes the NFC-normalised source under ``source_text``,
  plus the ``source_offset_unit`` and ``source_normalisation`` fields
  describing the offset contract.
* **``--annotate``** (CLI, opt-in human display): prints the source with
  matches highlighted in ANSI colour, or wrapped in
  ``[[Berlin|place]]``-style brackets for non-terminal contexts.

Two further surfaces are tracked as follow-ups: HTML/Markdown rendering
for notebooks and web UIs, and Web Annotation Data Model export (see the
follow-up issue at :issue:`114`).

The standoff contract
=====================

For every entry in ``place_names`` and ``date_entities`` you get:

.. code-block:: jsonc

   {
     "name": "Berlin",           // place_names; date_entities use "text"
     "char_start": 18,
     "char_end":   24,
     "matched":    true,
     "gazetteer_id":  "geonames:2950159",
     "gazetteer_url": "https://www.geonames.org/2950159"
   }

The slice ``source_text[char_start:char_end]`` is guaranteed to equal
``name`` / ``text``.

Offset unit
-----------

``source_offset_unit`` is always ``"python_codepoint"``: indices count
Unicode code points (Python ``len(str)`` semantics, post-PEP 393). This
matters when consuming the result from JavaScript or Java, which count
UTF-16 code units. A safe round-trip from Python offsets to UTF-16 offsets:

.. code-block:: python

   def to_utf16_offsets(text, start, end):
       prefix = text[:start].encode("utf-16-le")
       slice_ = text[start:end].encode("utf-16-le")
       return len(prefix) // 2, (len(prefix) + len(slice_)) // 2

Or, in JavaScript, use the source text returned by geoextent directly —
``[...text]`` iterates code points and lets you reproduce the slice.

Normalisation
-------------

``source_normalisation`` is always ``"nfc"``. The extractor normalises
the input to NFC before tokenising; ``source_text`` reflects that. If
the caller passed an NFD string (e.g. ``"München"``), the echoed
``source_text`` is the NFC form (``"München"``) and the offsets index
into *that* form, not the original.

This eliminates the family of bugs where ``é`` (1 code point) and
``é`` (``e`` + ``́``, 2 code points) produce different offsets for
the same visual character.

Byte-order marks
----------------

A leading ``﻿`` (BOM) is stripped before offsets are computed —
both for file inputs (already handled by the text reader) and for
``--text``/stdin inputs.

Consuming the offsets in Python
===============================

The simplest possible consumer that prints matched spans with their
gazetteer URL:

.. code-block:: python

   from geoextent.lib import extent

   result = extent.from_text(
       "Sediment cores in Berlin span the Holocene; resurvey on 2024-05-12.",
       bbox=True, tbox=True, text_method="ner",
       ner_gazetteer="nominatim",
       ner_ambiguity="top",
   )

   src = result["source_text"]
   for rec in result["place_names"]:
       surface = src[rec["char_start"]:rec["char_end"]]
       print(f"place  {surface!r:20s} → {rec.get('gazetteer_url')}")
   for rec in result["date_entities"]:
       surface = src[rec["char_start"]:rec["char_end"]]
       kind = rec["kind"]
       resolved = (rec.get("start"), rec.get("end"))
       print(f"{kind:6s} {surface!r:20s} → {resolved}")

Sample output::

   place  'Berlin'             → https://www.openstreetmap.org/relation/62422
   period 'Holocene'           → ('-9750-01-01', '1950-01-01')
   date   '2024-05-12'         → ('2024-05-12', '2024-05-12')

Opting out of the source-text echo
==================================

The echoed ``source_text`` can be sizable (for long inputs) or sensitive
(for inputs containing private text). Suppress it with the
``--no-source-text`` CLI flag or ``include_source_text=False`` API
parameter:

.. code-block:: bash

   geoextent -b -t --quiet --text-method ner --no-source-text \
       --text "Berlin in 1990"

The offsets are still emitted; they just point into the source the caller
keeps locally. ``--annotate`` cannot render when ``source_text`` is
absent, so combine ``--no-source-text`` with ``--annotate off``.

The ``--annotate`` flag
=======================

``--annotate {auto,ansi,brackets,off}`` adds a human-readable rendering
of the source after the JSON result. Default: ``auto`` (``ansi`` when
stdout is a TTY, ``brackets`` otherwise).

ANSI (terminal)
---------------

.. code-block:: bash

   geoextent -b -t --quiet --text-method ner --ner-ambiguity top \
       --annotate ansi \
       --text "Sediment cores in Berlin span the Holocene; resurvey on 2024-05-12."

The annotated line follows the JSON and a header:

.. code-block::

   {... JSON ...}
   ---annotated source (ansi)---
   Sediment cores in [cyan]Berlin[/] span the [magenta]Holocene[/]; resurvey on [yellow]2024-05-12[/].

Default colour assignment: places cyan, dates yellow, periods magenta.
Override with ``--annotate-classes``:

.. code-block:: bash

   geoextent ... --annotate ansi \
       --annotate-classes "place=bright_red,date=green,period=blue"

Recognised colour names: ``black``, ``red``, ``green``, ``yellow``,
``blue``, ``magenta``, ``cyan``, ``white``, each available as a
``bright_*`` variant.

Brackets (pipelines, log capture, non-TTY contexts)
---------------------------------------------------

.. code-block:: bash

   geoextent -b -t --quiet --text-method ner --ner-ambiguity top \
       --annotate brackets \
       --text "Sediment cores in Berlin span the Holocene; resurvey on 2024-05-12." \
     | tee report.txt

::

   ---annotated source (brackets)---
   Sediment cores in [[Berlin|place]] span the [[Holocene|period]]; resurvey on [[2024-05-12|date]].

The markers are designed to survive piping, log aggregation, and
copy/paste into chat clients. They never collide with HTML or Markdown
formatting because they are not interpreted as either.

Library API
-----------

The renderer is available as :func:`geoextent.lib.annotate.render_annotated_text`
for use in notebooks, services, or custom tooling:

.. code-block:: python

   from geoextent.lib import extent
   from geoextent.lib.annotate import render_annotated_text, parse_classes

   result = extent.from_text("Berlin in 1990.", bbox=True, tbox=True,
                             text_method="ner", ner_ambiguity="top")
   print(render_annotated_text(result, mode="brackets"))
   # → Berlin in [[1990|date]].   (well, Berlin too if the gazetteer resolves)

   # Custom classes
   classes = parse_classes("place=red,date=green,period=blue")
   print(render_annotated_text(result, mode="ansi", classes=classes))

Overlap handling
----------------

Most inputs do not produce overlapping spans because the period
``PhraseMatcher`` already wins over conflicting place spans before
provenance is emitted (see :mod:`geoextent.lib.text_extraction.ner`).
When overlaps do appear in custom result dicts, the renderer falls back
to **greedy longest-wins**: the longer match is kept, shorter overlapping
spans are dropped (and logged at debug level). This is the same rule
used by :mod:`geoextent.lib.text_extraction.periods.extract_periods`.

Multi-input runs
================

When more than one positional input is given (or a directory contains
several text files), the CLI prints one annotated block per source, each
prefixed by the input label::

   ---annotated source (brackets) — <text>---
   ...
   ---annotated source (brackets) — tests/testdata/text/cities.txt---
   ...

Roadmap
=======

Coming in a follow-up (:issue:`114`):

* ``--annotate html`` and a library helper that wraps matches in
  ``<mark class="geoextent-place" data-id="…">…</mark>`` elements, plus
  ``geoextent.display(result)`` for one-line Jupyter integration.
* A ``--format webannotations`` export emitting JSON-LD compatible with
  the W3C Web Annotation Data Model, BRAT, INCEPTION, and Hypothes.is.
