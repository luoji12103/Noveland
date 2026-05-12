from __future__ import annotations

from typing import Any

import httpx
from noveland.providers.adapters.speech_common import SpeechAdapterInput, SpeechAdapterResult

OPENAI_API_BASE_URL = "https://api.openai.com/v1"


class OpenAISpeechAdapterError(RuntimeError):
    pass


class OpenAISpeechAdapter:
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
        operation = str(request_json.get("operation") or "").lower()
        if operation == "stt" or media_inputs:
            return self._transcribe(
                base_url=base_url,
                auth_ref=auth_ref,
                config_json=config_json,
                default_params_json=default_params_json,
                request_json=request_json,
                media_inputs=_speech_inputs(media_inputs),
            )
        return self._speech(
            base_url=base_url,
            auth_ref=auth_ref,
            config_json=config_json,
            default_params_json=default_params_json,
            input_text=input_text,
            input_json=input_json,
            request_json=request_json,
        )

    def _speech(
        self,
        *,
        base_url: str | None,
        auth_ref: str | None,
        config_json: dict[str, Any],
        default_params_json: dict[str, Any],
        input_text: str | None,
        input_json: dict[str, Any],
        request_json: dict[str, Any],
    ) -> SpeechAdapterResult:
        text = input_text or request_json.get("text") or input_json.get("text")
        if not isinstance(text, str) or text.strip() == "":
            raise OpenAISpeechAdapterError("OpenAI TTS requires text")
        payload = {**default_params_json}
        payload.setdefault("model", "gpt-4o-mini-tts")
        payload.setdefault("voice", _voice(request_json.get("provider_voice_id")) or "alloy")
        payload["input"] = text
        instructions = _instructions(request_json.get("style_json"))
        if instructions is not None:
            payload["instructions"] = instructions
        if request_json.get("output_format") is not None:
            payload["response_format"] = request_json["output_format"]
        with httpx.Client(timeout=float(config_json.get("timeout_seconds", 60))) as client:
            response = client.post(
                _endpoint(base_url, "/audio/speech"),
                headers={"Authorization": f"Bearer {_api_key(auth_ref, config_json)}"},
                json=payload,
            )
        response.raise_for_status()
        output_format = str(request_json.get("output_format") or "wav")
        return SpeechAdapterResult(
            output_text="speech audio generated",
            output_json={"media": "audio", "output_format": output_format},
            raw_response_json={"content_type": response.headers.get("content-type")},
            media_bytes=response.content,
            media_mime_type=_audio_mime(output_format),
            media_filename=f"openai-speech.{_audio_ext(output_format)}",
        )

    def _transcribe(
        self,
        *,
        base_url: str | None,
        auth_ref: str | None,
        config_json: dict[str, Any],
        default_params_json: dict[str, Any],
        request_json: dict[str, Any],
        media_inputs: list[SpeechAdapterInput],
    ) -> SpeechAdapterResult:
        if not media_inputs:
            raise OpenAISpeechAdapterError("OpenAI STT requires audio input")
        audio = media_inputs[0]
        data = {**default_params_json}
        data.setdefault("model", "gpt-4o-transcribe")
        if request_json.get("language") is not None:
            data["language"] = request_json["language"]
        if request_json.get("response_format") is not None:
            data["response_format"] = request_json["response_format"]
        if request_json.get("timestamps") and str(data.get("model")) == "whisper-1":
            data["response_format"] = "verbose_json"
            data["timestamp_granularities[]"] = ["segment"]
        with httpx.Client(timeout=float(config_json.get("timeout_seconds", 60))) as client:
            response = client.post(
                _endpoint(base_url, "/audio/transcriptions"),
                headers={"Authorization": f"Bearer {_api_key(auth_ref, config_json)}"},
                data=data,
                files={"file": (audio.filename, audio.data, audio.mime_type)},
            )
        response.raise_for_status()
        raw = response.json()
        text = raw.get("text")
        transcript = text if isinstance(text, str) else ""
        output_json: dict[str, Any] = {"transcript_text": transcript}
        if isinstance(raw.get("segments"), list):
            output_json["segments"] = raw["segments"]
        return SpeechAdapterResult(
            output_text=transcript,
            output_json=output_json,
            raw_response_json=raw,
        )


def _endpoint(base_url: str | None, path: str) -> str:
    return f"{(base_url or OPENAI_API_BASE_URL).rstrip('/')}{path}"


def _api_key(auth_ref: str | None, config_json: dict[str, Any]) -> str:
    del config_json
    api_key = auth_ref
    if not isinstance(api_key, str) or api_key.strip() == "":
        raise OpenAISpeechAdapterError("OpenAI speech adapter requires resolved auth_ref")
    return api_key


def _voice(value: object) -> str | dict[str, str] | None:
    if not isinstance(value, str) or value.strip() == "":
        return None
    if value.startswith("voice_"):
        return {"id": value}
    return value


def _audio_ext(output_format: str) -> str:
    return "mp3" if output_format == "mp3" else output_format


def _audio_mime(output_format: str) -> str:
    if output_format == "aac":
        return "audio/aac"
    if output_format == "flac":
        return "audio/flac"
    if output_format == "mp3":
        return "audio/mpeg"
    if output_format in {"ogg", "opus"}:
        return "audio/ogg"
    if output_format == "pcm":
        return "audio/pcm"
    if output_format == "webm":
        return "audio/webm"
    return "audio/wav"


def _instructions(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict) or not value:
        return None
    for key in ("instructions", "director_mode", "style_prompt"):
        item = value.get(key)
        if isinstance(item, str) and item.strip():
            return item
    return str(value)


def _speech_inputs(value: object) -> list[SpeechAdapterInput]:
    if isinstance(value, list) and all(isinstance(item, SpeechAdapterInput) for item in value):
        return value
    return []
