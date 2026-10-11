import re
from urllib.parse import urlparse

ALLOWED_HOSTS = {
    "www.amazon.com",
    "amazon.com",
    "www.amazon.co.uk",
    "www.amazon.ca",
    "www.amazon.de",
}

# Default marketplace used to build product URLs from ASINs.
AMAZON_BASE = "https://www.amazon.com"

ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")


class InvalidURLError(ValueError):
    pass


class InvalidASINError(ValueError):
    pass


def validate_asin(raw: str) -> str:
    """
    Accepts a 10-char ASIN (case-insensitive, whitespace stripped).
    Returns the uppercase ASIN or raises InvalidASINError.
    """
    if raw is None:
        raise InvalidASINError("ASIN is missing.")
    asin = raw.strip().upper()
    if not ASIN_RE.match(asin):
        raise InvalidASINError(
            f"Invalid ASIN: '{raw.strip()}'. Must be 10 letters/digits."
        )
    return asin


def asin_to_url(asin: str) -> str:
    """Build the canonical product URL for an ASIN."""
    return f"{AMAZON_BASE}/dp/{asin}"


def validate_amazon_url(url: str) -> str:
    """Kept for internal callers. Still useful if you re-enable URL input."""
    url = url.strip()
    if not url:
        raise InvalidURLError("URL is empty.")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError("URL must start with http:// or https://")

    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise InvalidURLError(
            f"Only Amazon domains are allowed. Got: {host or 'unknown'}"
        )

    if parsed.username or parsed.password:
        raise InvalidURLError("URL must not contain credentials.")
    if parsed.port and parsed.port not in (80, 443):
        raise InvalidURLError("URL must use standard ports.")

    return url