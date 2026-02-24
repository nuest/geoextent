
API Docs
========

Documentation for the package's Python API for usage as a library.

Individual files
-----------------

The main function is:

::

   geoextent.from_file(input, bbox, time)

**Parameters:**
   - ``input``: a string value of input file or path
   - ``bbox``: a boolean value to extract spatial extent (bounding box)
   - ``time``: a boolean value to extract temporal extent ( at "day" precision '%Y-%m-%d')

The output of this function is the bbox and/or the tbox for individual files (see: :doc:`../supportedformats/index_supportedformats`). The resulting coordinate reference system  ``CRS`` of the bounding box is the one resulting from the extraction (i.e no transformation to other coordinate reference system).

Examples
--------

Extract bounding box from a single file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Code:

::

   geoextent.from_file('muenster_ring_zeit.geojson', True, False)

Output:

.. jupyter-execute::
   :hide-code:
   :stderr:

   import geoextent.lib.extent as geoextent
   geoextent.from_file('../tests/testdata/geojson/muenster_ring_zeit.geojson', True, False)

(`source of file muenster_ring_zeit.geojson`_)

Extracting time interval from a single file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Code:

::

   geoextent.from_file('muenster_ring_zeit.geojson', False, True)

Output:

.. jupyter-execute::
   :hide-code:
   :stderr:

   import geoextent.lib.extent as geoextent
   geoextent.from_file('../tests/testdata/geojson/muenster_ring_zeit.geojson', False, True)

(`source of file muenster_ring_zeit.geojson`_)

Extracting both bounding box and time interval from a single file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Code:

::

   geoextent.from_file('muenster_ring_zeit.geojson', True, True)

Output:

.. jupyter-execute::
   :hide-code:
   :stderr:

   import geoextent.lib.extent as geoextent
   geoextent.from_file('../tests/testdata/geojson/muenster_ring_zeit.geojson', True, True)

(`source of file muenster_ring_zeit.geojson`_)

.. _source of file muenster_ring_zeit.geojson: https://github.com/nuest/geoextent/blob/main/tests/testdata/geojson/muenster_ring_zeit.geojson

Folders or ZIP file(s)
----------------------

**Geoextent** also supports queries for multiple files inside **folders** or **ZIP files**.

::

   geoextent.from_directory(input, bbox, time, details)

**Parameters:**
   - ``input``: a string value of directory of zipfile path
   - ``bbox``: a boolean value to extract spatial extent (bounding box)
   - ``time``: a boolean value to extract temporal extent ( at "day" precision '%Y-%m-%d')
   - ``details``: a boolean value to return details (geoextent) of individual files (default **False**)
   - ``workers``: number of parallel workers for file extraction (default **1** = sequential, **0** = auto-detect CPU count). Parallel extraction uses threads and helps most with directories containing many files (tens or more), where per-file I/O latency adds up.

The output of this function is the combined bbox or tbox resulting from merging all results of individual files (see: :doc:`../supportedformats/index_supportedformats`) inside the folder or zipfile. The resulting coordinate reference system  ``CRS`` of the combined bbox is always in the `EPSG: 4326 <https://epsg.io/4326>`_ system.

Extracting both bounding box and time interval from a folder (with details)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Code:

::

   geoextent.from_directory('folder_one_file', True, True, True)

Output:

.. jupyter-execute::
   :hide-code:
   :stderr:

   import geoextent.lib.extent as geoextent
   geoextent.from_directory('../tests/testdata/folders/folder_one_file', True, True, True)

`folder_two_files <https://github.com/nuest/geoextent/blob/main/tests/testdata/folders/folder_two_files>`_

Remote repositories
-------------------

**Geoextent** supports queries for multiple research data repositories including Zenodo, Figshare, Dryad, PANGAEA, OSF, Dataverse, GFZ Data Services, Pensoft, GBIF, SEANOE, DEIMS-SDR, HALO DB, GDI-DE, Arctic Data Center, and TU Dresden Opara.

Geoextent downloads files from the repository and extracts the temporal or geographical extent. The function supports both single identifiers (string) and multiple identifiers (list).

::

   geoextent.from_remote(remote_identifier, bbox, time, details)

**Parameters:**
   - ``remote_identifier``: a string value with a repository URL or DOI (e.g., https://zenodo.org/record/3528062, https://doi.org/10.5281/zenodo.3528062, 10.5281/zenodo.3528062), or a list of identifiers for multiple resource extraction
   - ``bbox``: a boolean value to extract spatial extent (bounding box)
   - ``time``: a boolean value to extract temporal extent (at "day" precision '%Y-%m-%d')
   - ``details``: a boolean value to return details (geoextent) of individual files (default **False**)

The output of this function is the combined bbox or tbox resulting from merging all results of individual files (see: :doc:`../supportedformats/index_supportedformats`) inside the repository. The resulting coordinate reference system  ``CRS`` of the combined bbox is always in the `EPSG: 4326 <https://epsg.io/4326>`_ system.

Single repository extraction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Code:

::

   geoextent.from_remote('https://zenodo.org/record/820562', True, True, False)

Output:

.. jupyter-execute::
   :hide-code:
   :stderr:

   import geoextent.lib.extent as geoextent
   geoextent.from_remote('https://zenodo.org/record/820562', True, True)

Multiple repositories
^^^^^^^^^^^^^^^^^^^^^

Extract from multiple repositories in a single call:

::

   identifiers = [
       '10.5281/zenodo.4593540',
       '10.25532/OPARA-581',
       'https://osf.io/abc123/'
   ]

   geoextent.from_remote(identifiers, True, True, True)

The function returns a **merged bounding box** covering all resources (similar to directory extraction), plus extraction metadata with success/failure tracking. Individual resource details are available in the ``details`` field for diagnostics.

See :doc:`../features` for detailed documentation on multiple resource extraction features and return structure.

Download size limits
^^^^^^^^^^^^^^^^^^^^^

Use the ``max_download_size`` parameter to limit how much data geoextent downloads from a remote repository. The value is a human-friendly size string parsed by `filesizelib <https://pypi.org/project/filesizelib/>`_ (e.g. ``'100MB'``, ``'2GB'``, ``'500KB'``, ``'10MiB'``, ``'0.5GiB'``):

::

   # Limit download to 20 MB
   geoextent.from_remote('10.23728/b2share.26jnj-a4x24', bbox=True, tbox=True,
                         max_download_size='20MB')

   # Limit GBIF DwC-A download to 500 MB
   geoextent.from_remote('10.15468/6bleia', bbox=True, tbox=True,
                         max_download_size='500MB')

When the combined file sizes exceed the limit, the default behavior (API) is to silently select a subset using the ``max_download_method`` strategy (``'ordered'`` by default, or ``'random'`` with a reproducible seed via ``max_download_method_seed``).

Download size soft limit
""""""""""""""""""""""""

Set ``download_size_soft_limit=True`` to raise a ``DownloadSizeExceeded`` exception instead of silently truncating the file list. This is what the CLI uses to prompt the user for confirmation, and is available for all providers whose APIs report file sizes:

::

   from geoextent.lib.exceptions import DownloadSizeExceeded

   try:
       result = geoextent.from_remote('10.5281/zenodo.820562', bbox=True,
                                      max_download_size='1MB',
                                      download_size_soft_limit=True)
   except DownloadSizeExceeded as exc:
       print(f"Download is {exc.estimated_size:,} bytes "
             f"(limit: {exc.max_size:,} bytes, provider: {exc.provider})")
       # Retry with a larger limit
       result = geoextent.from_remote('10.5281/zenodo.820562', bbox=True,
                                      max_download_size=f'{exc.estimated_size + 1}B',
                                      download_size_soft_limit=True)

The exception carries three attributes:

- ``exc.estimated_size`` — total available download size in bytes
- ``exc.max_size`` — the size limit that was exceeded, in bytes
- ``exc.provider`` — name of the provider (e.g. ``"Zenodo"``, ``"GBIF"``)

**GBIF DwC-A soft limit.** GBIF datasets with Darwin Core Archive downloads have an additional built-in 1 GB soft limit that is always active (regardless of ``download_size_soft_limit``).

.. note::

   The soft limit relies on providers reporting file sizes in their API metadata before download. Metadata-only providers (DEIMS-SDR, HALO DB, Wikidata, Pensoft) do not download data files, so the size limit does not apply. A warning is logged when ``max_download_size`` is configured but the provider cannot enforce it.

To avoid the size check entirely, use ``download_data=False`` for metadata-only extraction:

::

   # Fast, no download — uses provider API metadata
   result = geoextent.from_remote('10.15468/6bleia', bbox=True, tbox=True,
                                  download_data=False)

Progress callbacks
------------------

All three public API functions (``from_file``, ``from_directory``, ``from_remote``)
accept a ``progress_callback`` parameter for structured progress reporting.
This is useful for web applications, Jupyter notebooks, and other programmatic
consumers that need to display progress without depending on tqdm.

The callback receives :class:`~geoextent.lib.progress.ProgressEvent` instances
-- frozen dataclasses describing what geoextent is doing at each step.

Quick start
^^^^^^^^^^^

::

   from geoextent.lib.progress import CollectingProgressCallback
   from geoextent.lib import extent

   cb = CollectingProgressCallback()
   result = extent.from_file(
       'data.tif',
       bbox=True,
       tbox=True,
       progress_callback=cb,
   )

   for event in cb.events:
       print(f'{event.phase.value}: {event.message} [{event.current}/{event.total}]')

Output::

   process_file: Processing data.tif [0/2]
   spatial: Processing data.tif [1/2]
   temporal: Processing data.tif [2/2]

ProgressEvent
^^^^^^^^^^^^^

Each event is a frozen (immutable) dataclass with these fields:

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - ``phase``
     - ``ProgressPhase``
     - Which processing phase emitted this event (see table below).
   * - ``message``
     - ``str``
     - Human-readable description (e.g. ``"Processing directory: mydata"``).
   * - ``current``
     - ``int``
     - Current step number (0 when phase starts).
   * - ``total``
     - ``int``
     - Total number of steps (0 if unknown).
   * - ``detail``
     - ``str | None``
     - Optional extra context (filename, provider name, etc.).
   * - ``bytes_current``
     - ``int``
     - Bytes processed so far (download phase only).
   * - ``bytes_total``
     - ``int``
     - Total bytes to download (download phase only).

Two computed properties are available:

- ``event.fraction`` -- progress as a float in ``[0.0, 1.0]``, or ``-1.0`` if
  indeterminate (``total <= 0``).
- ``event.is_indeterminate`` -- ``True`` when ``total`` is unknown.

ProgressPhase
^^^^^^^^^^^^^

Events are tagged with a phase indicating which part of the pipeline emitted them:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Phase
     - Emitted by
     - Description
   * - ``PROCESS_FILE``
     - ``from_file``
     - Starting to process a single file.
   * - ``SPATIAL``
     - ``from_file``
     - Spatial extent extraction completed for a file.
   * - ``TEMPORAL``
     - ``from_file``
     - Temporal extent extraction completed for a file.
   * - ``PROCESS_DIR``
     - ``from_directory``
     - Processing the *n*-th item in a directory. ``current``/``total`` track progress.
   * - ``MERGE``
     - ``from_directory``
     - Merging individual file results into a combined extent.
   * - ``RESOLVE``
     - ``from_remote``
     - A content provider has been identified for the remote identifier.
   * - ``DOWNLOAD``
     - ``from_remote``
     - Downloading files from a remote repository. ``bytes_current``/``bytes_total`` track byte-level progress.
   * - ``EXTRACT``
     - --
     - Extracting an archive.
   * - ``PLACENAME``
     - --
     - Reverse-geocoding coordinates to a placename.

Built-in callbacks
^^^^^^^^^^^^^^^^^^

Three callback implementations are provided in ``geoextent.lib.progress``:

**CollectingProgressCallback** -- appends every event to a list. Useful for
testing and post-hoc analysis.

::

   from geoextent.lib.progress import CollectingProgressCallback

   cb = CollectingProgressCallback()
   result = extent.from_directory('mydata/', bbox=True, progress_callback=cb)
   print(f'{len(cb.events)} events captured')

**LoggingProgressCallback** -- logs each event to the ``geoextent`` logger. The
log level is configurable (default ``INFO``).

::

   from geoextent.lib.progress import LoggingProgressCallback

   cb = LoggingProgressCallback()  # or LoggingProgressCallback(level=logging.DEBUG)
   result = extent.from_file('data.shp', bbox=True, progress_callback=cb)

**TqdmProgressCallback** -- renders tqdm progress bars, one per phase. This is
what geoextent uses internally when ``show_progress=True`` and no callback is
provided.

::

   from geoextent.lib.progress import TqdmProgressCallback

   cb = TqdmProgressCallback(leave=True)  # leave=True keeps bars on screen
   result = extent.from_directory('mydata/', bbox=True, progress_callback=cb)
   cb.close()  # close any open bars

Writing a custom callback
^^^^^^^^^^^^^^^^^^^^^^^^^

A callback is any callable that accepts a single ``ProgressEvent`` argument.
Here is an example that pushes progress to a web API:

::

   import requests
   from geoextent.lib.progress import ProgressEvent

   def webhook_callback(event: ProgressEvent) -> None:
       requests.post('https://example.com/progress', json={
           'phase': event.phase.value,
           'message': event.message,
           'fraction': event.fraction,
           'detail': event.detail,
       }, timeout=5)

   result = extent.from_remote(
       '10.5281/zenodo.820562',
       bbox=True,
       tbox=True,
       progress_callback=webhook_callback,
   )

Here is an example that updates a Jupyter notebook widget:

::

   import ipywidgets as widgets
   from IPython.display import display
   from geoextent.lib.progress import ProgressEvent

   progress_bar = widgets.FloatProgress(min=0, max=1, description='Extracting...')
   status_label = widgets.Label()
   display(widgets.HBox([progress_bar, status_label]))

   def jupyter_callback(event: ProgressEvent) -> None:
       if not event.is_indeterminate:
           progress_bar.value = event.fraction
       status_label.value = event.message

   result = extent.from_directory(
       'mydata/',
       bbox=True,
       progress_callback=jupyter_callback,
   )
   progress_bar.value = 1.0
   status_label.value = 'Done'

Interaction with show_progress
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- When ``progress_callback`` is provided, geoextent automatically suppresses
  internal tqdm bars (equivalent to ``show_progress=False``) to avoid duplicate
  output.
- When ``progress_callback`` is ``None`` and ``show_progress=True`` (the
  default), geoextent auto-creates a ``TqdmProgressCallback`` internally for
  backward compatibility. The CLI uses this path.
- To disable all progress output, pass both ``show_progress=False`` and omit
  ``progress_callback``.
