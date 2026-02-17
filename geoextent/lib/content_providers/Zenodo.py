import logging
import re

from .InvenioRDM import InvenioRDM, INVENIORDM_INSTANCES


class Zenodo(InvenioRDM):
    """Zenodo content provider — thin subclass of InvenioRDM.

    Zenodo migrated to InvenioRDM in Oct 2023. This subclass handles
    Zenodo-specific patterns (legacy /record/ URLs) while inheriting
    all InvenioRDM download and metadata logic.
    """

    doi_prefixes = ("10.5281/zenodo",)

    @classmethod
    def provider_info(cls):
        return {
            "name": "Zenodo",
            "description": "Zenodo is a free and open digital archive built by CERN and OpenAIRE, enabling researchers to share and preserve research output in any size, format and from all fields of research. It assigns persistent DOIs to all submissions and stores data in the CERN Data Center for long-term preservation.",
            "website": "https://zenodo.org/",
            "supported_identifiers": [
                "https://zenodo.org/records/{record_id}",
                "https://zenodo.org/record/{record_id}",
                "https://doi.org/10.5281/zenodo.{record_id}",
                "10.5281/zenodo.{record_id}",
            ],
            "doi_prefix": "10.5281/zenodo",
            "examples": [
                "https://doi.org/10.5281/zenodo.4593540",
                "10.5281/zenodo.4593540",
            ],
        }

    def __init__(self):
        super().__init__()
        self.name = "Zenodo"
        self._instance_config = INVENIORDM_INSTANCES["zenodo.org"]
        self.host = {
            "hostname": self._instance_config["hostnames"],
            "api": self._instance_config["api"],
        }

    def validate_provider(self, reference):
        """Zenodo-specific validation: only matches zenodo.org URLs and DOIs.

        Does NOT call super().validate_provider() to avoid matching other
        InvenioRDM instances (CaltechDATA, TU Wien, etc.).
        """
        self.reference = reference
        url = self.get_url

        # Check against Zenodo hostnames only
        if any(url.startswith(p) for p in self.host["hostname"]):
            clean_url = url.rstrip("/")
            self.record_id = clean_url.rsplit("/", maxsplit=1)[1]
            return True

        # Zenodo-specific: legacy pattern https://zenodo.org/record/(\d+)$
        zenodo_pattern = re.compile(r"https://zenodo\.org/record/(\d+)$", flags=re.I)
        match = zenodo_pattern.match(reference)
        if match:
            self.record_id = match.group(1)
            return True

        return False
