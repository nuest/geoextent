
API Docs
========

Documentation for the package's Python API for usage as a library.

Individual files
-----------------

The main function is:

::

   geoextent.fromFile(input, bbox, time)

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

   geoextent.fromFile('muenster_ring_zeit.geojson', True, False)

Output:

.. jupyter-execute::
   :hide-code:
   :stderr:

   import geoextent.lib.extent as geoextent
   geoextent.fromFile('../tests/testdata/geojson/muenster_ring_zeit.geojson', True, False)

(`source of file muenster_ring_zeit.geojson`_)

Extracting time interval from a single file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Code:

::

   geoextent.fromFile('muenster_ring_zeit.geojson', False, True)

Output:

.. jupyter-execute::
   :hide-code:
   :stderr:

   import geoextent.lib.extent as geoextent
   geoextent.fromFile('../tests/testdata/geojson/muenster_ring_zeit.geojson', False, True)

(`source of file muenster_ring_zeit.geojson`_)

Extracting both bounding box and time interval from a single file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Code:

::

   geoextent.fromFile('muenster_ring_zeit.geojson', True, True)

Output:

.. jupyter-execute::
   :hide-code:
   :stderr:

   import geoextent.lib.extent as geoextent
   geoextent.fromFile('../tests/testdata/geojson/muenster_ring_zeit.geojson', True, True)

(`source of file muenster_ring_zeit.geojson`_)

.. _source of file muenster_ring_zeit.geojson: https://github.com/nuest/geoextent/blob/main/tests/testdata/geojson/muenster_ring_zeit.geojson

Folders or ZIP file(s)
----------------------

**Geoextent** also supports queries for multiple files inside **folders** or **ZIP files**.

::

   geoextent.fromDirectory(input, bbox, time, details)

**Parameters:**
   - ``input``: a string value of directory of zipfile path
   - ``bbox``: a boolean value to extract spatial extent (bounding box)
   - ``time``: a boolean value to extract temporal extent ( at "day" precision '%Y-%m-%d')
   - ``details``: a boolean value to return details (geoextent) of individual files (default **False**)

The output of this function is the combined bbox or tbox resulting from merging all results of individual files (see: :doc:`../supportedformats/index_supportedformats`) inside the folder or zipfile. The resulting coordinate reference system  ``CRS`` of the combined bbox is always in the `EPSG: 4326 <https://epsg.io/4326>`_ system.

Extracting both bounding box and time interval from a folder (with details)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Code:

::

   geoextent.fromDirectory('folder_one_file', True, True, True)

Output:

.. jupyter-execute::
   :hide-code:
   :stderr:

   import geoextent.lib.extent as geoextent
   geoextent.fromDirectory('../tests/testdata/folders/folder_one_file', True, True, True)

`folder_two_files <https://github.com/nuest/geoextent/blob/main/tests/testdata/folders/folder_two_files>`_

Remote repositories
-------------------

**Geoextent** supports queries for multiple research data repositories including Zenodo, Figshare, Dryad, PANGAEA, OSF, Dataverse, GFZ Data Services, Pensoft, GBIF, SEANOE, DEIMS-SDR, HALO DB, Arctic Data Center, and TU Dresden Opara.

Geoextent downloads files from the repository and extracts the temporal or geographical extent. The function supports both single identifiers (string) and multiple identifiers (list).

::

   geoextent.fromRemote(remote_identifier, bbox, time, details)

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

   geoextent.fromRemote('https://zenodo.org/record/820562', True, True, False)

Output:

.. jupyter-execute::
   :hide-code:
   :stderr:

   import geoextent.lib.extent as geoextent
   geoextent.fromRemote('https://zenodo.org/record/820562', True, True)

Multiple repositories
^^^^^^^^^^^^^^^^^^^^^

Extract from multiple repositories in a single call:

::

   identifiers = [
       '10.5281/zenodo.4593540',
       '10.25532/OPARA-581',
       'https://osf.io/abc123/'
   ]

   geoextent.fromRemote(identifiers, True, True, True)

The function returns a **merged bounding box** covering all resources (similar to directory extraction), plus extraction metadata with success/failure tracking. Individual resource details are available in the ``details`` field for diagnostics.

See :doc:`../features` for detailed documentation on multiple resource extraction features and return structure.

Download size limits
^^^^^^^^^^^^^^^^^^^^^

Use the ``max_download_size`` parameter to limit how much data geoextent downloads from a remote repository. The value is a human-friendly size string parsed by `filesizelib <https://pypi.org/project/filesizelib/>`_ (e.g. ``'100MB'``, ``'2GB'``, ``'500KB'``, ``'10MiB'``, ``'0.5GiB'``):

::

   # Limit download to 20 MB
   geoextent.fromRemote('10.23728/b2share.26jnj-a4x24', bbox=True, tbox=True,
                         max_download_size='20MB')

   # Limit GBIF DwC-A download to 500 MB
   geoextent.fromRemote('10.15468/6bleia', bbox=True, tbox=True,
                         max_download_size='500MB')

When the combined file sizes exceed the limit, the default behavior (API) is to silently select a subset using the ``max_download_method`` strategy (``'ordered'`` by default, or ``'random'`` with a reproducible seed via ``max_download_method_seed``).

Download size soft limit
""""""""""""""""""""""""

Set ``download_size_soft_limit=True`` to raise a ``DownloadSizeExceeded`` exception instead of silently truncating the file list. This is what the CLI uses to prompt the user for confirmation, and is available for all providers whose APIs report file sizes:

::

   from geoextent.lib.exceptions import DownloadSizeExceeded

   try:
       result = geoextent.fromRemote('10.5281/zenodo.820562', bbox=True,
                                      max_download_size='1MB',
                                      download_size_soft_limit=True)
   except DownloadSizeExceeded as exc:
       print(f"Download is {exc.estimated_size:,} bytes "
             f"(limit: {exc.max_size:,} bytes, provider: {exc.provider})")
       # Retry with a larger limit
       result = geoextent.fromRemote('10.5281/zenodo.820562', bbox=True,
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
   result = geoextent.fromRemote('10.15468/6bleia', bbox=True, tbox=True,
                                  download_data=False)
