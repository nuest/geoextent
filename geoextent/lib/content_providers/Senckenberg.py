"""
Senckenberg Data Portal content provider.

The Senckenberg Biodiversity and Climate Research Centre operates a CKAN-based
data portal for publishing research datasets at https://dataportal.senckenberg.de/

This provider supports:
- Direct dataset URLs: https://dataportal.senckenberg.de/dataset/{dataset-id}
- DOIs: 10.12761/sgn.YYYY.NNNNN
- Dataset IDs (names or UUIDs)
"""

import logging
import re
from requests import HTTPError
from .CKANProvider import CKANProvider
from .. import helpfunctions as hf


class Senckenberg(CKANProvider):
    doi_prefixes = ("10.12761/sgn",)
    """
    Content provider for Senckenberg Biodiversity and Climate Research Centre.

    Senckenberg data portal uses CKAN and provides access to biodiversity,
    climate, and geoscience research data.
    """

    def __init__(self):
        super().__init__()
        self.log = logging.getLogger("geoextent")
        self.host = {
            "hostname": [
                "https://dataportal.senckenberg.de/dataset/",
                "http://dataportal.senckenberg.de/dataset/",
            ],
            "api": "https://dataportal.senckenberg.de/api/3/",
        }
        self.reference = None
        self.dataset_id = None
        self.name = "Senckenberg"
        self.throttle = False

    def validate_provider(self, reference):
        """
        Validate if the reference is a Senckenberg data portal URL or DOI.

        Supports:
        - Direct dataset URLs: https://dataportal.senckenberg.de/dataset/{id}
        - Senckenberg DOIs: 10.12761/sgn.YYYY.NNNNN (resolved via DOI.org)
        - Dataset IDs (name slugs or UUIDs)
        - .jsonld URLs (redirects to dataset page)

        Returns:
            bool: True if this provider can handle the reference
        """
        self.reference = reference

        # First, try to resolve DOI if it looks like a DOI
        url = self.get_url

        # Check for direct Senckenberg dataset URLs
        if any(url.startswith(hostname) for hostname in self.host["hostname"]):
            # Extract dataset ID from URL
            # Handle both .jsonld and regular URLs
            clean_url = url.rstrip("/")
            # Remove .jsonld extension if present
            if clean_url.endswith(".jsonld"):
                clean_url = clean_url[:-7]

            # Extract the dataset ID (last part of URL)
            self.dataset_id = clean_url.rsplit("/", maxsplit=1)[1]
            return True

        # Check for Senckenberg DOI pattern: 10.12761/sgn.YYYY.NNNNN
        senckenberg_doi_pattern = re.compile(
            r"^(?:https?://(?:dx\.)?doi\.org/)?10\.12761/sgn\.\d+\.\d+$",
            re.IGNORECASE,
        )
        if senckenberg_doi_pattern.match(reference):
            # Extract just the DOI part
            doi_match = re.search(r"10\.12761/sgn\.\d+\.\d+", reference, re.IGNORECASE)
            if doi_match:
                doi = doi_match.group(0)
                try:
                    # Resolve DOI to get the actual Senckenberg URL
                    resolved_url = self._resolve_doi_to_url(doi)
                    if resolved_url and "dataportal.senckenberg.de" in resolved_url:
                        # Extract dataset ID from resolved URL
                        clean_url = resolved_url.rstrip("/")
                        if clean_url.endswith(".jsonld"):
                            clean_url = clean_url[:-7]
                        self.dataset_id = clean_url.rsplit("/", maxsplit=1)[1]
                        return True
                except Exception as e:
                    self.log.debug(f"Failed to resolve Senckenberg DOI {doi}: {e}")
                    return False

        # Check if reference looks like a dataset ID (UUID or name slug)
        # UUIDs are 36 characters with hyphens
        uuid_pattern = re.compile(r"^[a-f0-9-]{36}$", re.IGNORECASE)
        # Name slugs are lowercase with hyphens, typically 3+ characters
        name_slug_pattern = re.compile(r"^[a-z0-9-]{3,}$", re.IGNORECASE)

        if uuid_pattern.match(reference) or name_slug_pattern.match(reference):
            # Verify this is a valid dataset by trying to fetch metadata
            try:
                self.dataset_id = reference
                self._get_metadata()
                return True
            except Exception as e:
                self.log.debug(
                    f"Reference {reference} looks like a dataset ID but validation failed: {e}"
                )
                return False

        return False

    def _resolve_doi_to_url(self, doi):
        """
        Resolve a DOI to its landing page URL.

        Args:
            doi: DOI string (e.g., "10.12761/sgn.2018.10225")

        Returns:
            str: Resolved URL
        """
        try:
            response = self._request(
                f"https://doi.org/{doi}",
                allow_redirects=True,
            )
            response.raise_for_status()
            return response.url
        except Exception as e:
            self.log.warning(f"Failed to resolve DOI {doi}: {e}")
            raise

    def _get_metadata(self):
        """
        Get dataset metadata from Senckenberg CKAN API.

        Extends parent method to handle Senckenberg-specific metadata fields.

        Returns:
            dict: Complete dataset metadata
        """
        metadata = super()._get_metadata()

        # Log Senckenberg-specific information
        if metadata:
            dataset_title = metadata.get("title", self.dataset_id)
            self.log.debug(f"Senckenberg dataset: {dataset_title}")

            # Check for restricted access
            is_private = metadata.get("private", False)
            if is_private:
                self.log.warning(
                    f"Dataset {self.dataset_id} is marked as private - access may be restricted"
                )

        return metadata

    def _extract_spatial_metadata(self):
        """
        Extract spatial extent from Senckenberg CKAN metadata.

        Senckenberg datasets include spatial coverage in top-level fields:
        - northBoundingCoordinate, southBoundingCoordinate
        - eastBoundingCoordinate, westBoundingCoordinate
        - geographicDescription (text description)

        Returns:
            dict or None: Spatial metadata with bbox in [W, S, E, N] format, or None
        """
        if not self.metadata:
            self._get_metadata()

        # Check for Senckenberg-specific bounding coordinates in top-level metadata
        north = self.metadata.get("northBoundingCoordinate")
        south = self.metadata.get("southBoundingCoordinate")
        east = self.metadata.get("eastBoundingCoordinate")
        west = self.metadata.get("westBoundingCoordinate")

        # All four coordinates must be present and numeric
        if all(coord is not None for coord in [north, south, east, west]):
            try:
                bbox = [
                    float(west),
                    float(south),
                    float(east),
                    float(north),
                ]

                geo_description = self.metadata.get("geographicDescription")
                if geo_description:
                    self.log.info(f"Found spatial extent for: {geo_description}")

                return {
                    "bbox": bbox,
                    "crs": "4326",
                }
            except (ValueError, TypeError) as e:
                self.log.debug(f"Could not parse bounding coordinates: {e}")

        # Try parent class method as fallback (standard CKAN spatial field)
        parent_spatial = super()._extract_spatial_metadata()
        if parent_spatial:
            return parent_spatial

        # Log geographic description if available but no bbox
        geo_description = self.metadata.get("geographicDescription")
        if geo_description:
            self.log.info(
                f"Dataset has geographic description but no extractable coordinates: {geo_description}"
            )

        return None

    def _extract_temporal_metadata(self):
        """
        Extract temporal extent from Senckenberg CKAN metadata.

        Senckenberg datasets include temporal coverage in top-level fields:
        - rangeOfDates: List of dicts with 'beginDate' and 'endDate'
        - singleDateTime: List of single date strings

        Returns:
            list or None: Temporal extent as [start_date, end_date], or None
        """
        if not self.metadata:
            self._get_metadata()

        # Check for rangeOfDates (preferred - has begin and end)
        range_of_dates = self.metadata.get("rangeOfDates")
        if (
            range_of_dates
            and isinstance(range_of_dates, list)
            and len(range_of_dates) > 0
        ):
            # Get the first date range
            date_range = range_of_dates[0]
            begin_date = date_range.get("beginDate")
            end_date = date_range.get("endDate")

            if begin_date and end_date:
                self.log.info(f"Found temporal extent: {begin_date} to {end_date}")
                return [begin_date, end_date]
            elif begin_date:
                # Only start date available
                self.log.info(f"Found temporal start date: {begin_date}")
                return [begin_date, None]
            elif end_date:
                # Only end date available (unusual)
                self.log.info(f"Found temporal end date: {end_date}")
                return [None, end_date]

        # Check for singleDateTime as fallback
        single_date_time = self.metadata.get("singleDateTime")
        if (
            single_date_time
            and isinstance(single_date_time, list)
            and len(single_date_time) > 0
        ):
            # Use the single date as both start and end
            date = single_date_time[0]
            if date:
                self.log.info(f"Found single date time: {date}")
                return [date, date]

        # Use parent method as fallback (checks CKAN extras)
        return super()._extract_temporal_metadata()

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
    ):
        """
        Download files from Senckenberg dataset.

        Extends parent method to handle Senckenberg-specific access restrictions.
        Some datasets may have restricted resources that require authentication.
        """
        if max_download_method_seed is None:
            max_download_method_seed = hf.DEFAULT_DOWNLOAD_SAMPLE_SEED

        # Check for access restrictions before attempting download
        if not download_data:
            # Metadata-only mode - use parent class implementation which creates GeoJSON
            self.log.info(
                f"Extracting metadata-only from Senckenberg dataset {self.dataset_id}"
            )

        # Use parent download method (handles both metadata-only and full download)
        super().download(
            folder=folder,
            throttle=throttle,
            download_data=download_data,
            show_progress=show_progress,
            max_size_bytes=max_size_bytes,
            max_download_method=max_download_method,
            max_download_method_seed=max_download_method_seed,
            download_skip_nogeo=download_skip_nogeo,
            download_skip_nogeo_exts=download_skip_nogeo_exts,
            max_download_workers=max_download_workers,
        )
