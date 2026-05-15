Journal Landing Page Examples
==============================

This page demonstrates how to extract geospatial extent from **journal article
landing pages** that advertise spatial metadata in their HTML head. Geoextent
ships with a ``journals/`` umbrella content provider that detects three
publishing platforms out of the box and pulls a normalised bbox / tbox out of
whatever encoding the publisher chose.

Overview
--------

The ``journals/`` umbrella covers:

- **OJS** (Open Journal Systems) with the
  `ojsGeo <https://github.com/nuest/ojsGeo>`_ plugin — fingerprinted via the
  ``<meta name="generator" content="Open Journal Systems …">`` tag every OJS
  theme emits.
- **Janeway** with the
  `janeway_geometadata <https://github.com/GeoinformationSystems/janeway_geometadata/>`_
  plugin — fingerprinted via the ``<link rel="alternate"
  type="application/geo+json">`` link the plugin always renders, plus the
  ``/article/id/{N}/`` URL pattern.
- **Pensoft** journals (e.g. Biodiversity Data Journal, ZooKeys) — DOI-prefix
  fast-path on ``10.3897/`` plus a JSON-LD ``contentLocation`` walker. See
  :doc:`examples` for the existing Pensoft example.

For OJS and Janeway you can pass either:

- the article landing-page URL (``http://journal-host/article/view/{N}`` or
  ``/article/id/{N}/``), or
- a DOI that resolves to the article (any prefix — the OJS/Janeway providers
  do not need a per-publisher allowlist).

A journal that advertises the platform but does **not** have the geo plugin
installed is still recognised; geoextent then returns no spatial extent but
will still surface the publication date and, when ``--ext-metadata`` is set,
look up the article DOI on CrossRef / DataCite.

Source-Preference Priority
--------------------------

When a page emits the same article in multiple encodings, the provider picks
the one most likely to carry the richest geometry, *not* the one easiest to
parse. Priority order (first match wins):

1. JSON-LD ``<script type="application/ld+json">`` with ``spatialCoverage``
   or ``contentLocation`` — may carry Point, Polygon, MultiPolygon,
   GeometryCollection, Feature, or FeatureCollection.
2. ``<link rel="alternate" type="application/geo+json">`` — fetched inline
   from the plugin's canonical export endpoint.
3. ``DC.SpatialCoverage`` with ``scheme="GeoJSON"`` (handles both the OJS
   FeatureCollection wrapper and the Janeway single-Feature wrapper).
4. ``DC.SpatialCoverage`` with ``scheme="WKT"``.
5. Inlined ISO 19139 ``EX_GeographicBoundingBox`` snippets.
6. DCMI Box (``DC.box``) bounding-box fields.
7. OJS ``administrativeUnits[].bbox`` fallback (when the plugin recorded an
   admin unit but no real geometry).
8. ``ICBM`` / ``geo.position`` centroids — last resort, single-point bbox.

The temporal extent chain is analogous, but more conservative: JSON-LD
``temporalCoverage`` → ``DC.temporal`` / ``DC.PeriodOfTime`` ISO 8601
intervals → embedded GeoJSON ``temporal_periods``. **Publication-date meta
tags (``DC.Date.issued``, ``citation_publication_date``, ``citation_date``)
are deliberately NOT used as a fallback** — a journal article's
publication date is metadata about the *article*, not about what the
article *studied*. If no research-period source is present, ``tbox`` stays
``None``.

Basic Extraction
----------------

OJS article with a real polygon and research period
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Article 40 in the TIB OJS demo journal carries a polygon over Brandenburg
and a *research* period of 2008–2018 advertised via
``<meta name="DC.temporal" scheme="ISO8601" content="2008-01-01/2018-12-31"/>``
— note that this is **distinct** from the publication date in
``DC.Date.issued`` (``2025-07-14``). The temporal resolver prefers the
research period because it appears earlier in the priority list:

.. code-block:: bash

   python -m geoextent -b -t \\
     https://service.tib.eu/komet/ojs330/index.php/gmdj/article/view/40

Output:

.. code-block:: json

   {
     "type": "FeatureCollection",
     "features": [
       {
         "type": "Feature",
         "geometry": {
           "type": "Polygon",
           "coordinates": [[
             [11.2657725, 51.359064],
             [14.7658159, 51.359064],
             [14.7658159, 53.5590907],
             [11.2657725, 53.5590907],
             [11.2657725, 51.359064]
           ]]
         },
         "properties": {
           "tbox": ["2008-01-01", "2018-12-31"]
         }
       }
     ],
     "geoextent_extraction": {
       "inputs": ["https://service.tib.eu/komet/ojs330/index.php/gmdj/article/view/40"],
       "format": "remote",
       "crs": "4326",
       "extent_type": "bounding_box"
     }
   }

OJS article with point coordinates and no research period
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Article 32 on the same demo journal references a study site in Sulawesi as a
single point and has **no** ``DC.temporal`` / ``DC.PeriodOfTime`` / JSON-LD
``temporalCoverage`` — only a ``DC.Date.issued`` publication date, which is
intentionally not used as a fallback. ``tbox`` is therefore absent from the
output. The point itself comes from the GeoJSON-encoded
``DC.SpatialCoverage`` (the OJS plugin's first-class encoding):

.. code-block:: bash

   python -m geoextent -b -t \\
     https://service.tib.eu/komet/ojs330/index.php/gmdj/article/view/32

Output (geometry shortened):

.. code-block:: json

   {
     "type": "FeatureCollection",
     "features": [
       {
         "type": "Feature",
         "geometry": {
           "type": "Point",
           "coordinates": [121.34369641542438, -3.9118318544582156]
         },
         "properties": {}
       }
     ],
     "geoextent_extraction": {"extent_type": "point", "format": "remote", "crs": "4326"}
   }

Edge case: platform detected, no spatial metadata
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Real-world OJS journals that have not installed the geo plugin yet are still
recognised as OJS via the ``generator`` meta tag, so the provider claims the
request even though it has nothing spatial to return. Article 170 in JOSIS is
a real peer-reviewed paper without spatial metadata on its landing page:

.. code-block:: bash

   python -m geoextent -b -t \\
     https://josis.org/index.php/josis/article/view/170

Output:

.. code-block:: json

   {
     "format": "remote",
     "_extracted_doi": "10.5311/JOSIS.2021.23.170"
   }

The provider was unable to compute a bounding box (no spatial extent warning
is logged) and no temporal extent is reported either — only the article DOI
is lifted from the head, which sets up the next example.

External Metadata Enrichment via Extracted DOI
-----------------------------------------------

This is what makes the journal providers genuinely useful in citation
pipelines: pass the **URL** of any journal article and combine ``--ext-metadata``
with the platform fingerprint to get CrossRef / DataCite metadata back, even
though the user never typed the DOI:

.. code-block:: bash

   python -m geoextent -b -t --ext-metadata \\
     https://josis.org/index.php/josis/article/view/170

The provider:

1. Resolves the URL → fetches the landing page.
2. Detects the OJS generator meta tag → claims the request.
3. Lifts the article DOI out of the HTML head — in order: JSON-LD
   ``identifier`` blocks, ``citation_doi`` meta, ``prism.doi``, then
   ``DC.Identifier`` if it looks like a DOI.
4. Substitutes that extracted DOI for the URL when calling
   ``external_metadata.get_external_metadata`` so CrossRef returns a hit.

Output (single-resource shape):

.. code-block:: json

   {
     "format": "remote",
     "_extracted_doi": "10.5311/JOSIS.2021.23.170",
     "external_metadata": [
       {
         "source": "CrossRef",
         "doi": "10.5311/JOSIS.2021.23.170",
         "title": "Identifying regional variation in place visit behavior during a global pandemic",
         "authors": ["Grant McKenzie", "Kevin Mwenda"],
         "publisher": "Journal of Spatial Information Science",
         "publication_year": 2021,
         "url": "https://doi.org/10.5311/josis.2021.23.170",
         "license": "https://creativecommons.org/licenses/by/3.0/"
       }
     ]
   }

Without ``--ext-metadata`` the ``external_metadata`` array is omitted; with
the flag it is populated whenever the provider could lift a DOI from the
head, regardless of whether the original input was a URL or already a DOI.

Python API
----------

Same flow from Python:

.. code-block:: python

   import geoextent.lib.extent as geoextent

   result = geoextent.from_remote(
       "https://josis.org/index.php/josis/article/view/170",
       bbox=True,
       tbox=True,
       ext_metadata=True,
   )

   print(result["_extracted_doi"])
   # "10.5311/JOSIS.2021.23.170"

   print(result["external_metadata"][0]["title"])
   # "Identifying regional variation in place visit behavior during a global pandemic"

   print(result.get("tbox"))
   # None — JOSIS article 170 has no research-period meta tag, and the
   # publication date is intentionally not used as a tbox fallback.

Janeway example
---------------

The Janeway plugin emits more meta tags than ojsGeo — DC.SpatialCoverage in
both WKT and GeoJSON, DC.box, ISO 19139, schema.org JSON-LD with
``spatialCoverage`` Place, plus a separate ``application/geo+json`` alternate
link. Because Janeway has no public demo URL, this example uses the local
``Delta Quadrant Journal`` dev instance (article IDs drift as the dev DB is
reset):

.. code-block:: bash

   python -m geoextent -b -t \\
     http://localhost:8000/dqj/article/id/251/

Output (Laos polygon, geometry abbreviated):

.. code-block:: json

   {
     "type": "FeatureCollection",
     "features": [
       {
         "type": "Feature",
         "geometry": {
           "type": "Polygon",
           "coordinates": [[
             [100.1, 13.9], [107.7, 13.9],
             [107.7, 22.5], [100.1, 22.5],
             [100.1, 13.9]
           ]]
         },
         "properties": {}
       }
     ],
     "geoextent_extraction": {"extent_type": "bounding_box", "format": "remote", "crs": "4326"}
   }

(The Janeway demo article 251 emits an empty ``temporal_periods`` list and
no ``DC.temporal``, so no research-period source is available; the
publication date is excluded as a fallback per the rule above.)

Notes and Limitations
---------------------

- The DOI extracted from the HTML head is exposed in the per-resource
  dictionary as ``_extracted_doi``. With ``--ext-metadata`` it is used as the
  CrossRef / DataCite lookup key whenever the user-supplied identifier is a
  URL, not a DOI.
- The alternate ``application/geo+json`` link is fetched inline as one
  additional GET; failures fall through to the next priority rule silently
  (debug-logged). Set ``--debug`` to see the fetch attempt.
- Coordinate order at the public API boundary is EPSG:4326 native
  ``[lat, lon]``. GeoJSON output remains ``[lon, lat]`` per RFC 7946. Use
  ``--legacy`` to switch the bbox output to ``[lon, lat]``.
- See :doc:`features` for a list of every meta tag and JSON-LD shape the
  ``journals/`` provider recognises, and :issue:`76` for the implementation
  history.
