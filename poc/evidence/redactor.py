from __future__ import annotations

import json
import re
from collections.abc import Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from poc.contracts._serialization import JSONValue


REDACTED = "[REDACTED]"
REDACTED_PATH = "[REDACTED_PATH]"

_SENSITIVE_FIELD_PARTS = (
    "apikey",
    "accesstoken",
    "authorization",
    "secret",
    "credential",
    "password",
    "clientsecret",
    "refreshtoken",
    "idtoken",
    "cookie",
)
_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_WINDOWS_USER_PATH = re.compile(r'(?i)\b[A-Z]:\\Users\\[^\\/\s"\'<>]+(?:\\[^\s"\'<>]*)?')
_POSIX_USER_PATH = re.compile(r'(?<![A-Za-z0-9])/(?:home|Users|root)/[^/\s"\'<>]+(?:/[^\s"\'<>]*)?')
_HEADER_PATTERNS = (
    re.compile(r"(?im)(\bauthorization\s*[:=]\s*)([^\r\n]+)"),
    re.compile(r"(?im)(\bx-api-key\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^,;\s]+)"),
    re.compile(r"(?im)(\b(?:cookie|set-cookie)\s*[:=]\s*)([^\r\n]+)"),
    re.compile(r"(?im)(\b(?:[A-Z0-9_]*(?:API|PROVIDER)[_-]?KEY|[A-Z0-9_]*(?:TOKEN|SECRET|CREDENTIAL|PASSWORD))\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^,;\s]+)"),
)
_BEARER_TOKEN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")
_GITHUB_TOKEN = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")
_API_KEY_SHAPE = re.compile(
    r"\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{12,}|rk-[A-Za-z0-9_-]{12,}|"
    r"gsk_[A-Za-z0-9_-]{20,}|xai-[A-Za-z0-9_-]{20,}|"
    r"AIza[0-9A-Za-z_-]{20,}|hf_[A-Za-z0-9]{20,}|r8_[A-Za-z0-9]{20,})\b"
)


def _is_sensitive_field(name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", name.casefold())
    return any(part in normalized for part in _SENSITIVE_FIELD_PARTS)


def _is_secret_query_parameter(name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", name.casefold())
    return (
        normalized in {"key", "token", "secret", "signature", "auth", "password", "credential"}
        or any(part in normalized for part in _SENSITIVE_FIELD_PARTS)
        or normalized.endswith("signature")
    )


def _redact_url(url: str) -> str:
    trailing = ""
    while url and url[-1] in ".,;:!?)]}":
        trailing = url[-1] + trailing
        url = url[:-1]
    try:
        parts = urlsplit(url)
    except ValueError:
        return REDACTED + trailing
    netloc = parts.netloc
    if "@" in netloc:
        netloc = REDACTED + "@" + netloc.rsplit("@", 1)[1]
    query = [
        (name, REDACTED if _is_secret_query_parameter(name) else value)
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    sanitized = urlunsplit((parts.scheme, netloc, parts.path, urlencode(query), parts.fragment))
    return sanitized + trailing


def redact_string(value: str) -> str:
    sanitized = value
    for pattern in _HEADER_PATTERNS:
        sanitized = pattern.sub(lambda match: match.group(1) + REDACTED, sanitized)
    sanitized = _BEARER_TOKEN.sub("Bearer " + REDACTED, sanitized)
    sanitized = _GITHUB_TOKEN.sub(REDACTED, sanitized)
    sanitized = _API_KEY_SHAPE.sub(REDACTED, sanitized)
    sanitized = _URL_PATTERN.sub(lambda match: _redact_url(match.group(0)), sanitized)
    sanitized = _WINDOWS_USER_PATH.sub(REDACTED_PATH, sanitized)
    sanitized = _POSIX_USER_PATH.sub(REDACTED_PATH, sanitized)
    return sanitized


def redact_value(value: JSONValue) -> JSONValue:
    if isinstance(value, dict):
        sanitized: dict[str, JSONValue] = {}
        for key, item in value.items():
            if _is_sensitive_field(key):
                sanitized[key] = REDACTED
            else:
                sanitized[key] = redact_value(item)
        return sanitized
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        return redact_string(value)
    return value


def redacted_json_dumps(value: JSONValue) -> str:
    """Redact a JSON-compatible value before producing permanent JSON text."""
    return json.dumps(redact_value(value), sort_keys=True, ensure_ascii=True, separators=(",", ":"))
