from __future__ import annotations

from typing import Any

import httpx
from noveland.providers.adapters.speech_common import SpeechAdapterInput, SpeechAdapterResult


class MiMOASRAdapterError(RuntimeError):
    pass


class MiMOASRAdapter:
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
            transcript = str(request_json.get("transcript") or "mimo dry-run transcript")
            return SpeechAdapterResult(
                output_text=transcript,
                output_json={"transcript_text": transcript, "provider": "mimo_asr"},
                raw_response_json={"dry_run": True},
            )
        if base_url is None:
            raise MiMOASRAdapterError(
                "MiMo ASR adapter requires base_url unless dry_run is enabled"
            )
        inputs = _speech_inputs(media_inputs)
        if not inputs:
            raise MiMOASRAdapterError("MiMo ASR requires audio input")
        endpoint = str(config_json.get("endpoint", "/asr"))
        audio = inputs[0]
        data = {**default_params_json, "language": request_json.get("language")}
        headers = {"Authorization": f"Bearer {auth_ref}"} if auth_ref else {}
        with httpx.Client(timeout=float(config_json.get("timeout_seconds", 60))) as client:
            response = client.post(
                f"{base_url.rstrip('/')}{endpoint}",
                headers=headers,
                data=data,
                files={"file": (audio.filename, audio.data, audio.mime_type)},
            )
        response.raise_for_status()
        raw = _response_payload(response)
        text = raw.get("text") or raw.get("transcript") or raw.get("transcript_text")
        transcript = str(text or "")
        return SpeechAdapterResult(
            output_text=transcript,
            output_json={"transcript_text": transcript},
            raw_response_json=raw,
        )


def _speech_inputs(value: object) -> list[SpeechAdapterInput]:
    if isinstance(value, list) and all(isinstance(item, SpeechAdapterInput) for item in value):
        return value
    return []


def _response_payload(response: httpx.Response) -> dict[str, Any]:
    try:
        raw = response.json()
    except ValueError:
        return {
            "transcript_text": response.text.strip(),
            "content_type": response.headers.get("content-type"),
        }
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        return {"transcript_text": raw}
    return {"transcript_text": ""}
