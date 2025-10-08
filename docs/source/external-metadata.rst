External Metadata Retrieval
============================

Overview
--------

The external metadata feature allows you to retrieve bibliographic metadata for Digital Object Identifiers (DOIs) from CrossRef and DataCite APIs. This is particularly useful when working with research datasets and publications, as it automatically fetches citation information, licensing details, and publication metadata.

**Key Features:**

- Retrieve metadata from CrossRef (academic publications) and DataCite (research data)
- Flexible source selection: query specific sources or all available sources
- Support for multiple DOI input formats
- Automatic DOI extraction from URLs and prefixed formats
- Rich metadata extraction including title, authors, publisher, publication year, URL, and license
- Array-based output structure for consistent handling

Supported Metadata Sources
---------------------------

CrossRef
^^^^^^^^

CrossRef is primarily used for academic publications, journal articles, books, and conference papers. It covers:

- Academic journals (e.g., PLOS ONE, Nature, Science)
- Books and book chapters
- Conference proceedings
- Reports and working papers

DataCite
^^^^^^^^

DataCite is primarily used for research datasets and related outputs. It covers:

- Research datasets (e.g., Zenodo, Figshare)
- Software and code
- Protocols and methods
- Preprints and grey literature

Quick Start
-----------

Basic Usage
^^^^^^^^^^^

Retrieve metadata for a DOI using the default ``auto`` method::

   geoextent -b --ext-metadata 10.5281/zenodo.4593540

This will:

1. Extract the geospatial extent from the Zenodo dataset
2. Try to retrieve metadata from CrossRef first
3. Fall back to DataCite if CrossRef doesn't have the DOI
4. Include the metadata in the GeoJSON output

CLI Options
-----------

``--ext-metadata``
^^^^^^^^^^^^^^^^^^

Enable external metadata retrieval. When this flag is set, geoextent will attempt to retrieve bibliographic metadata for the provided DOI.

**Example**::

   geoextent -b --ext-metadata 10.5281/zenodo.4593540

``--ext-metadata-method``
^^^^^^^^^^^^^^^^^^^^^^^^^

Control which metadata sources are queried. Accepts four values:

**auto** (default)
   Try CrossRef first, then fall back to DataCite if CrossRef fails. This is the most efficient option for unknown DOIs.

   Example::

      geoextent -b --ext-metadata --ext-metadata-method auto 10.5281/zenodo.4593540

**all**
   Query all available sources (CrossRef and DataCite) and return all results. Use this when you want to see metadata from all sources that have information about the DOI.

   Example::

      geoextent -b --ext-metadata --ext-metadata-method all 10.5281/zenodo.4593540

**crossref**
   Query CrossRef only. Use this for academic publications and journal articles.

   Example::

      geoextent -b --ext-metadata --ext-metadata-method crossref 10.1371/journal.pone.0230416

**datacite**
   Query DataCite only. Use this for research datasets and software.

   Example::

      geoextent -b --ext-metadata --ext-metadata-method datacite 10.5281/zenodo.4593540

DOI Input Formats
-----------------

The external metadata feature accepts DOIs in multiple formats:

Plain DOI
^^^^^^^^^

::

   geoextent -b --ext-metadata 10.5281/zenodo.4593540

DOI URL
^^^^^^^

::

   geoextent -b --ext-metadata https://doi.org/10.5281/zenodo.4593540

DOI with Prefix
^^^^^^^^^^^^^^^

::

   geoextent -b --ext-metadata doi:10.5281/zenodo.4593540

All formats are automatically normalized to extract the DOI before querying the metadata sources.

Output Format
-------------

Metadata Structure
^^^^^^^^^^^^^^^^^^

External metadata is always returned as an **array** (list), even when only one source is queried or only one source returns results. Each metadata entry in the array is a dictionary with the following fields:

- ``source``: The metadata source (``"CrossRef"`` or ``"DataCite"``)
- ``doi``: The DOI of the resource
- ``title``: The title of the publication or dataset
- ``authors``: Array of author names
- ``publisher``: Publisher name
- ``publication_year``: Year of publication (integer)
- ``url``: URL to the resource (usually the DOI URL)
- ``license``: License information (string or array)

Example Output (GeoJSON)
^^^^^^^^^^^^^^^^^^^^^^^^^

When using the default GeoJSON output format, the external metadata is included in the feature properties:

.. code-block:: json

   {
     "type": "FeatureCollection",
     "features": [
       {
         "type": "Feature",
         "geometry": {
           "type": "Polygon",
           "coordinates": [[...]]
         },
         "properties": {
           "external_metadata": [
             {
               "source": "DataCite",
               "doi": "10.5281/zenodo.4593540",
               "title": "Pennsylvania SGL with 1km buffer (GEOJSON)",
               "authors": ["Conner, Weston"],
               "publisher": "Zenodo",
               "publication_year": 2021,
               "url": "https://zenodo.org/record/4593540",
               "license": [
                 "https://creativecommons.org/licenses/by/4.0/legalcode",
                 "info:eu-repo/semantics/openAccess"
               ]
             }
           ]
         }
       }
     ],
     "geoextent_extraction": {...}
   }

Empty Results
^^^^^^^^^^^^^

If no metadata is found (e.g., invalid DOI or querying the wrong source), the ``external_metadata`` field will be an empty array:

.. code-block:: json

   {
     "external_metadata": []
   }

Python API
----------

Basic Usage
^^^^^^^^^^^

.. code-block:: python

   from geoextent.lib import extent

   # Retrieve extent and metadata
   result = extent.fromRemote(
       '10.5281/zenodo.4593540',
       bbox=True,
       ext_metadata=True
   )

   # Access metadata
   metadata_list = result['external_metadata']
   for metadata in metadata_list:
       print(f"Source: {metadata['source']}")
       print(f"Title: {metadata['title']}")
       print(f"Authors: {', '.join(metadata['authors'])}")
       print(f"Year: {metadata['publication_year']}")

Specifying Method
^^^^^^^^^^^^^^^^^

.. code-block:: python

   from geoextent.lib import extent

   # Query only DataCite
   result = extent.fromRemote(
       '10.5281/zenodo.4593540',
       bbox=True,
       ext_metadata=True,
       ext_metadata_method='datacite'
   )

   # Query all sources
   result = extent.fromRemote(
       '10.5281/zenodo.4593540',
       bbox=True,
       ext_metadata=True,
       ext_metadata_method='all'
   )

Direct Metadata Retrieval
^^^^^^^^^^^^^^^^^^^^^^^^^^

You can also retrieve metadata directly without extracting geospatial extent:

.. code-block:: python

   from geoextent.lib import external_metadata

   # Retrieve metadata using auto method
   metadata = external_metadata.get_external_metadata(
       '10.5281/zenodo.4593540',
       method='auto'
   )

   # Returns a list of metadata dictionaries
   for entry in metadata:
       print(entry['title'])

Use Cases
---------

Research Data Citation
^^^^^^^^^^^^^^^^^^^^^^

Automatically retrieve citation information for research datasets::

   geoextent -b --ext-metadata 10.5281/zenodo.4593540

This retrieves both the geospatial extent and the full citation metadata, making it easy to properly cite the dataset in publications.

License Verification
^^^^^^^^^^^^^^^^^^^^

Check the license of a dataset before using it::

   geoextent -b --ext-metadata --ext-metadata-method datacite 10.5281/zenodo.4593540

The output includes license information in the ``license`` field.

Cross-Registry Search
^^^^^^^^^^^^^^^^^^^^^

Search for a DOI across multiple registries::

   geoextent -b --ext-metadata --ext-metadata-method all 10.5281/zenodo.4593540

This queries both CrossRef and DataCite, returning results from all sources that have the DOI.

Publication Metadata
^^^^^^^^^^^^^^^^^^^^

Retrieve metadata for academic publications::

   geoextent -b --ext-metadata --ext-metadata-method crossref 10.1371/journal.pone.0230416

Dependencies
------------

The external metadata feature requires the following Python packages:

- ``crossref-commons``: For querying the CrossRef API
- ``datacite``: For querying the DataCite API

These dependencies are automatically installed when you install geoextent.

If you're installing geoextent from source, make sure to install with::

   pip install -e .

Or install the dependencies manually::

   pip install crossref-commons datacite

Troubleshooting
---------------

No Metadata Found
^^^^^^^^^^^^^^^^^

If no metadata is returned:

1. **Check the DOI**: Ensure the DOI is valid and correctly formatted
2. **Try different methods**: Use ``--ext-metadata-method all`` to query all sources
3. **Check the source**: Some DOIs are only in CrossRef or only in DataCite, not both
4. **Network issues**: Ensure you have internet connectivity to access the APIs

Example - DOI only in DataCite::

   # This will return empty (CrossRef doesn't have it)
   geoextent -b --ext-metadata --ext-metadata-method crossref 10.5281/zenodo.4593540

   # This will succeed
   geoextent -b --ext-metadata --ext-metadata-method datacite 10.5281/zenodo.4593540

Rate Limiting
^^^^^^^^^^^^^

Both CrossRef and DataCite APIs have rate limits. If you're processing many DOIs:

- Add delays between requests
- Use batch processing carefully
- Consider caching results
- Check the API documentation for current rate limits

API Errors
^^^^^^^^^^

If you encounter API errors:

- Check your internet connection
- Verify the API services are available
- Check the geoextent logs for detailed error messages (use ``--debug`` flag)

Example with debug logging::

   geoextent -b --ext-metadata --debug 10.5281/zenodo.4593540

Examples
--------

Example 1: Dataset with Metadata
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extract extent and metadata from a Zenodo dataset::

   geoextent -b --ext-metadata 10.5281/zenodo.4593540

Output includes geospatial extent and complete bibliographic metadata.

Example 2: Academic Publication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Retrieve metadata for a PLOS ONE article::

   geoextent -b --ext-metadata --ext-metadata-method crossref 10.1371/journal.pone.0230416

Output includes publication details, authors, and license.

Example 3: Compare Sources
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Query all sources to compare metadata::

   geoextent -b --ext-metadata --ext-metadata-method all 10.5281/zenodo.4593540

If the DOI is in multiple registries, you'll see entries from each source.

Example 4: Python Integration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Integrate metadata retrieval in a Python script:

.. code-block:: python

   from geoextent.lib import extent
   import json

   # List of DOIs to process
   dois = [
       '10.5281/zenodo.4593540',
       '10.1371/journal.pone.0230416'
   ]

   # Process each DOI
   for doi in dois:
       result = extent.fromRemote(
           doi,
           bbox=True,
           ext_metadata=True,
           ext_metadata_method='auto',
           download_data=False  # Just get metadata
       )

       # Extract and display metadata
       metadata = result.get('external_metadata', [])
       if metadata:
           meta = metadata[0]
           print(f"Title: {meta['title']}")
           print(f"Authors: {', '.join(meta['authors'])}")
           print(f"Year: {meta['publication_year']}")
           print(f"Source: {meta['source']}")
           print("---")

Best Practices
--------------

1. **Use the auto method for unknown DOIs**: This efficiently tries CrossRef first and falls back to DataCite
2. **Specify the source if you know it**: Faster and more efficient than querying all sources
3. **Handle empty results gracefully**: Always check if the metadata array is non-empty before accessing data
4. **Cache metadata when possible**: Avoid repeated API calls for the same DOI
5. **Respect rate limits**: Add delays when processing many DOIs
6. **Use --quiet for batch processing**: Suppress progress bars and logs when processing many files

See Also
--------

- :doc:`features` - Overview of all geoextent features
- :doc:`examples` - More usage examples
- :doc:`providers` - Supported content providers
- :doc:`changelog` - Recent changes and updates
