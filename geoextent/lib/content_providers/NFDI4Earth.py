"""
NFDI4Earth Knowledge Hub content provider for geoextent.

NFDI4Earth (National Research Data Infrastructure for Earth System Sciences) operates the
Knowledge Hub -- a Cordra-based digital object repository with a SPARQL endpoint, containing
1.3M+ datasets, 168 repositories, and 415K data services.  The OneStop4All portal
(onestop4all.nfdi4earth.de) is the user-facing search/discovery frontend.

Supported identifiers:
- OneStop4All landing pages: https://onestop4all.nfdi4earth.de/result/{suffix}
- Cordra object URLs: https://cordra.knowledgehub.nfdi4earth.de/objects/n4e/{suffix}
- Cordra test instance: https://cordra.knowledgehub.test.n4e.geo.tu-dresden.de/objects/n4e/{suffix}

Geospatial metadata is extracted from the SPARQL endpoint (primary) with Cordra REST API
as fallback.  Only dcat:Dataset type objects are in scope.
"""

import json
import logging
import os
import re
import shutil

import requests
from osgeo import ogr

from geoextent.lib import helpfunctions as hf
from geoextent.lib.content_providers.providers import ContentProvider

logger = logging.getLogger("geoextent")

_SPARQL_ENDPOINT = "https://sparql.knowledgehub.nfdi4earth.de"
_CORDRA_BASE = "https://cordra.knowledgehub.nfdi4earth.de"

# URL patterns for OneStop4All landing pages
_ONESTOP4ALL_RE = re.compile(
    r"https?://onestop4all\.nfdi4earth\.de/result/([\w-]+)/?$",
    re.IGNORECASE,
)

# URL patterns for Cordra object URLs (production and test instances)
_CORDRA_URL_RE = re.compile(
    r"https?://cordra\.knowledgehub\.(?:nfdi4earth\.de|test\.n4e\.geo\.tu-dresden\.de)"
    r"/objects/(n4e/[\w-]+)/?$",
    re.IGNORECASE,
)

# SPARQL query template for dataset metadata
_SPARQL_QUERY = """\
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX locn: <http://www.w3.org/ns/locn#>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX schema: <http://schema.org/>

SELECT ?title ?geometry ?startDate ?endDate ?landingPage ?type ?description
WHERE {{
  <{iri}> a ?type ;
          dct:title ?title .
  OPTIONAL {{ <{iri}> dct:spatial ?spatial .
             ?spatial locn:geometry ?geometry }}
  OPTIONAL {{ <{iri}> dct:temporal ?temporal .
             ?temporal dcat:startDate ?startDate .
             ?temporal dcat:endDate ?endDate }}
  OPTIONAL {{ <{iri}> dcat:landingPage ?landingPage }}
  OPTIONAL {{ <{iri}> schema:description ?description }}
}}
"""


class NFDI4Earth(ContentProvider):
    """Content provider for the NFDI4Earth Knowledge Hub."""

    @classmethod
    def provider_info(cls):
        return {
            "name": "NFDI4Earth",
            "description": "NFDI4Earth Knowledge Hub is a Cordra-based digital object repository for Earth System Sciences with 1.3M+ datasets, powered by a SPARQL endpoint. The OneStop4All portal provides search/discovery.",
            "website": "https://onestop4all.nfdi4earth.de/",
            "supported_identifiers": [
                "https://onestop4all.nfdi4earth.de/result/{id}",
                "https://cordra.knowledgehub.nfdi4earth.de/objects/n4e/{id}",
            ],
            "examples": [
                "https://onestop4all.nfdi4earth.de/result/dthb-82b6552d-2b8e-4800-b955-ea495efc28af/",
                "https://onestop4all.nfdi4earth.de/result/dthb-7b3bddd5af4945c2ac508a6d25537f0a/",
            ],
            "notes": "Metadata-only provider. Extracts spatial (WKT) and temporal extent from SPARQL endpoint. Can follow landingPage URLs to other supported providers.",
        }

    @property
    def supports_metadata_extraction(self):
        return True

    def __init__(self):
        super().__init__()
        self.name = "NFDI4Earth"
        self.reference = None
        self.cordra_id = None  # e.g. "n4e/dthb-82b6552d-..."
        self.cordra_iri = None  # full IRI for SPARQL
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "nuest/geoextent"})

    def validate_provider(self, reference):
        """Check if the reference is an NFDI4Earth OneStop4All or Cordra URL.

        Args:
            reference (str): Identifier to validate

        Returns:
            bool: True if this is an NFDI4Earth identifier
        """
        self.reference = reference

        # OneStop4All landing page URL
        m = _ONESTOP4ALL_RE.search(reference)
        if m:
            suffix = m.group(1)
            self.cordra_id = f"n4e/{suffix}"
            self.cordra_iri = f"{_CORDRA_BASE}/objects/{self.cordra_id}"
            return True

        # Direct Cordra object URL (production or test)
        m = _CORDRA_URL_RE.search(reference)
        if m:
            self.cordra_id = m.group(1)
            self.cordra_iri = f"{_CORDRA_BASE}/objects/{self.cordra_id}"
            return True

        return False

    def _sparql_query(self, query_str):
        """Execute a SPARQL SELECT query and return result bindings.

        Args:
            query_str (str): SPARQL query

        Returns:
            list[dict]: Result bindings from the SPARQL response
        """
        response = self.session.get(
            _SPARQL_ENDPOINT,
            params={"query": query_str},
            headers={"Accept": "application/sparql-results+json"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("results", {}).get("bindings", [])

    def _fetch_metadata_sparql(self):
        """Fetch dataset metadata from the SPARQL endpoint.

        Returns:
            dict: Normalized metadata dict, or None on failure
        """
        query = _SPARQL_QUERY.format(iri=self.cordra_iri)
        bindings = self._sparql_query(query)

        if not bindings:
            return None

        # Collect best values across bindings (may have multiple rows for
        # multiple types or language-tagged titles)
        metadata = {
            "title": None,
            "type": None,
            "geometry_wkt": None,
            "start_date": None,
            "end_date": None,
            "landing_page": None,
            "description": None,
        }

        for row in bindings:
            if "title" in row and metadata["title"] is None:
                metadata["title"] = row["title"]["value"]
            if "type" in row:
                type_val = row["type"]["value"]
                if "Dataset" in type_val:
                    metadata["type"] = "dcat:Dataset"
                elif metadata["type"] is None:
                    metadata["type"] = type_val
            if "geometry" in row and metadata["geometry_wkt"] is None:
                metadata["geometry_wkt"] = row["geometry"]["value"]
            if "startDate" in row and metadata["start_date"] is None:
                metadata["start_date"] = row["startDate"]["value"]
            if "endDate" in row and metadata["end_date"] is None:
                metadata["end_date"] = row["endDate"]["value"]
            if "landingPage" in row and metadata["landing_page"] is None:
                metadata["landing_page"] = row["landingPage"]["value"]
            if "description" in row and metadata["description"] is None:
                metadata["description"] = row["description"]["value"]

        return metadata

    def _fetch_metadata_cordra(self):
        """Fetch metadata from the Cordra REST API (fallback).

        Returns:
            dict: Normalized metadata dict, or None on failure
        """
        url = f"{_CORDRA_BASE}/objects/{self.cordra_id}"
        response = self.session.get(
            url,
            headers={"Accept": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        metadata = {
            "title": data.get("title") or data.get("name"),
            "type": data.get("@type"),
            "geometry_wkt": None,
            "start_date": None,
            "end_date": None,
            "landing_page": None,
            "description": data.get("description"),
        }

        # Extract spatial coverage
        spatial = data.get("spatialCoverage")
        if isinstance(spatial, dict):
            geo = spatial.get("geometry")
            if isinstance(geo, str):
                metadata["geometry_wkt"] = geo

        # Extract temporal coverage
        temporal = data.get("temporal")
        if isinstance(temporal, list):
            for t in temporal:
                if isinstance(t, dict):
                    if metadata["start_date"] is None:
                        metadata["start_date"] = t.get("startDate")
                    if metadata["end_date"] is None:
                        metadata["end_date"] = t.get("endDate")
        elif isinstance(temporal, dict):
            metadata["start_date"] = temporal.get("startDate")
            metadata["end_date"] = temporal.get("endDate")

        # Extract landing page
        lp = data.get("landingPage")
        if isinstance(lp, str):
            metadata["landing_page"] = lp

        return metadata

    def _fetch_metadata(self):
        """Fetch metadata, trying SPARQL first then Cordra REST fallback.

        Returns:
            dict: Normalized metadata dict
        """
        try:
            metadata = self._fetch_metadata_sparql()
            if metadata is not None:
                logger.debug("NFDI4Earth: metadata retrieved via SPARQL")
                return metadata
        except (requests.RequestException, ValueError, KeyError) as e:
            logger.warning(
                "NFDI4Earth: SPARQL endpoint failed (%s), trying Cordra REST fallback",
                e,
            )

        metadata = self._fetch_metadata_cordra()
        if metadata is not None:
            logger.debug("NFDI4Earth: metadata retrieved via Cordra REST")
            return metadata

        raise RuntimeError(
            f"NFDI4Earth: could not retrieve metadata for {self.cordra_id}"
        )

    def _extract_geographic(self, metadata):
        """Parse WKT geometry from metadata.

        Args:
            metadata (dict): Normalized metadata dict

        Returns:
            ogr.Geometry or None: Parsed geometry
        """
        wkt = metadata.get("geometry_wkt")
        if not wkt:
            return None

        geom = ogr.CreateGeometryFromWkt(wkt)
        if geom is None:
            logger.warning("NFDI4Earth: failed to parse WKT: %s", wkt[:100])
        return geom

    def _extract_temporal(self, metadata):
        """Extract temporal extent from metadata.

        Args:
            metadata (dict): Normalized metadata dict

        Returns:
            tuple or None: (start_date, end_date) as YYYY-MM-DD strings
        """
        start = metadata.get("start_date")
        end = metadata.get("end_date")

        if start is None:
            return None

        # Normalize to YYYY-MM-DD
        start = start[:10] if len(start) >= 10 else start
        if end is not None:
            end = end[:10] if len(end) >= 10 else end
        else:
            end = start

        return (start, end)

    def _extract_external_references(self, metadata):
        """Extract followable landing page URL from metadata.

        Args:
            metadata (dict): Normalized metadata dict

        Returns:
            list[str]: List of followable references (0 or 1 items)
        """
        refs = []
        lp = metadata.get("landing_page")
        if lp and isinstance(lp, str):
            lp = lp.strip()
            if hf.doi_regexp.match(lp) or hf.https_regexp.match(lp):
                refs.append(lp)
        return refs

    def _try_follow_reference(self, reference, folder, download_kwargs):
        """Try to follow an external reference to a supported provider.

        Args:
            reference (str): URL to follow
            folder (str): Download target directory
            download_kwargs (dict): Keyword arguments for provider.download()

        Returns:
            dict or None: Follow info dict on success, None on failure
        """
        from geoextent.lib.extent import _get_content_providers
        from geoextent.lib.content_providers.providers import find_provider

        provider = find_provider(reference, _get_content_providers())
        if provider is None:
            logger.info(
                "NFDI4Earth: external reference %s not matched by any provider, skipping",
                reference,
            )
            return None

        # Prevent self-referencing loops
        if isinstance(provider, NFDI4Earth):
            logger.debug("NFDI4Earth: skipping self-reference to %s", reference)
            return None

        logger.info(
            "NFDI4Earth dataset %s references %s -> following to %s",
            self.cordra_id,
            reference,
            provider.name,
        )

        try:
            provider.download(folder, **download_kwargs)
            if os.listdir(folder):
                logger.info("NFDI4Earth -> %s: follow successful", provider.name)
                return {
                    "from": "NFDI4Earth",
                    "to": provider.name,
                    "via": reference,
                }
            else:
                logger.warning(
                    "NFDI4Earth -> %s: follow produced no files", provider.name
                )
                return None
        except Exception as e:
            logger.warning("NFDI4Earth -> %s: follow failed: %s", provider.name, e)
            for f in os.listdir(folder):
                fpath = os.path.join(folder, f)
                try:
                    if os.path.isdir(fpath):
                        shutil.rmtree(fpath)
                    else:
                        os.remove(fpath)
                except OSError:
                    pass
            return None

    def _create_geojson(self, geom, metadata, temporal, folder):
        """Create a GeoJSON file from extracted geometry and metadata.

        Args:
            geom (ogr.Geometry): The geometry to write
            metadata (dict): Normalized metadata dict
            temporal (tuple or None): (start, end) dates
            folder (str): Target directory

        Returns:
            str: Path to created GeoJSON file
        """
        geojson_geom = json.loads(geom.ExportToJson())

        properties = {
            "source": "NFDI4Earth",
            "title": metadata.get("title", ""),
            "resource_type": metadata.get("type", ""),
            "cordra_id": self.cordra_id,
            "url": self.reference,
        }

        if temporal:
            properties["start_time"] = temporal[0]
            properties["end_time"] = temporal[1]

        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": geojson_geom,
                    "properties": properties,
                }
            ],
        }

        safe_id = self.cordra_id.replace("/", "_")
        filename = f"nfdi4earth_{safe_id}.geojson"
        filepath = os.path.join(folder, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)

        logger.debug("Created GeoJSON file: %s", filepath)
        return filepath

    def download(
        self,
        folder,
        throttle=False,
        download_data=True,
        show_progress=True,
        max_size_bytes=None,
        max_download_method="ordered",
        max_download_method_seed=None,
        download_skip_nogeo=False,
        download_skip_nogeo_exts=None,
        max_download_workers=4,
        follow=True,
    ):
        """Extract metadata from NFDI4Earth and create GeoJSON.

        NFDI4Earth is metadata-only: it does not host downloadable data files.
        When ``follow=True`` and ``download_data=True``, the landing page URL
        is followed to other supported providers for actual data extent extraction.

        Args:
            folder (str): Target directory for GeoJSON output
            follow (bool): Follow landing page to other providers
                (default True). Disable with ``--no-follow`` or ``follow=False``.
            (other parameters accepted for API compatibility but not used)

        Returns:
            str: Path to output directory containing GeoJSON file(s)
        """
        logger.info("Extracting metadata from NFDI4Earth: %s", self.cordra_id)

        safe_id = self.cordra_id.replace("/", "_")
        download_dir = os.path.join(folder, f"nfdi4earth_{safe_id}")
        os.makedirs(download_dir, exist_ok=True)

        self._follow_info = None

        try:
            metadata = self._fetch_metadata()

            # Try to follow landing page to other providers
            if follow and download_data:
                external_refs = self._extract_external_references(metadata)
                if external_refs:
                    download_kwargs = {
                        "throttle": throttle,
                        "download_data": download_data,
                        "show_progress": show_progress,
                        "max_size_bytes": max_size_bytes,
                        "max_download_method": max_download_method,
                        "max_download_method_seed": max_download_method_seed,
                        "download_skip_nogeo": download_skip_nogeo,
                        "download_skip_nogeo_exts": download_skip_nogeo_exts,
                        "max_download_workers": max_download_workers,
                    }
                    for ref in external_refs:
                        result = self._try_follow_reference(
                            ref, download_dir, download_kwargs
                        )
                        if result is not None:
                            self._follow_info = result
                            logger.info(
                                "NFDI4Earth: successfully followed to %s via %s",
                                result["to"],
                                result["via"],
                            )
                            return download_dir

                    logger.info(
                        "NFDI4Earth: no external references could be followed, "
                        "using own metadata"
                    )
                else:
                    logger.debug("NFDI4Earth: no external references found in metadata")
            elif not follow:
                logger.info(
                    "NFDI4Earth: follow disabled (--no-follow), using own metadata"
                )

            # Fall through: create GeoJSON from NFDI4Earth metadata
            geom = self._extract_geographic(metadata)
            if geom is None:
                logger.warning(
                    "No geographic data found for NFDI4Earth %s", self.cordra_id
                )
                return download_dir

            temporal = self._extract_temporal(metadata)
            self._create_geojson(geom, metadata, temporal, download_dir)
            return download_dir

        except requests.RequestException as e:
            logger.error("Error fetching NFDI4Earth metadata: %s", e)
            raise
