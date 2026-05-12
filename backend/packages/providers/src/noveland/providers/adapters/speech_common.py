from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SpeechAdapterInput:
    filename: str
    data: bytes
    mime_type: str
    field_name: str = "file"


@dataclass(frozen=True, slots=True)
class SpeechAdapterResult:
    output_text: str | None
    output_json: dict[str, Any]
    raw_response_json: dict[str, Any]
    media_bytes: bytes | None = None
    media_mime_type: str | None = None
    media_filename: str | None = None
