"""Tracked links in one consistent UTM scheme.

``utm_source=<platform>&utm_medium=influencer&utm_campaign=<campaign slug>&utm_content=<creator>``
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .errors import DataProblem

PLATFORMS = ("instagram", "tiktok", "youtube", "snapchat")
UTM_MEDIUM = "influencer"
_NORDIC = str.maketrans({"æ": "ae", "Æ": "ae", "ø": "o", "Ø": "o", "å": "a", "Å": "a"})
_NOT_SLUG = re.compile(r"[^a-z0-9_]+")


def slugify(text: object, *, separator: str = "-") -> str:
    """Lowercase ASCII slug; Norwegian letters are transliterated (æ→ae, ø→o, å→a)."""
    value = str(text or "").translate(_NORDIC)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    value = value.lstrip("@")
    value = _NOT_SLUG.sub(separator, value)
    value = re.sub(re.escape(separator) + "+", separator, value)
    return value.strip(separator + "_")


def creator_token(handle: str | None, name: str | None = None) -> str:
    """The utm_content value for a creator: their handle (without @), else their name."""
    token = slugify(handle, separator="_") if handle else ""
    if not token:
        token = slugify(name, separator="_")
    if not token:
        raise DataProblem("A creator needs a handle or a name to build a tracked link.")
    return token


def utm_params(platform: str, campaign_slug: str, creator: str) -> dict[str, str]:
    """Return the four UTM parameters in a fixed order."""
    source = slugify(platform)
    if source not in PLATFORMS:
        raise DataProblem(f"Unknown platform '{platform}'. Use one of: {', '.join(PLATFORMS)}.")
    campaign = slugify(campaign_slug)
    if not campaign:
        raise DataProblem("The campaign needs a slug before tracked links can be built.")
    content = slugify(creator, separator="_")
    if not content:
        raise DataProblem("The creator token for utm_content is empty.")
    return {
        "utm_source": source,
        "utm_medium": UTM_MEDIUM,
        "utm_campaign": campaign,
        "utm_content": content,
    }


def build_tracked_url(landing_url: str, platform: str, campaign_slug: str, creator: str) -> str:
    """Append the UTM scheme to a landing page, keeping its other query parameters and fragment."""
    url = (landing_url or "").strip()
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise DataProblem("The landing page must be a full http:// or https:// address.")
    kept = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if not key.startswith("utm_")]
    query = urlencode(kept + list(utm_params(platform, campaign_slug, creator).items()))
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", query, parts.fragment))
