from __future__ import annotations

from typing import Any

import httpx
from noveland.providers.adapters.speech_common import SpeechAdapterInput, SpeechAdapterResult


class MiMOTTSAdapterError(RuntimeError):
    pass


class MiMOTTSAdapter:
    def execute(
        self,
        *,
        base_url: str | None,
        auth_ref: str | None,
        config_json: dict[str, Any],
        default_params_json: dict[str, Any],
        input_text: str | None,
        input_json: dict[str, Any],
        request_json: dict[str, Any],
        media_inputs: list[SpeechAdapterInput] | object | None = None,
    ) -> SpeechAdapterResult:
        if bool(config_json.get("dry_run", False)):
            return _dry_run("mimo-tts.wav")
        if base_url is None:
            raise MiMOTTSAdapterError(
                "MiMo TTS adapter requires base_url unless dry_run is enabled"
            )
        endpoint = str(config_json.get("endpoint", "/tts"))
        text = input_text or request_json.get("text") or input_json.get("text")
        payload = {
            **default_params_json,
            "text": text,
            "language": request_json.get("language"),
            "voice_id": request_json.get("provider_voice_id"),
            "style": request_json.get("style_json", {}),
            "output_format": request_json.get("output_format", "wav"),
        }
        headers = {"Authorization": f"Bearer {auth_ref}"} if auth_ref else {}
        with httpx.Client(timeout=float(config_json.get("timeout_seconds", 60))) as client:
            response = client.post(
                f"{base_url.rstrip('/')}{endpoint}",
                headers=headers,
                json=payload,
            )
        response.raise_for_status()
        output_format = str(request_json.get("output_format") or "wav")
        return SpeechAdapterResult(
            output_text="mimo speech audio generated",
            output_json={"media": "audio", "provider": "mimo_tts"},
            raw_response_json={"content_type": response.headers.get("content-type")},
            media_bytes=response.content,
            media_mime_type="audio/wav" if output_format == "wav" else "audio/mpeg",
            media_filename=f"mimo-tts.{output_format}",
        )


def _dry_run(filename: str) -> SpeechAdapterResult:
    data = (
        b"RIFF(\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
        b"\x01\x00\x01\x00@\x1f\x00\x00@\x1f\x00\x00"
        b"\x01\x00\x08\x00data\x04\x00\x00\x00\x00\x00\x00\x00"
    )
    return SpeechAdapterResult(
        output_text="mimo dry-run speech audio generated",
        output_json={"media": "audio", "dry_run": True},
        raw_response_json={"dry_run": True},
        media_bytes=data,
        media_mime_type="audio/wav",
        media_filename=filename,
    )
