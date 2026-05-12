from __future__ import annotations

from collections.abc import Callable
from typing import cast

import httpx
import pytest
from noveland.providers.adapters.openai_speech import OpenAISpeechAdapter
from noveland.providers.adapters.speech_common import SpeechAdapterInput


def test_openai_speech_adapter_maps_tts_request(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = request.content
        captured["authorization"] = request.headers["authorization"]
        return httpx.Response(200, content=b"audio-bytes", headers={"content-type": "audio/wav"})

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    result = OpenAISpeechAdapter().execute(
        base_url="https://api.example.test/v1",
        auth_ref="sk-test",
        config_json={},
        default_params_json={"model": "gpt-4o-mini-tts"},
        input_text="speak this",
        input_json={},
        request_json={
            "operation": "tts",
            "provider_voice_id": "voice_1234",
            "style_json": {"instructions": "soft and warm"},
            "output_format": "wav",
        },
    )

    assert captured["url"] == "https://api.example.test/v1/audio/speech"
    assert captured["authorization"] == "Bearer sk-test"
    body = cast(bytes, captured["json"])
    assert b'"model":"gpt-4o-mini-tts"' in body
    assert b'"input":"speak this"' in body
    assert b'"voice":{"id":"voice_1234"}' in body
    assert b'"instructions":"soft and warm"' in body
    assert b'"response_format":"wav"' in body
    assert result.media_bytes == b"audio-bytes"
    assert result.media_mime_type == "audio/wav"


def test_openai_speech_adapter_maps_stt_request(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.content
        captured["content_type"] = request.headers["content-type"]
        return httpx.Response(200, json={"text": "recognized", "segments": [{"start": 0}]})

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    result = OpenAISpeechAdapter().execute(
        base_url="https://api.example.test/v1",
        auth_ref=None,
        config_json={"api_key": "sk-from-config"},
        default_params_json={"model": "gpt-4o-transcribe"},
        input_text=None,
        input_json={},
        request_json={"operation": "stt", "language": "ja", "timestamps": True},
        media_inputs=[
            SpeechAdapterInput(
                filename="source.wav",
                data=b"wav-bytes",
                mime_type="audio/wav",
            )
        ],
    )

    assert captured["url"] == "https://api.example.test/v1/audio/transcriptions"
    assert "multipart/form-data" in str(captured["content_type"])
    body = cast(bytes, captured["body"])
    assert b'name="model"' in body
    assert b"gpt-4o-transcribe" in body
    assert b'name="language"' in body
    assert b"source.wav" in body
    assert b"timestamp_granularities" not in body
    assert result.output_text == "recognized"
    assert result.output_json["segments"] == [{"start": 0}]


def test_openai_speech_adapter_uses_whisper_timestamp_granularity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content
        return httpx.Response(200, json={"text": "recognized"})

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    OpenAISpeechAdapter().execute(
        base_url="https://api.example.test/v1",
        auth_ref="sk-test",
        config_json={},
        default_params_json={"model": "whisper-1"},
        input_text=None,
        input_json={},
        request_json={"operation": "stt", "timestamps": True},
        media_inputs=[
            SpeechAdapterInput(
                filename="source.wav",
                data=b"wav-bytes",
                mime_type="audio/wav",
            )
        ],
    )

    body = cast(bytes, captured["body"])
    assert b"timestamp_granularities" in body
    assert b"verbose_json" in body


def _client_factory(
    handler: Callable[[httpx.Request], httpx.Response],
) -> Callable[..., httpx.Client]:
    original_client = httpx.Client

    def create_client(**_: object) -> httpx.Client:
        return original_client(transport=httpx.MockTransport(handler))

    return create_client
