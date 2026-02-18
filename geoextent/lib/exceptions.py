"""Custom exceptions for geoextent."""


class DownloadSizeExceeded(Exception):
    """Raised when a download exceeds the configured size limit.

    Attributes:
        estimated_size: Estimated size in bytes of the download
        max_size: Current size limit in bytes
        provider: Name of the content provider
    """

    def __init__(self, estimated_size, max_size, provider):
        self.estimated_size = estimated_size
        self.max_size = max_size
        self.provider = provider
        super().__init__(
            f"{provider}: estimated download size {estimated_size:,} bytes "
            f"exceeds limit of {max_size:,} bytes"
        )
