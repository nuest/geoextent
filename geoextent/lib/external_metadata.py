"""
External metadata retrieval from CrossRef and DataCite APIs.

This module provides functionality to retrieve bibliographic metadata for DOIs
from CrossRef and DataCite registries.
"""

import logging
import re

logger = logging.getLogger("geoextent")

# DOI pattern matching
DOI_PATTERN = re.compile(r"10\.\d{4,}(?:\.\d+)*\/\S+")


def extract_doi_from_string(identifier: str) -> str | None:
    """
    Extract DOI from various formats (plain DOI, DOI URL, etc.).

    Args:
        identifier: String that may contain a DOI

    Returns:
        Extracted DOI string or None if no DOI found
    """
    # Remove common URL prefixes
    identifier = identifier.strip()
    identifier = re.sub(r"^https?://doi\.org/", "", identifier)
    identifier = re.sub(r"^https?://dx\.doi\.org/", "", identifier)
    identifier = re.sub(r"^doi:", "", identifier, flags=re.IGNORECASE)

    # Try to match DOI pattern
    match = DOI_PATTERN.search(identifier)
    if match:
        return match.group(0)

    return None


def get_crossref_metadata(doi: str) -> dict | None:
    """
    Retrieve metadata from CrossRef API.

    Args:
        doi: DOI string (e.g., "10.5281/zenodo.4593540")

    Returns:
        Dictionary with metadata fields or None if retrieval fails
    """
    try:
        from crossref_commons.retrieval import get_publication_as_json

        result = get_publication_as_json(doi)

        if not result:
            return None

        # Extract relevant fields
        metadata = {
            "source": "CrossRef",
            "doi": doi,
        }

        # Title
        if "title" in result and result["title"]:
            metadata["title"] = (
                result["title"][0]
                if isinstance(result["title"], list)
                else result["title"]
            )

        # Authors
        if "author" in result:
            authors = []
            for author in result["author"]:
                name_parts = []
                if "given" in author:
                    name_parts.append(author["given"])
                if "family" in author:
                    name_parts.append(author["family"])
                if name_parts:
                    authors.append(" ".join(name_parts))
            if authors:
                metadata["authors"] = authors

        # Publisher
        if "publisher" in result:
            metadata["publisher"] = result["publisher"]

        # Publication year
        if "published" in result and "date-parts" in result["published"]:
            date_parts = result["published"]["date-parts"]
            if date_parts and len(date_parts[0]) > 0:
                metadata["publication_year"] = date_parts[0][0]
        elif "published-print" in result and "date-parts" in result["published-print"]:
            date_parts = result["published-print"]["date-parts"]
            if date_parts and len(date_parts[0]) > 0:
                metadata["publication_year"] = date_parts[0][0]

        # URL
        if "URL" in result:
            metadata["url"] = result["URL"]
        else:
            metadata["url"] = f"https://doi.org/{doi}"

        # License
        if "license" in result and result["license"]:
            licenses = []
            for lic in result["license"]:
                if "URL" in lic:
                    licenses.append(lic["URL"])
            if licenses:
                metadata["license"] = licenses[0] if len(licenses) == 1 else licenses

        return metadata

    except ImportError:
        logger.warning(
            "crossref-commons package not installed. Install with: pip install crossref-commons"
        )
        return None
    except Exception as e:
        logger.debug(f"CrossRef API error for DOI {doi}: {e}")
        return None


def get_datacite_metadata(doi: str) -> dict | None:
    """
    Retrieve metadata from DataCite API.

    Args:
        doi: DOI string (e.g., "10.5281/zenodo.4593540")

    Returns:
        Dictionary with metadata fields or None if retrieval fails
    """
    try:
        import requests

        # Use DataCite REST API (public, no authentication required)
        api_url = f"https://api.datacite.org/dois/{doi}"
        response = requests.get(api_url, timeout=10)

        if response.status_code != 200:
            logger.debug(
                f"DataCite API returned status {response.status_code} for DOI {doi}"
            )
            return None

        result = response.json()

        if not result or "data" not in result:
            return None

        data = result["data"]
        attributes = data.get("attributes", {})

        metadata = {
            "source": "DataCite",
            "doi": doi,
        }

        # Title
        titles = attributes.get("titles", [])
        if titles and len(titles) > 0:
            metadata["title"] = titles[0].get("title", "")

        # Authors (creators in DataCite)
        creators = attributes.get("creators", [])
        if creators:
            authors = []
            for creator in creators:
                if "name" in creator:
                    authors.append(creator["name"])
                elif "givenName" in creator and "familyName" in creator:
                    authors.append(f"{creator['givenName']} {creator['familyName']}")
                elif "familyName" in creator:
                    authors.append(creator["familyName"])
            if authors:
                metadata["authors"] = authors

        # Publisher
        if "publisher" in attributes:
            if isinstance(attributes["publisher"], dict):
                metadata["publisher"] = attributes["publisher"].get("name", "")
            else:
                metadata["publisher"] = attributes["publisher"]

        # Publication year
        if "publicationYear" in attributes:
            try:
                metadata["publication_year"] = int(attributes["publicationYear"])
            except (ValueError, TypeError):
                metadata["publication_year"] = attributes["publicationYear"]

        # URL
        if "url" in attributes:
            metadata["url"] = attributes["url"]
        else:
            metadata["url"] = f"https://doi.org/{doi}"

        # Rights/License
        rights_list = attributes.get("rightsList", [])
        if rights_list:
            licenses = []
            for rights in rights_list:
                if "rightsUri" in rights:
                    licenses.append(rights["rightsUri"])
                elif "rights" in rights:
                    licenses.append(rights["rights"])
            if licenses:
                metadata["license"] = licenses[0] if len(licenses) == 1 else licenses

        return metadata

    except Exception as e:
        logger.debug(f"DataCite API error for DOI {doi}: {e}")
        return None


def get_external_metadata(identifier: str, method: str = "auto") -> list[dict]:
    """
    Retrieve external metadata for a DOI from CrossRef and/or DataCite.

    This function attempts to extract a DOI from the identifier and then
    queries metadata sources based on the specified method.

    Args:
        identifier: DOI string, DOI URL, or other identifier containing a DOI
        method: Method for retrieving metadata:
            - "auto" (default): Try CrossRef first, then DataCite if CrossRef fails
            - "all": Query all sources and return all results
            - "crossref": Query CrossRef only
            - "datacite": Query DataCite only

    Returns:
        List of metadata dictionaries (one per source). Empty list if retrieval fails.

    Example:
        >>> metadata = get_external_metadata("10.5281/zenodo.4593540", method="auto")
        >>> print(metadata[0]["title"])
        >>> print(metadata[0]["authors"])

        >>> all_metadata = get_external_metadata("10.5281/zenodo.4593540", method="all")
        >>> for source_metadata in all_metadata:
        >>>     print(source_metadata["source"], source_metadata["title"])
    """
    # Extract DOI from identifier
    doi = extract_doi_from_string(identifier)
    if not doi:
        logger.debug(f"No DOI found in identifier: {identifier}")
        return []

    logger.debug(f"Retrieving external metadata for DOI: {doi} using method: {method}")

    results = []

    if method == "auto":
        # Try CrossRef first (faster and more common for academic publications)
        metadata = get_crossref_metadata(doi)
        if metadata:
            logger.info(f"Retrieved metadata from CrossRef for DOI: {doi}")
            results.append(metadata)
        else:
            # Fall back to DataCite (common for datasets and research data)
            metadata = get_datacite_metadata(doi)
            if metadata:
                logger.info(f"Retrieved metadata from DataCite for DOI: {doi}")
                results.append(metadata)

    elif method == "all":
        # Query all sources
        crossref_metadata = get_crossref_metadata(doi)
        if crossref_metadata:
            logger.info(f"Retrieved metadata from CrossRef for DOI: {doi}")
            results.append(crossref_metadata)

        datacite_metadata = get_datacite_metadata(doi)
        if datacite_metadata:
            logger.info(f"Retrieved metadata from DataCite for DOI: {doi}")
            results.append(datacite_metadata)

    elif method == "crossref":
        # Query CrossRef only
        metadata = get_crossref_metadata(doi)
        if metadata:
            logger.info(f"Retrieved metadata from CrossRef for DOI: {doi}")
            results.append(metadata)

    elif method == "datacite":
        # Query DataCite only
        metadata = get_datacite_metadata(doi)
        if metadata:
            logger.info(f"Retrieved metadata from DataCite for DOI: {doi}")
            results.append(metadata)

    if not results:
        logger.warning(
            f"Could not retrieve external metadata for DOI: {doi} using method: {method}"
        )

    return results
