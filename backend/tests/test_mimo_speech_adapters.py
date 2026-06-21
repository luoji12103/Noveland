from __future__ import annotations

from collections.abc import Callable
from typing import cast

import httpx
import pytest
from noveland.providers.adapters.gpt_sovits import GPTSoVITSAdapter
from noveland.providers.adapters.mimo_asr import MiMOASRAdapter
from noveland.providers.adapters.mimo_tts import MiMOTTSAdapter
from noveland.providers.adapters.omnivoice import OmniVoiceAdapter
from noveland.providers.adapters.speech_common import SpeechAdapterInput


def test_mimo_tts_adapter_maps_style_and_emotion(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = request.content
        captured["authorization"] = request.headers["authorization"]
        return httpx.Response(200, content=b"audio", headers={"content-type": "audio/wav"})

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    result = MiMOTTSAdapter().execute(
        base_url="https://mimo.example.test",
        auth_ref="mimo-secret",
        config_json={"endpoint": "/v2.5/tts"},
        default_params_json={"model": "mimo-v2.5-tts"},
        input_text="hello",
        input_json={},
        request_json={
            "language": "zh",
            "provider_voice_id": "voice-1",
            "style_json": {"emotion": "shy", "director_mode": "soft"},
            "output_format": "wav",
        },
    )

    assert captured["url"] == "https://mimo.example.test/v2.5/tts"
    assert captured["authorization"] == "Bearer mimo-secret"
    body = cast(bytes, captured["json"])
    assert b'"text":"hello"' in body
    assert b'"voice_id":"voice-1"' in body
    assert b'"emotion":"shy"' in body
    assert result.media_bytes == b"audio"
    assert result.media_mime_type == "audio/wav"


def test_mimo_asr_adapter_maps_audio_request(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.content
        captured["content_type"] = request.headers["content-type"]
        return httpx.Response(200, json={"transcript_text": "recognized"})

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    result = MiMOASRAdapter().execute(
        base_url="https://mimo.example.test",
        auth_ref=None,
        config_json={"endpoint": "/v2.5/asr"},
        default_params_json={"model": "mimo-v2.5-asr"},
        input_text=None,
        input_json={},
        request_json={"language": "ja"},
        media_inputs=[
            SpeechAdapterInput(
                filename="source.wav",
                data=b"wav",
                mime_type="audio/wav",
            )
        ],
    )

    assert captured["url"] == "https://mimo.example.test/v2.5/asr"
    assert "multipart/form-data" in str(captured["content_type"])
    body = cast(bytes, captured["body"])
    assert b"source.wav" in body
    assert b"mimo-v2.5-asr" in body
    assert result.output_text == "recognized"


def test_mimo_asr_adapter_accepts_plain_text_transcript_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="plain transcript",
            headers={"content-type": "text/plain"},
        )

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    result = MiMOASRAdapter().execute(
        base_url="https://mimo.example.test",
        auth_ref="mimo-secret",
        config_json={"endpoint": "/v2.5/asr"},
        default_params_json={"model": "mimo-v2.5-asr"},
        input_text=None,
        input_json={},
        request_json={"language": "ja"},
        media_inputs=[
            SpeechAdapterInput(
                filename="source.wav",
                data=b"wav",
                mime_type="audio/wav",
            )
        ],
    )

    assert result.output_text == "plain transcript"
    assert result.output_json == {"transcript_text": "plain transcript"}


@pytest.mark.parametrize(
    "adapter",
    [
        OmniVoiceAdapter(),
        GPTSoVITSAdapter(),
    ],
)
def test_configurable_tts_contract_adapters_support_dry_run(
    adapter: OmniVoiceAdapter | GPTSoVITSAdapter,
) -> None:
    result = adapter.execute(
        base_url=None,
        auth_ref=None,
        config_json={"dry_run": True},
        default_params_json={},
        input_text="hello",
        input_json={},
        request_json={},
    )

    assert result.media_bytes is not None
    assert result.media_filename == "mimo-tts.wav"
    assert result.media_mime_type == "audio/wav"


def _client_factory(
    handler: Callable[[httpx.Request], httpx.Response],
) -> Callable[..., httpx.Client]:
    original_client = httpx.Client

    def create_client(**_: object) -> httpx.Client:
        return original_client(transport=httpx.MockTransport(handler))

    return create_client
