from __future__ import annotations

import re
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ALLOWED_RTSP_SCHEMES = {"rtsp", "rtsps"}
SENSITIVE_QUERY_KEYS = {
    "api_key",
    "apikey",
    "key",
    "password",
    "pass",
    "pwd",
    "secret",
    "token",
}

_RTSP_URL_RE = re.compile(r"rtsp[s]?://[^\s\"'<>]+", re.IGNORECASE)


def validate_rtsp_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("RTSP URL is required")

    cleaned = url.strip()
    parts = urlsplit(cleaned)
    scheme = (parts.scheme or "").lower()

    if scheme not in ALLOWED_RTSP_SCHEMES:
        raise ValueError("RTSP URL must start with rtsp:// or rtsps://")
    if not parts.hostname:
        raise ValueError("RTSP URL must include a host")

    return cleaned


def redact_rtsp_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return url

    try:
        parts = urlsplit(url)
    except Exception:
        return url

    if not parts.scheme or not parts.netloc:
        return url

    netloc = parts.netloc
    if "@" in netloc:
        creds, host = netloc.rsplit("@", 1)
        if ":" in creds:
            user, _ = creds.split(":", 1)
            creds = f"{user}:***"
        else:
            creds = "***"
        netloc = f"{creds}@{host}"

    query = parts.query
    if query:
        pairs = []
        for key, value in parse_qsl(query, keep_blank_values=True):
            if key.lower() in SENSITIVE_QUERY_KEYS:
                pairs.append((key, "***"))
            else:
                pairs.append((key, value))
        query = urlencode(pairs, doseq=True)

    return urlunsplit((parts.scheme, netloc, parts.path, query, parts.fragment))


def redact_rtsp_urls_in_text(text: str) -> str:
    if "rtsp" not in text.lower():
        return text

    def _replace(match: re.Match[str]) -> str:
        return redact_rtsp_url(match.group(0)) or match.group(0)

    return _RTSP_URL_RE.sub(_replace, text)
