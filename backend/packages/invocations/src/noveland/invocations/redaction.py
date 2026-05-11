from __future__ import annotations

import hashlib
import json
from typing import Any

from noveland.invocations.contracts import InvocationRedactionStatus, RedactionMode


def checksum_text(value: str | None) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def checksum_json(value: Any) -> str | None:
    if value is None:
        return None
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def prompt_checksum(
    *,
    raw_prompt_text: str | None,
    raw_messages_json: Any,
    raw_request_json: Any,
) -> str:
    rendered = json.dumps(
        {
            "raw_prompt_text": raw_prompt_text,
            "raw_messages_json": raw_messages_json,
            "raw_request_json": raw_request_json,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def redacted_summary_text(value: str | None, mode: RedactionMode) -> str | None:
    if mode == RedactionMode.CLEAR_RAW_PAYLOADS:
        return None
    if mode == RedactionMode.CHECKSUM_ONLY:
        return None
    return value


def redaction_status_for_mode(mode: RedactionMode) -> InvocationRedactionStatus:
    if mode == RedactionMode.CLEAR_RAW_PAYLOADS:
        return InvocationRedactionStatus.REDACTED
    if mode == RedactionMode.CHECKSUM_ONLY:
        return InvocationRedactionStatus.CHECKSUM_ONLY
    return InvocationRedactionStatus.HIDDEN
