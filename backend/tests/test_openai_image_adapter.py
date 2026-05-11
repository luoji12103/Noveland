from __future__ import annotations

import base64
from collections.abc import Callable
from typing import cast

import httpx
import pytest
from noveland.providers.adapters.openai_image import ImageAdapterInput, OpenAIImageAdapter


def test_openai_image_adapter_maps_generation_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = request.content
        return httpx.Response(200, json={"data": [{"b64_json": _b64(b"png-bytes")}]})

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    result = OpenAIImageAdapter().execute(
        base_url="https://api.example.test/v1",
        auth_ref="sk-test",
        config_json={},
        default_params_json={"model": "gpt-image-2"},
        input_text="draw",
        input_json={},
        request_json={"size": "1024x1024", "output_format": "png"},
    )

    assert captured["url"] == "https://api.example.test/v1/images/generations"
    assert b'"prompt":"draw"' in cast(bytes, captured["json"])
    assert result.media_bytes == b"png-bytes"
    assert result.media_mime_type == "image/png"


def test_openai_image_adapter_maps_edit_request(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["content_type"] = request.headers["content-type"]
        body = request.content
        captured["body"] = body
        return httpx.Response(200, json={"data": [{"b64_json": _b64(b"edited")}]})

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    result = OpenAIImageAdapter().execute(
        base_url="https://api.example.test/v1",
        auth_ref="sk-test",
        config_json={},
        default_params_json={"model": "gpt-image-2"},
        input_text="edit",
        input_json={},
        request_json={"operation": "edit"},
        media_inputs=[
            ImageAdapterInput(
                filename="input.png",
                data=b"image",
                mime_type="image/png",
            )
        ],
    )

    assert captured["url"] == "https://api.example.test/v1/images/edits"
    assert "multipart/form-data" in str(captured["content_type"])
    assert b'name="prompt"' in cast(bytes, captured["body"])
    assert b"input.png" in cast(bytes, captured["body"])
    assert result.media_bytes == b"edited"


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _client_factory(
    handler: Callable[[httpx.Request], httpx.Response],
) -> Callable[..., httpx.Client]:
    original_client = httpx.Client

    def create_client(**_: object) -> httpx.Client:
        return original_client(transport=httpx.MockTransport(handler))

    return create_client
