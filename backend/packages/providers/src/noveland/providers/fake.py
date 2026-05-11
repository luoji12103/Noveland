from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from noveland.providers.contracts import ProviderKind


@dataclass(frozen=True, slots=True)
class FakeProviderResult:
    output_text: str | None
    output_json: dict[str, Any]
    raw_response_json: dict[str, Any]
    media_bytes: bytes | None = None
    media_mime_type: str | None = None
    media_filename: str | None = None


class FakeProviderAdapter:
    def execute(
        self,
        provider_kind: ProviderKind,
        *,
        input_text: str | None,
        input_json: dict[str, Any],
        request_json: dict[str, Any],
    ) -> FakeProviderResult:
        if provider_kind == ProviderKind.TEXT_GENERATION:
            output = f"fake text: {input_text or input_json.get('prompt') or 'ok'}"
            return FakeProviderResult(
                output_text=output,
                output_json={"text": output},
                raw_response_json={"provider": "fake", "output": output},
            )
        if provider_kind == ProviderKind.IMAGE_GENERATION:
            data = _fake_png_bytes()
            return FakeProviderResult(
                output_text="fake image generated",
                output_json={"media": "image"},
                raw_response_json={"provider": "fake", "media": "image/png"},
                media_bytes=data,
                media_mime_type="image/png",
                media_filename="fake-image.png",
            )
        if provider_kind == ProviderKind.TEXT_TO_SPEECH:
            data = _fake_wav_bytes()
            return FakeProviderResult(
                output_text="fake speech audio generated",
                output_json={"media": "audio"},
                raw_response_json={"provider": "fake", "media": "audio/wav"},
                media_bytes=data,
                media_mime_type="audio/wav",
                media_filename="fake-speech.wav",
            )
        if provider_kind == ProviderKind.SPEECH_TO_TEXT:
            transcript = request_json.get("transcript") or input_text or "fake transcript"
            return FakeProviderResult(
                output_text=str(transcript),
                output_json={"transcript_text": str(transcript)},
                raw_response_json={"provider": "fake", "transcript_text": str(transcript)},
            )
        return FakeProviderResult(
            output_text="fake provider executed",
            output_json={"ok": True},
            raw_response_json={"provider": "fake", "ok": True},
        )


def _fake_png_bytes() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
        b"\x1f\x15\xc4\x89"
        b"\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe"
        b"\xdc\xccY\xe7"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _fake_wav_bytes() -> bytes:
    data = b"\x00\x00\x00\x00"
    return (
        b"RIFF"
        + (36 + len(data)).to_bytes(4, "little")
        + b"WAVEfmt "
        + (16).to_bytes(4, "little")
        + (1).to_bytes(2, "little")
        + (1).to_bytes(2, "little")
        + (8000).to_bytes(4, "little")
        + (8000).to_bytes(4, "little")
        + (1).to_bytes(2, "little")
        + (8).to_bytes(2, "little")
        + b"data"
        + len(data).to_bytes(4, "little")
        + data
    )
