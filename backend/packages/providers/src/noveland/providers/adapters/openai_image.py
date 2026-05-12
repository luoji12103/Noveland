from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import httpx
from noveland.providers.adapters.speech_common import SpeechAdapterInput

OPENAI_API_BASE_URL = "https://api.openai.com/v1"


class OpenAIImageAdapterError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ImageAdapterInput:
    filename: str
    data: bytes
    mime_type: str
    field_name: str = "image"


@dataclass(frozen=True, slots=True)
class ImageAdapterResult:
    output_text: str | None
    output_json: dict[str, Any]
    raw_response_json: dict[str, Any]
    media_bytes: bytes | None
    media_mime_type: str | None
    media_filename: str | None


class OpenAIImageAdapter:
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
        media_inputs: list[ImageAdapterInput] | list[SpeechAdapterInput] | None = None,
    ) -> ImageAdapterResult:
        api_key = _api_key(auth_ref, config_json)
        is_edit = request_json.get("operation") == "edit" or bool(media_inputs)
        endpoint = _endpoint(base_url, "/images/edits" if is_edit else "/images/generations")
        with httpx.Client(timeout=float(config_json.get("timeout_seconds", 60))) as client:
            if is_edit:
                response = client.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {api_key}"},
                    data=self._payload(default_params_json, input_text, input_json, request_json),
                    files=_files(_image_inputs(media_inputs)),
                )
            else:
                response = client.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=self._payload(default_params_json, input_text, input_json, request_json),
                )
        response.raise_for_status()
        raw = response.json()
        return _decode_image_response(raw, request_json.get("output_format", "png"))

    def _payload(
        self,
        default_params_json: dict[str, Any],
        input_text: str | None,
        input_json: dict[str, Any],
        request_json: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = input_text or request_json.get("prompt") or input_json.get("prompt")
        if not isinstance(prompt, str) or prompt.strip() == "":
            raise OpenAIImageAdapterError("OpenAI image generation requires prompt")
        payload = {**default_params_json}
        payload.setdefault("model", "gpt-image-2")
        payload["prompt"] = prompt
        for key in ("size", "quality", "background", "output_format"):
            value = request_json.get(key)
            if value is not None:
                payload[key] = value
        payload.pop("reference_asset_ids", None)
        payload.pop("input_asset_ids", None)
        payload.pop("mask_asset_id", None)
        payload.pop("operation", None)
        return payload


def _decode_image_response(raw: dict[str, Any], output_format: object) -> ImageAdapterResult:
    data = raw.get("data")
    if not isinstance(data, list) or not data:
        raise OpenAIImageAdapterError("OpenAI image response did not include data")
    first = data[0]
    if not isinstance(first, dict):
        raise OpenAIImageAdapterError("OpenAI image response data must contain objects")
    b64_json = first.get("b64_json")
    if not isinstance(b64_json, str):
        raise OpenAIImageAdapterError("OpenAI image response must include b64_json")
    media = base64.b64decode(b64_json)
    ext = str(output_format or "png").lower()
    mime_type = {
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "webp": "image/webp",
    }.get(ext, "image/png")
    revised_prompt = first.get("revised_prompt")
    return ImageAdapterResult(
        output_text=revised_prompt if isinstance(revised_prompt, str) else None,
        output_json={"media": "image", "revised_prompt": revised_prompt},
        raw_response_json=raw,
        media_bytes=media,
        media_mime_type=mime_type,
        media_filename=f"openai-image.{ext}",
    )


def _endpoint(base_url: str | None, path: str) -> str:
    return f"{(base_url or OPENAI_API_BASE_URL).rstrip('/')}{path}"


def _api_key(auth_ref: str | None, config_json: dict[str, Any]) -> str:
    api_key = config_json.get("api_key") or auth_ref
    if not isinstance(api_key, str) or api_key.strip() == "":
        raise OpenAIImageAdapterError(
            "OpenAI image adapter requires auth_ref or config_json.api_key"
        )
    return api_key


def _image_inputs(
    value: list[ImageAdapterInput] | list[SpeechAdapterInput] | None,
) -> list[ImageAdapterInput]:
    if value is None:
        return []
    return [item for item in value if isinstance(item, ImageAdapterInput)]


def _files(media_inputs: list[ImageAdapterInput]) -> list[tuple[str, tuple[str, bytes, str]]]:
    if not media_inputs:
        raise OpenAIImageAdapterError("OpenAI image edit requires input images")
    return [
        (item.field_name, (item.filename, item.data, item.mime_type))
        for item in media_inputs
    ]
