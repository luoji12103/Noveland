from __future__ import annotations

from collections.abc import Iterable
from typing import Any

FORBIDDEN_SECURITY_TOKENS = (
    "authorization",
    "bearer",
    "base64",
    "bytes",
    "file://",
    "filesystem-path-marker",
    "local://",
    "media://",
    "prompt_snapshot",
    "raw_output",
    "raw_prompt",
    "resolved_secret",
    "sk-security-secret",
    "storage_uri",
)

FORBIDDEN_PAYLOAD_FIXTURE: dict[str, Any] = {
    "headers": {"Authorization": "Bearer sk-security-secret"},
    "storage_uri": "media://worlds/security/worldlines/primary/assets/object",
    "file_ref": "file://filesystem-path-marker",
    "raw_prompt": "raw_prompt marker",
    "raw_output": "raw_output marker",
    "encoded": {"base64": "bytes-marker"},
    "prompt_snapshot": {"id": "hidden"},
    "resolved_secret": "sk-security-secret",
}


def assert_no_forbidden_tokens(text: str, extra_tokens: Iterable[str] = ()) -> None:
    lowered = text.lower()
    for token in (*FORBIDDEN_SECURITY_TOKENS, *tuple(extra_tokens)):
        assert token.lower() not in lowered


def contains_forbidden_payload(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            _contains_forbidden_token(str(key)) or contains_forbidden_payload(nested)
            for key, nested in value.items()
        )
    if isinstance(value, list | tuple | set):
        return any(contains_forbidden_payload(item) for item in value)
    return _contains_forbidden_token(str(value))


def _contains_forbidden_token(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in FORBIDDEN_SECURITY_TOKENS)
