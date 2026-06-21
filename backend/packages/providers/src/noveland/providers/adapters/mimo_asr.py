from __future__ import annotations

import base64
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
        endpoint = str(config_json.get("endpoint", "/v1/chat/completions"))
        request_format = str(
            config_json.get("request_format") or _infer_request_format(endpoint)
        )
        audio = inputs[0]
        headers = {"Authorization": f"Bearer {auth_ref}"} if auth_ref else {}
        with httpx.Client(timeout=float(config_json.get("timeout_seconds", 60))) as client:
            if request_format == "chat_completions":
                response = client.post(
                    f"{base_url.rstrip('/')}{endpoint}",
                    headers=headers,
                    json=_chat_completions_payload(
                        audio=audio,
                        default_params_json=default_params_json,
                        request_json=request_json,
                    ),
                )
            elif request_format == "multipart":
                response = client.post(
                    f"{base_url.rstrip('/')}{endpoint}",
                    headers=headers,
                    data={**default_params_json, "language": request_json.get("language")},
                    files={"file": (audio.filename, audio.data, audio.mime_type)},
                )
            else:
                raise MiMOASRAdapterError(
                    f"Unsupported MiMo ASR request_format: {request_format}"
                )
        response.raise_for_status()
        raw = _response_payload(response)
        transcript = _transcript_text(raw)
        return SpeechAdapterResult(
            output_text=transcript,
            output_json={"transcript_text": transcript},
            raw_response_json=raw,
        )


def _speech_inputs(value: object) -> list[SpeechAdapterInput]:
    if isinstance(value, list) and all(isinstance(item, SpeechAdapterInput) for item in value):
        return value
    return []


def _infer_request_format(endpoint: str) -> str:
    if endpoint.rstrip("/").endswith("/chat/completions"):
        return "chat_completions"
    return "multipart"


def _chat_completions_payload(
    *,
    audio: SpeechAdapterInput,
    default_params_json: dict[str, Any],
    request_json: dict[str, Any],
) -> dict[str, Any]:
    payload = dict(default_params_json)
    payload["messages"] = [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {"data": _audio_data_url(audio)},
                }
            ],
        }
    ]
    language = request_json.get("language")
    if language:
        payload["asr_options"] = {"language": language}
    return payload


def _audio_data_url(audio: SpeechAdapterInput) -> str:
    encoded = base64.b64encode(audio.data).decode("ascii")
    return f"data:{audio.mime_type};base64,{encoded}"


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


def _transcript_text(raw: dict[str, Any]) -> str:
    for key in ("text", "transcript", "transcript_text"):
        text = raw.get(key)
        if text is not None:
            return str(text)
    choices = raw.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if not isinstance(message, dict):
                continue
            content_text = _content_text(message.get("content"))
            if content_text is not None:
                return content_text
            audio = message.get("audio")
            if isinstance(audio, dict):
                for key in ("transcript", "text", "content"):
                    text = audio.get(key)
                    if text is not None:
                        return str(text)
    return ""


def _content_text(content: object) -> str | None:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        if parts:
            return "".join(parts)
    return None
