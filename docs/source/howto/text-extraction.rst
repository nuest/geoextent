==========================================
Extracting extents from free text
==========================================

geoextent can pull spatial and temporal extents out of unstructured English
prose using `spaCy <https://spacy.io/>`_ named entity recognition together
with a place-name gazetteer and a bundled time-period gazetteer (ICS
GTS2020). This page is a tour of the feature: setup, place names, calendar
dates, named time periods, the signed ISO 8601 output format, match
highlighting, ambiguity policy, and how to turn the source off.

For the offset contract that underpins highlighting and tool integration,
see :doc:`highlighting`. Issue :issue:`112` tracks the feature; follow-ups
:issue:`113` (Wikidata period gazetteer) and :issue:`114` (HTML and Web
Annotation export) are open.

One-time setup
==============

Install the optional ``[nlp]`` extra and a spaCy English model:

.. code-block:: bash

   pip install 'geoextent[nlp]'
   python -m spacy download en_core_web_sm

The default forward-gazetteer is **Nominatim** (no API key required); the
default model is ``en_core_web_sm`` (auto-downloaded on first use unless
``--no-auto-download`` is passed). Without the ``[nlp]`` extra the text
handler silently declines, so a directory containing ``README.md`` is not
suddenly NER-ed just because you upgraded geoextent.

Place names from text
=====================

The defaults make place-name extraction work out of the box:

.. code-block:: bash

   geoextent -b --text "Field campaigns in Berlin and Paris"

That prints a GeoJSON ``FeatureCollection`` with each resolved place under
``place_names``. Note that by default geoextent **drops** ambiguous mentions
— "Paris" has many homonyms (Paris/France, Paris/Texas, Paris/Ontario, …),
so Nominatim returns several candidates and the safe default refuses to
guess. To keep the top-ranked match:

.. code-block:: bash

   geoextent -b --ner-ambiguity top \
       --text "Field campaigns in Berlin and Paris"

Other input modes:

.. code-block:: bash

   # Stdin
   echo "Workshops in Tokyo and London" | geoextent -b -

   # A single text file
   geoextent -b tests/testdata/text/cities.txt

   # A whole directory of text files
   geoextent -b tests/testdata/text/

   # Mixed text + geospatial in one call
   geoextent -b \
       tests/testdata/text/mixed_dir/cities.txt \
       tests/testdata/text/mixed_dir/point.geojson

   # Different gazetteer (Nominatim is already the default; GeoNames needs
   # the GEONAMES_USERNAME env var or a .env file)
   geoextent -b --ner-gazetteer photon \
       --text "Saxony, Bavaria, and Brandenburg"

Boundary geometries
-------------------

Some gazetteers can return more than a centroid for areal features. By
default, geoextent uses an administrative boundary or other areal polygon
when one is available, and falls back to the centroid point otherwise. The
classic case is a state name like *Saxony*:

.. code-block:: bash

   geoextent -b --ner-ambiguity top --text "Field campaign in Saxony"

With Nominatim (the default gazetteer), Saxony resolves to OSM relation
``62467`` and the gazetteer returns the state's ``MultiPolygon``. The
emitted ``bbox`` is the polygon's envelope (roughly
``[11.87, 50.17, 15.04, 51.69]``) and the place provenance carries the
geometry under ``boundary``:

.. code-block:: jsonc

   "place_names": [{
     "name": "Saxony",
     "gazetteer_id": "osm:relation:62467",
     "gazetteer_url": "https://www.openstreetmap.org/relation/62467",
     "lat": 50.93, "lon": 13.46,         // centroid, still emitted
     "boundary": {"type": "MultiPolygon", "coordinates": [...]}
   }]

Force a centroid (e.g. for sensors that expect single-point geometry) with
``--place-geometry point``:

.. code-block:: bash

   geoextent -b --place-geometry point \
       --ner-ambiguity top --text "Field campaign in Saxony"
   # → bbox is the centroid (degenerate point envelope)

``--place-geometry auto`` (default) uses the boundary when present and
silently falls back to the point when absent. ``boundary`` is the same as
``auto`` today; a future release may make it stricter (warn / error on
fallback). **GeoNames and Photon return only centroid points** for the
geopy interface geoextent uses, so this knob has no effect with those
backends — the spatial extent will always be the point envelope.

Convex hull on mixed geometries
-------------------------------

With ``--convex-hull`` the spatial extent is the convex hull of all
matched gazetteer hits — polygon hits contribute their boundary vertices,
point hits contribute their centroid, and the union is hulled together.
This makes ``--convex-hull`` useful for three distinct shapes of input:

**Single polygon hit — polygon simplification.** If only one place is
matched and it has a boundary, the result is the convex hull of that
polygon's vertices. For an already-convex shape the result equals the
boundary; for an irregular shape it acts as a simplification:

.. code-block:: bash

   geoextent -b --convex-hull --ner-ambiguity top --text "Field campaign in Saxony"
   # → "bbox" is a closed polygon ring covering the Saxony outline

**Polygon + outside point — extended hull.** A polygon plus a far-away
point extends the hull to enclose both. The hull of "Saxony" (covering
~11.9–15.0°E, 50.2–51.7°N) and "Berlin" (~13.4°E, 52.5°N) reaches north
beyond Saxony to include Berlin:

.. code-block:: bash

   geoextent -b --convex-hull --ner-ambiguity top \
       --text "Field campaigns in Saxony and Berlin"
   # → "bbox" is a closed polygon ring whose northern boundary touches Berlin

**Multiple point hits.** Two or three point hits (cities) produce a line
segment or polygon hull — the same behaviour as before:

.. code-block:: bash

   geoextent -b --convex-hull --ner-ambiguity top \
       --text "Field campaigns in Berlin, Paris, and Tokyo"

``--place-geometry point`` forces the hull to be computed from centroids
even when polygons are available, which can be useful if you want a
city-to-city skeleton and not a country-wide hull.

Viewing the extent on geojson.io and the 150 KB payload limit
-------------------------------------------------------------

``--geojsonio`` produces a clickable URL that opens the extracted extent
on https://geojson.io. The URL embeds the GeoJSON directly in its
``#data=…`` fragment, so the only practical limit is how much GeoJSON
fits in a URL:

.. code-block:: bash

   geoextent -b --convex-hull --geojsonio \
       --ner-ambiguity top --text "Field campaigns in Berlin and Reykjavik"
   # → http://geojson.io/#data=data:application/json,%7B%22type%22%…

**The 150 KB threshold.** geojson.io itself does not document a maximum
payload size — see the upstream `URL API reference <https://github.com/mapbox/geojson.io/blob/main/API.md>`__.
The limit comes from the `geojsonio Python wrapper <https://github.com/jwass/geojsonio.py>`__
that geoextent uses to build the URL: it defines
``MAX_URL_LEN = 150e3`` (150 000 bytes of GeoJSON content) and, for
anything larger, falls back to *uploading the GeoJSON as an anonymous
GitHub Gist* and embedding the gist ID in the URL instead.

**Why the fallback fails today.** GitHub no longer permits anonymous
gist creation (the API returns ``401 Requires authentication``), so the
fallback always fails for oversize payloads. geoextent surfaces this as:

.. code-block:: text

   geojson.io URL could not be generated — geojson.io service call
   failed: geojsonio.make_url → GitHub Gist API (anonymous gist
   fallback for GeoJSON > ~150 KB): 401 Requires authentication
   (payload size 331222 bytes) — try --convex-hull to reduce geometry
   complexity, or drop optional fields that bloat properties

**What pushes a text-NER extent over 150 KB.** The geometry itself is
usually small (a convex hull or a 4-corner envelope is a few hundred
bytes). The bloat comes from the ``place_names[*].boundary`` polygons
that Nominatim returns for administrative areas — a single ``Berlin``
or ``Saxony`` boundary is 50–200 KB of coordinates. ``--convex-hull``
already strips boundaries from the provenance once it has consumed them
for the hull, so the common fix is:

.. code-block:: bash

   # Was 324 KB → 401 from the gist fallback
   geoextent -b --geojsonio --placename --text "Workshops in Berlin"

   # 2.5 KB → URL-fragment path, no gist, works
   geoextent -b --convex-hull --geojsonio --placename \
       --text "Workshops in Berlin"

Other ways to shrink the payload below 150 KB:

* ``--place-geometry point`` also drops boundaries from provenance.
* Cap the number of mentions (``--ner-ambiguity drop`` skips ambiguous
  ones; you can also write tighter input text).
* Use ``--ner-gazetteer photon`` or ``--ner-gazetteer geonames`` —
  neither returns admin polygons, so the provenance stays small.
* Save the GeoJSON to a file (``geoextent -b > extent.geojson``) and
  upload via the geojson.io GUI's "Open → File" instead.

If you need to render a > 150 KB extent and don't want to depend on
external services, ``--map FILE`` writes a local PNG preview without
involving geojson.io at all.

Combining a text input with a local geospatial file
---------------------------------------------------

The CLI accepts ``--text`` together with positional file or directory
inputs in a single call. ``--text`` (and ``-`` stdin) is treated as one
more source, peer to the positional inputs, and **all sources are
merged into a single envelope / convex hull by default** — the same
behaviour you get from multiple positional files. Use ``--details`` to
inspect each source separately; the merged top-level extent is kept
either way:

.. code-block:: bash

   # Mix a free-text mention with a GeoJSON file. The bbox spans Berlin
   # (from --text) and Tokyo (from the file).
   geoextent -b --ner-ambiguity top \
       --text "Field campaigns in Berlin" \
       tests/testdata/text/mixed_dir/point.geojson

   # Convex hull across text + file, with temporal extent merged too.
   # Denmark + Belgium (from --text), Berlin + Reykjavik (from cities.txt);
   # tbox spans 2021–2023.
   geoextent -b -t --convex-hull \
       --text "Travelling from Denmark to Belgium in 2021 and 2023" \
       tests/testdata/text/mixed_dir/cities.txt

   # Same as above, with --geojsonio appended to also print a clickable
   # geojson.io URL covering the four-country hull. Stays well under the
   # 150 KB URL-fragment limit because --convex-hull strips per-place
   # boundary polygons from the provenance.
   geoextent -b -t --convex-hull \
       --text "Travelling from Denmark to Belgium in 2021 and 2023" \
       --geojsonio \
       tests/testdata/text/mixed_dir/cities.txt

   # Add --details to inspect the per-source extents under
   # geoextent_extraction.details.
   geoextent -b --details --ner-ambiguity top \
       --text "Field campaigns in Berlin" \
       tests/testdata/text/mixed_dir/point.geojson

The same shape works for any positional input: a Shapefile, a GeoTIFF, a
directory of geospatial files, a DOI / repository URL, or stdin (``-``).
Mixed runs through the Python API use the multi-input call:

.. code-block:: python

   from geoextent.lib import extent

   # 1) Inline text alone
   text_result = extent.from_text(
       "Field campaigns in Berlin",
       bbox=True, ner_ambiguity="top",
   )

   # 2) A local file alone
   file_result = extent.from_file("path/to/point.geojson", bbox=True)

   # 3) Merge in the application layer if you need a combined envelope.
   from geoextent.lib import helpfunctions as hf
   merged = hf.bbox_merge(
       {"text": text_result, "file": file_result},
       "multi-input",
   )
   print(merged["bbox"])

Tuning what spaCy picks up:

.. code-block:: bash

   # Only keep GPE (geo-political entities) — countries, cities, regions
   geoextent -b --ner-labels GPE \
       --text "Hiking in the Alps near Munich and along the Rhine"

   # Use a larger model (must be installed separately):
   #   python -m spacy download en_core_web_md
   geoextent -b --ner-model en_core_web_md \
       --text "Berlin and Paris"

Calendar dates from text
========================

The temporal pipeline understands four shapes of date expressions:

.. code-block:: bash

   geoextent -t --text "Field measurements in May 2024"
   # → "tbox": ["2024-05-01", "2024-05-31"]   (month envelope)

   geoextent -t --text "Records from the 1990s"
   # → "tbox": ["1990-01-01", "1999-12-31"]   (decade envelope)

   geoextent -t --text "Records from the 19th century"
   # → "tbox": ["1801-01-01", "1900-12-31"]   (century envelope)

   geoextent -t --text "Monitoring ran between 2010 and 2015"
   # → "tbox": ["2010-01-01", "2015-12-31"]   (range splitter)

Range detection handles ``between X and Y``, ``from X to Y``, en-dashes
(``X–Y``), em-dashes (``X—Y``), plain ASCII hyphens (``X-Y``), and
``to``/``until``/``through``/``and`` connectors.

Two phrasings, two provenance paths, same envelope
--------------------------------------------------

A useful comparison — the same time window expressed two ways yields
identical ``tbox`` envelopes but very different mention provenance:

.. code-block:: bash

   geoextent -t \
     --text "Field campaigns in Berlin and Paris ending in March 2022 and beginning in June 2021"

Result (extract):

.. code-block:: jsonc

   "tbox": ["2021-06-01", "2022-03-31"],
   "date_entities": [
     {"text": "March 2022", "kind": "date",
      "start": "2022-03-01", "end": "2022-03-31"},
     {"text": "June 2021",  "kind": "date",
      "start": "2021-06-01", "end": "2021-06-30"}
   ]

spaCy emits **two** independent ``DATE`` entities; each is parsed
independently (each into a month envelope), and ``tbox`` is the envelope of
the envelopes.

Now the same window in a single phrase:

.. code-block:: bash

   geoextent -t \
     --text "Field campaigns in Berlin and Paris from June 2021 to March 2022"

Result (extract):

.. code-block:: jsonc

   "tbox": ["2021-06-01", "2022-03-31"],
   "date_entities": [
     {"text": "June 2021 to March 2022", "kind": "date",
      "start": "2021-06-01", "end": "2022-03-31"}
   ]

spaCy emits **one** ``DATE`` span spanning both endpoints; geoextent's
range splitter recognises the ``to`` connector, parses each side, and
returns the merged envelope as a single mention.

Both phrasings produce the same ``tbox`` because the envelope-of-envelopes
and the explicit-range computations converge. The difference shows up in
``date_entities``: the first phrasing carries two mentions, the second
carries one. For downstream tools that highlight matches in the source,
this distinction matters — the second phrasing yields a single span to
underline (``"June 2021 to March 2022"``); the first yields two
non-contiguous spans.

Named time periods
==================

Beyond calendar dates, geoextent recognises geological time periods using
the bundled International Chronostratigraphic Chart (ICS GTS2020, CC0,
~178 eons / eras / periods / epochs / ages). Period detection runs as a
spaCy ``PhraseMatcher`` over the gazetteer's label index — which means it
catches mentions that ``en_core_web_sm`` mislabels (Holocene as ``ORG``,
Mesozoic Era as ``ORG``, Bronze Age as ``PERSON``) or misses entirely
(Pleistocene, Late Cretaceous):

.. code-block:: bash

   geoextent -t --text "Sediment cores from the Holocene"
   # → "tbox": ["-9750-01-01", "1950-01-01"]

   geoextent -t --text "Late Cretaceous fossils dominate the section"
   # → "tbox": ["-100498050-01-01", "-65998050-01-01"]

   geoextent -t --text "Pleistocene cores below the modern surface"
   # → "tbox": ["-2578050-01-01", "-9750-01-01"]

Resolved periods carry the same provenance shape as places — a
``gazetteer_id`` (``ics:Holocene``) and ``gazetteer_url`` pointing to the
canonical resource on ``resource.geosciml.org``. Disable period matching
with ``--no-period-resolution`` if you only want calendar-date parsing.

Combining periods and dates
---------------------------

.. code-block:: bash

   geoextent -t \
     --text "Pleistocene cores near Berlin re-surveyed on 2024-05-12"
   # → "tbox": ["-2578050-01-01", "2024-05-12"]

The deep-time start and the CE-date end coexist in the same envelope; the
``tbox`` merge falls back to numeric signed-year comparison when any
mention is pre-CE.

Signed ISO 8601 dates for pre-CE / deep time
============================================

Python's stdlib ``datetime`` cannot represent year 0 or negative years, so
geological periods are emitted as **signed ISO 8601 extended year**
strings:

* Holocene start: ``-9750-01-01``
* Pleistocene start: ``-2578050-01-01``
* Mesozoic Era start: ``-251900050-01-01``

The sign and the at-least-four-digit year width are fixed; larger years
extend the width as needed. ``--time-format`` is **not** applied to
deep-time mentions (those rely on the signed-ISO contract); CE-only output
continues to honour the format flag exactly as before, byte-for-byte.

Highlighting matches
====================

The CLI can render the source string with matched spans wrapped for
display:

.. code-block:: bash

   geoextent -b -t --annotate brackets \
     --text "Sediment cores in Berlin span the Holocene; resurvey on 2024-05-12"

Output (after the JSON):

.. code-block::

   ---annotated source (brackets)---
   Sediment cores in [[Berlin|place]] span the [[Holocene|period]]; resurvey on [[2024-05-12|date]]

Modes:

* ``--annotate auto`` (default) — ANSI colour when stdout is a TTY,
  brackets otherwise, mirroring ``grep --color=auto``.
* ``--annotate ansi`` — force ANSI SGR colours (terminal preview).
* ``--annotate brackets`` — force ``[[surface|kind]]`` markers (pipelines,
  log capture, chat clients).
* ``--annotate off`` — suppress.
* ``--annotate-classes "place=cyan,date=yellow,period=magenta"`` —
  override colours per kind.

Each mention also carries ``char_start`` / ``char_end`` offsets into the
echoed ``source_text`` so consumers can render their own highlights. See
:doc:`highlighting` for the contract details and a JavaScript / Java
re-encoding recipe.

Ambiguity policy
================

Both gazetteers (place-name and time-period) have an ``--ner-ambiguity``
/ ``--period-ambiguity`` knob with the same two values:

* ``drop`` (default) — refuse to choose when more than one candidate is
  returned. Defensive: a "Paris" mention without disambiguating context
  is dropped rather than silently bound to the wrong city. The first
  time a name is dropped, geoextent logs a WARNING to ``stderr`` naming
  the place, the gazetteer candidates that triggered the drop, and the
  exact flag (``--ner-ambiguity top``) to flip the policy.
* ``top`` — keep the highest-ranked candidate.

Repeat drops of the same name in one run only warn once, to keep the log
quiet when a long directory mentions the same ambiguous town many times.

.. code-block:: bash

   geoextent -b --ner-ambiguity top --text "We met in Paris and Berlin"
   geoextent -t --period-ambiguity top --text "Iron Age burials"

The drop policy preserves provenance: dropped mentions still appear in
``place_names`` / ``date_entities`` with ``matched: false`` and the full
``candidate_count``.

Turning text extraction off
===========================

If you process a directory of structured data and want to be sure no
``README.md`` (or similar) is fed to spaCy:

.. code-block:: bash

   geoextent -b -t --text-method none path/to/data_dir

``--text-method none`` disables the text handler entirely; ``.txt`` and
``.md`` files then fall back to other handlers (e.g. tab-delimited
Darwin Core occurrence files via the CSV handler) or are skipped.

Python API
==========

The same surface is available as :func:`geoextent.lib.extent.from_text`
for in-memory strings and as the standard handler for
:func:`~geoextent.lib.extent.from_file` /
:func:`~geoextent.lib.extent.from_directory`:

.. code-block:: python

   from geoextent.lib import extent

   result = extent.from_text(
       "Sediment cores in Berlin span the Holocene; resurvey on 2024-05-12.",
       bbox=True, tbox=True,
       ner_ambiguity="top",        # keep top hit (Berlin is unambiguous, but
                                   # "Paris" or "Springfield" would otherwise drop)
       period_ambiguity="top",     # same idea for the ICS gazetteer
   )

   print(result["bbox"])   # → [13.41, 52.52, 13.41, 52.52]
   print(result["tbox"])   # → ["-9750-01-01", "2024-05-12"]

   for rec in result["place_names"]:
       print("place ", rec["name"], "→", rec.get("gazetteer_url"))
   for rec in result["date_entities"]:
       print(rec["kind"], rec["text"], "→", rec.get("start"), rec.get("end"))

Listing the bundled period gazetteer
====================================

Downstream tools (UIs, autocomplete widgets, reference docs) often need
the full list of periods that geoextent recognises, together with the
licence and provenance of the underlying data. Two paths are provided:

**CLI** — ``--list-periods`` prints the bundled gazetteer to stdout:

.. code-block:: bash

   # Full JSON output with metadata block + 178 period records
   geoextent --list-periods

   # Plain-text table for terminal scanning
   geoextent --list-periods --list-periods-format text

   # Filter by substring (case-insensitive, matches name and aliases)
   geoextent --list-periods --list-periods-filter Holo
   geoextent --list-periods --list-periods-format text --list-periods-filter Mesozoic

The header of the output carries the provenance: source repository, the
exact upstream commit SHA, the build timestamp, the licence URL, and an
attribution string suitable for embedding in a UI footer.

**Python** — :func:`geoextent.lib.period_gazetteer.list_periods` returns
the same data as a dict:

.. code-block:: python

   from geoextent.lib.period_gazetteer import list_periods

   data = list_periods()
   print(data["source"], data["source_revision"], data["built_at"])
   for rec in data["periods"][:3]:
       print(rec["name"], rec["start"], "..", rec["end"], rec["url"])

   # Narrow the list (substring on name or any alias)
   holos = list_periods(name_filter="holocene")
   assert holos["period_count"] == 1

   # Drop the metadata block — useful when the consumer already knows the
   # provenance and only needs the records themselves.
   bare = list_periods(include_metadata=False)
   assert set(bare.keys()) == {"periods", "period_count"}

The dict shape matches the on-disk ``geoextent/lib/data/periods.json``;
``schema_version`` lets consumers detect a future layout shift. The
file's metadata block is reproduced here in full:

.. code-block:: jsonc

   {
     "name": "geoextent bundled period gazetteer",
     "schema_version": "1.0",
     "source": "ICS International Chronostratigraphic Chart (GTS2020)",
     "source_url": "https://github.com/CGI-IUGS/timescale-data",
     "source_file": ".../rdf/isc2020.ttl",
     "source_revision": "<upstream commit SHA>",
     "source_revision_date": "<commit date, ISO 8601 UTC>",
     "license": "CC0-1.0",
     "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
     "attribution": "International Chronostratigraphic Chart ... CC0-1.0 ...",
     "built_at": "<build timestamp, ISO 8601 UTC>",
     "built_by": "geoextent tools/build_periods_data.py",
     "ma_bp_origin_year": 1950,
     "period_count": 178,
     "periods": [ ... ]
   }

To refresh the bundled data from upstream, run
``python tools/build_periods_data.py`` and commit the regenerated
``periods.json``.

Performance notes
=================

* spaCy + ``en_core_web_sm`` is loaded **once** per process and reused.
* The forward gazetteer keeps an in-memory ``(service, query)`` cache for
  the run, so duplicate mentions within a directory only hit the network
  once.
* Public Nominatim has a 1 req/s rate limit; large batches may benefit
  from Photon or a self-hosted Nominatim. Set ``NOMINATIM_USER_AGENT``
  (env var) to identify your application.

Limitations and roadmap
=======================

* English only out of the box (``en_core_web_sm``). Multi-language models
  exist on spaCy's hub but are not exercised by geoextent's tests.
* Historical / archaeological periods (Bronze Age, Iron Age, Medieval,
  Roman, …) are not in the bundled ICS chart. Online Wikidata-backed
  resolution is tracked in :issue:`113`.
* HTML rendering for notebooks and Web Annotation Data Model JSON-LD
  export are tracked in :issue:`114`.
