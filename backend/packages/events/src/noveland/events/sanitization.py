from __future__ import annotations

import re
from typing import Any

WORLD_EVENT_PAYLOAD_FORBIDDEN_KEYS = {
    "api_key",
    "apikey",
    "auth_ref",
    "auth_refs",
    "authorization",
    "base64",
    "bearer_token",
    "bytes",
    "client_secret",
    "file_path",
    "filesystem_path",
    "password",
    "path",
    "payload_uri",
    "preview_uri",
    "private_key",
    "prompt_snapshot",
    "raw_bytes",
    "raw_output",
    "raw_prompt",
    "resolved_secret",
    "secret",
    "secret_ref",
    "secret_refs",
    "storage_uri",
    "thumbnail_uri",
    "token",
}
WORLD_EVENT_PAYLOAD_FORBIDDEN_KEY_MARKERS = {
    re.sub(r"[^a-z0-9]+", "", marker.lower())
    for marker in WORLD_EVENT_PAYLOAD_FORBIDDEN_KEYS
}
_WORLD_EVENT_PAYLOAD_EXACT_KEY_MARKERS = {
    "base64",
    "bytes",
    "password",
    "path",
    "secret",
    "token",
}
_WORLD_EVENT_PAYLOAD_SUBSTRING_KEY_MARKERS = (
    WORLD_EVENT_PAYLOAD_FORBIDDEN_KEY_MARKERS - _WORLD_EVENT_PAYLOAD_EXACT_KEY_MARKERS
)
WORLD_EVENT_PAYLOAD_FORBIDDEN_VALUE_RE = re.compile(
    r"(storage[_ -]?uri|payload[_ -]?uri|preview[_ -]?uri|thumbnail[_ -]?uri|"
    r"media://|object://|file://|s3://|gs://|/root/|/tmp/|base64,|"
    r"BEGIN PRIVATE KEY|sk-[A-Za-z0-9]|bearer\s+|authorization|"
    r"raw[_ -]?prompt|raw[_ -]?output|prompt[_ -]?snapshot|"
    r"file[_ -]?path|filesystem[_ -]?path)",
    re.IGNORECASE,
)
_OMIT_WORLD_EVENT_PAYLOAD_VALUE = object()


def sanitize_world_event_payload(value: Any) -> dict[str, Any]:
    sanitized = _sanitize_world_event_payload_value(value)
    return sanitized if isinstance(sanitized, dict) else {}


def _sanitize_world_event_payload_value(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_forbidden_world_event_payload_key(key_text):
                continue
            sanitized_item = _sanitize_world_event_payload_value(item)
            if sanitized_item is not _OMIT_WORLD_EVENT_PAYLOAD_VALUE:
                sanitized[key_text] = sanitized_item
        return sanitized
    if isinstance(value, list):
        sanitized_list: list[Any] = []
        for item in value:
            sanitized_item = _sanitize_world_event_payload_value(item)
            if sanitized_item is not _OMIT_WORLD_EVENT_PAYLOAD_VALUE:
                sanitized_list.append(sanitized_item)
        return sanitized_list
    if isinstance(value, tuple):
        sanitized_list = []
        for item in value:
            sanitized_item = _sanitize_world_event_payload_value(item)
            if sanitized_item is not _OMIT_WORLD_EVENT_PAYLOAD_VALUE:
                sanitized_list.append(sanitized_item)
        return sanitized_list
    if isinstance(value, str) and WORLD_EVENT_PAYLOAD_FORBIDDEN_VALUE_RE.search(value):
        return _OMIT_WORLD_EVENT_PAYLOAD_VALUE
    return value


def _is_forbidden_world_event_payload_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "", key.lower())
    return normalized in WORLD_EVENT_PAYLOAD_FORBIDDEN_KEY_MARKERS or any(
        marker and marker in normalized
        for marker in _WORLD_EVENT_PAYLOAD_SUBSTRING_KEY_MARKERS
    )
