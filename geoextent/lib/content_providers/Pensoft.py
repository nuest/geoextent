import json
import re
import logging
from bs4 import BeautifulSoup
from requests import HTTPError
from .providers import DoiProvider
from .. import helpfunctions as hf
from ..extent import *


class Pensoft(DoiProvider):
    """
    Content provider for Pensoft journals (e.g., Biodiversity Data Journal).

    Extracts geographic metadata from JSON-LD structured data embedded in
    article HTML pages, specifically from the contentLocation property.

    Supported input formats:
    - Plain DOIs: 10.3897/BDJ.2.e1068
    - DOI URLs: https://doi.org/10.3897/BDJ.2.e1068
    - Direct article URLs: https://bdj.pensoft.net/article/1068/
    """

    def __init__(self):
        super().__init__()
        self.log = logging.getLogger("geoextent")
        self.host = {
            "hostname": [
                "https://bdj.pensoft.net/article/",
                "http://bdj.pensoft.net/article/",
                # Add other Pensoft journals as needed
                "https://zookeys.pensoft.net/article/",
                "http://zookeys.pensoft.net/article/",
                "https://phytokeys.pensoft.net/article/",
                "http://phytokeys.pensoft.net/article/",
                "https://neobiota.pensoft.net/article/",
                "http://neobiota.pensoft.net/article/",
            ],
            "api": None,  # Pensoft doesn't have a direct API, we parse HTML
        }
        self.reference = None
        self.article_id = None
        self.name = "Pensoft"
        self.throttle = False

    def validate_provider(self, reference):
        """
        Validate if the reference is a supported Pensoft journal article.

        Supports:
        1. DOIs with Pensoft pattern (10.3897/...)
        2. Direct Pensoft article URLs
        3. Generic DOI URLs that resolve to Pensoft
        """
        self.reference = reference
        url = self.get_url

        # Check for direct Pensoft URLs
        if any([url.startswith(p) for p in self.host["hostname"]]):
            # Extract article ID from URL
            # Pattern: https://bdj.pensoft.net/article/1068/
            clean_url = url.rstrip("/")
            self.article_id = clean_url.rsplit("/", maxsplit=1)[1]
            return True

        # Check for Pensoft DOI pattern
        pensoft_doi_pattern = re.compile(
            r"(?:(?:https?://)?(?:dx\.)?doi\.org/)?(?:doi:)?(10\.3897/.+)$",
            flags=re.I
        )
        match = pensoft_doi_pattern.match(reference)
        if match:
            # This is a Pensoft DOI, resolve it to get article URL
            doi = match.group(1)
            try:
                resp = self._request(f"https://doi.org/{doi}")
                resolved_url = resp.url
                # Check if it resolved to a Pensoft journal
                if any([resolved_url.startswith(p) for p in self.host["hostname"]]):
                    clean_url = resolved_url.rstrip("/")
                    self.article_id = clean_url.rsplit("/", maxsplit=1)[1]
                    return True
            except HTTPError:
                pass

        return False

    def download_record(self):
        """
        Download and parse the Pensoft article HTML to extract geographic metadata.

        Returns:
            dict: Record data with geographic coordinates extracted from JSON-LD
        """
        if not self.article_id:
            raise ValueError("No article ID available for download")

        # Construct the article URL
        # For now, we'll assume BDJ, but this could be enhanced to detect journal type
        article_url = f"https://bdj.pensoft.net/article/{self.article_id}/"

        try:
            response = self._request(article_url, throttle=self.throttle)
            html_content = response.text

            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract JSON-LD structured data
            json_ld_scripts = soup.find_all('script', type='application/ld+json')

            record_data = {
                'id': self.article_id,
                'url': article_url,
                'coordinates': [],
                'title': None,
                'doi': None,
                'json_ld_data': []
            }

            # Extract title from HTML
            title_element = soup.find('title')
            if title_element:
                record_data['title'] = title_element.get_text().strip()

            # Process each JSON-LD script
            for script in json_ld_scripts:
                try:
                    json_data = json.loads(script.string)
                    record_data['json_ld_data'].append(json_data)

                    # Extract DOI if available
                    if isinstance(json_data, dict) and 'identifier' in json_data:
                        identifier = json_data['identifier']
                        if isinstance(identifier, list):
                            for ident in identifier:
                                if isinstance(ident, dict) and ident.get('name') == 'DOI':
                                    record_data['doi'] = ident.get('value')
                        elif isinstance(identifier, dict) and identifier.get('name') == 'DOI':
                            record_data['doi'] = identifier.get('value')

                    # Extract geographic coordinates from contentLocation
                    if isinstance(json_data, dict) and 'contentLocation' in json_data:
                        content_location = json_data['contentLocation']
                        coordinates = self._extract_coordinates(content_location)
                        record_data['coordinates'].extend(coordinates)

                except json.JSONDecodeError as e:
                    self.log.warning(f"Failed to parse JSON-LD in article {self.article_id}: {e}")
                    continue

            self.log.info(f"Successfully downloaded Pensoft article {self.article_id} with {len(record_data['coordinates'])} coordinates")
            return record_data

        except HTTPError as e:
            self.log.error(f"Failed to download Pensoft article {self.article_id}: {e}")
            raise

    def _extract_coordinates(self, content_location):
        """
        Extract coordinate pairs from the contentLocation JSON-LD data.

        Args:
            content_location: The contentLocation value from JSON-LD

        Returns:
            list: List of (longitude, latitude) tuples
        """
        coordinates = []

        if not content_location:
            return coordinates

        # Handle different structures of contentLocation
        if isinstance(content_location, list):
            for location in content_location:
                coords = self._extract_coordinates_from_location(location)
                coordinates.extend(coords)
        else:
            coords = self._extract_coordinates_from_location(content_location)
            coordinates.extend(coords)

        return coordinates

    def _extract_coordinates_from_location(self, location):
        """
        Extract coordinates from a single location object.

        Args:
            location: A location object from contentLocation

        Returns:
            list: List of (longitude, latitude) tuples
        """
        coordinates = []

        if not isinstance(location, dict):
            return coordinates

        # Look for direct latitude/longitude properties
        if 'latitude' in location and 'longitude' in location:
            try:
                lat = float(location['latitude'])
                lon = float(location['longitude'])
                coordinates.append((lon, lat))  # GeoJSON format: [longitude, latitude]
            except (ValueError, TypeError):
                self.log.warning(f"Invalid coordinate values: lat={location['latitude']}, lon={location['longitude']}")

        # Look for geo property with GeoCoordinates
        if 'geo' in location:
            geo = location['geo']
            if isinstance(geo, dict) and geo.get('@type') == 'GeoCoordinates':
                if 'latitude' in geo and 'longitude' in geo:
                    try:
                        lat = float(geo['latitude'])
                        lon = float(geo['longitude'])
                        coordinates.append((lon, lat))
                    except (ValueError, TypeError):
                        self.log.warning(f"Invalid geo coordinate values: lat={geo['latitude']}, lon={geo['longitude']}")
            elif isinstance(geo, list):
                for geo_item in geo:
                    if isinstance(geo_item, dict) and geo_item.get('@type') == 'GeoCoordinates':
                        if 'latitude' in geo_item and 'longitude' in geo_item:
                            try:
                                lat = float(geo_item['latitude'])
                                lon = float(geo_item['longitude'])
                                coordinates.append((lon, lat))
                            except (ValueError, TypeError):
                                self.log.warning(f"Invalid geo coordinate values: lat={geo_item['latitude']}, lon={geo_item['longitude']}")

        return coordinates

    def download(self, folder, throttle=False, download_data=True, show_progress=True, max_size_bytes=None, max_download_method="ordered", max_download_method_seed=None):
        """
        Download geographic data from Pensoft article as GeoJSON file.

        Args:
            folder: Directory to save the generated GeoJSON file
            throttle: Whether to throttle requests (not used for Pensoft)
            download_data: Whether to extract geographic data
            show_progress: Whether to show progress (not used for Pensoft)
            max_size_bytes: Size limit (not applicable for Pensoft)
            max_download_method: Download method (not applicable for Pensoft)
            max_download_method_seed: Seed for download method (not applicable for Pensoft)
        """
        import os

        self.throttle = throttle

        if not download_data:
            self.log.warning(
                "Pensoft provider extracts geographic coordinates from article HTML. "
                "Using download_data=False will skip coordinate extraction."
            )
            return

        if not self.article_id:
            raise ValueError("No article ID available for download")

        self.log.debug(f"Extracting geographic data from Pensoft article {self.article_id}")

        try:
            # Get the GeoJSON content
            geojson_content = self.get_file_content(self.article_id)

            if not geojson_content:
                self.log.warning(f"No geographic coordinates found in Pensoft article {self.article_id}")
                return

            # Create the output file
            os.makedirs(folder, exist_ok=True)
            output_filename = f"pensoft_article_{self.article_id}_coordinates.geojson"
            output_path = os.path.join(folder, output_filename)

            # Write the GeoJSON file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(geojson_content)

            self.log.info(f"Successfully saved Pensoft geographic data to {output_path}")

        except Exception as e:
            self.log.error(f"Failed to download Pensoft article {self.article_id}: {e}")
            raise

    def get_file_content(self, record_id, key="", file_types=[], **kwargs):
        """
        Get file content from Pensoft article.

        For Pensoft, we return the geographic coordinates as a GeoJSON-like structure.
        """
        record_data = self.download_record()

        if not record_data['coordinates']:
            self.log.warning(f"No geographic coordinates found in Pensoft article {record_id}")
            return None

        # Convert coordinates to GeoJSON format
        features = []
        for i, (lon, lat) in enumerate(record_data['coordinates']):
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "properties": {
                    "id": i,
                    "source": "Pensoft",
                    "article_id": record_id,
                    "doi": record_data.get('doi'),
                    "title": record_data.get('title')
                }
            }
            features.append(feature)

        geojson = {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {
                    "name": "EPSG:4326"
                }
            },
            "features": features,
            "properties": {
                "source": "Pensoft",
                "article_id": record_id,
                "total_coordinates": len(record_data['coordinates'])
            }
        }

        return json.dumps(geojson, indent=2)