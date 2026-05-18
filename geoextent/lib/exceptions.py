"""Custom exceptions for geoextent."""


class CloudflareBlockedError(Exception):
    """Raised when a content provider is blocked by Cloudflare protection.

    Lets callers (and tests) distinguish a Cloudflare challenge from a
    genuine "page does not exist / has no metadata" outcome so they can
    skip rather than fail on transient blocking.

    Attributes:
        url: The URL that was blocked
        provider: Name of the content provider
    """

    def __init__(self, url, provider, status_code=None):
        self.url = url
        self.provider = provider
        self.status_code = status_code
        suffix = f" (status={status_code})" if status_code is not None else ""
        super().__init__(f"{provider}: Cloudflare blocked request to {url}{suffix}")


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
