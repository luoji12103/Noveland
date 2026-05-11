from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest
from noveland.providers.adapters.comfyui import ComfyUIAdapter


def test_comfyui_adapter_dry_run_returns_image() -> None:
    result = ComfyUIAdapter().execute(
        base_url=None,
        auth_ref=None,
        config_json={"dry_run": True},
        default_params_json={},
        input_text="draw",
        input_json={},
        request_json={"size": "1024x1024"},
    )

    assert result.output_json == {"media": "image", "dry_run": True}
    assert result.media_mime_type == "image/png"
    assert result.media_bytes is not None


def test_comfyui_adapter_maps_template_and_fetches_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if request.url.path == "/prompt":
            assert b"mapped prompt" in request.content
            return httpx.Response(200, json={"prompt_id": "prompt-1"})
        if request.url.path == "/history/prompt-1":
            return httpx.Response(
                200,
                json={"prompt-1": {"outputs": {"9": {"images": [{"filename": "out.png"}]}}}},
            )
        if request.url.path == "/view":
            return httpx.Response(
                200,
                content=b"image-bytes",
                headers={"content-type": "image/png"},
            )
        raise AssertionError(str(request.url))

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    result = ComfyUIAdapter().execute(
        base_url="https://comfy.example.test",
        auth_ref=None,
        config_json={
            "workflow_template_json": {"nodes": {"1": {"inputs": {"text": ""}}}},
            "input_mapping_json": {"prompt": ["nodes", "1", "inputs", "text"]},
        },
        default_params_json={},
        input_text="mapped prompt",
        input_json={},
        request_json={},
    )

    assert requests == [
        "https://comfy.example.test/prompt",
        "https://comfy.example.test/history/prompt-1",
        "https://comfy.example.test/view?filename=out.png",
    ]
    assert result.media_bytes == b"image-bytes"


def _client_factory(
    handler: Callable[[httpx.Request], httpx.Response],
) -> Callable[..., httpx.Client]:
    original_client = httpx.Client

    def create_client(**_: object) -> httpx.Client:
        return original_client(transport=httpx.MockTransport(handler))

    return create_client
