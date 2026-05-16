from __future__ import annotations

from typing import Any

import httpx
from noveland.providers.adapters.openai_image import ImageAdapterResult


class AnthropicCompatibleTextAdapterError(RuntimeError):
    pass


class AnthropicCompatibleTextAdapter:
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
        media_inputs: object | None = None,
    ) -> ImageAdapterResult:
        del media_inputs
        if bool(config_json.get("dry_run", False)):
            text = input_text or str(input_json.get("prompt") or request_json.get("prompt") or "ok")
            return ImageAdapterResult(
                output_text=f"anthropic-compatible dry-run: {text}",
                output_json={"text": f"anthropic-compatible dry-run: {text}", "dry_run": True},
                raw_response_json={"dry_run": True},
                media_bytes=None,
                media_mime_type=None,
                media_filename=None,
            )
        api_key = _api_key(auth_ref)
        endpoint = _endpoint(base_url, str(config_json.get("messages_path", "/v1/messages")))
        payload = _payload(default_params_json, input_text, input_json, request_json)
        headers = {
            "x-api-key": api_key,
            "anthropic-version": str(config_json.get("anthropic_version") or "2023-06-01"),
        }
        with httpx.Client(timeout=float(config_json.get("timeout_seconds", 60))) as client:
            response = client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        raw = response.json()
        text = _extract_text(raw)
        return ImageAdapterResult(
            output_text=text,
            output_json={"text": text},
            raw_response_json=raw if isinstance(raw, dict) else {"response": raw},
            media_bytes=None,
            media_mime_type=None,
            media_filename=None,
        )


def _payload(
    default_params_json: dict[str, Any],
    input_text: str | None,
    input_json: dict[str, Any],
    request_json: dict[str, Any],
) -> dict[str, Any]:
    prompt = input_text or request_json.get("prompt") or input_json.get("prompt")
    if not isinstance(prompt, str) or prompt.strip() == "":
        raise AnthropicCompatibleTextAdapterError("text generation requires prompt")
    payload = {**default_params_json, **request_json}
    payload.pop("prompt", None)
    payload.setdefault("model", request_json.get("model") or input_json.get("model") or "model")
    payload.setdefault("max_tokens", 1024)
    if "messages" not in payload:
        payload["messages"] = [{"role": "user", "content": prompt}]
    return payload


def _extract_text(raw: object) -> str:
    if isinstance(raw, dict):
        content = raw.get("content")
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            if parts:
                return "\n".join(parts)
        if isinstance(raw.get("text"), str):
            return str(raw["text"])
    raise AnthropicCompatibleTextAdapterError("text response did not include output text")


def _endpoint(base_url: str | None, path: str) -> str:
    if not isinstance(base_url, str) or base_url.strip() == "":
        raise AnthropicCompatibleTextAdapterError("text adapter requires configured base_url")
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _api_key(auth_ref: str | None) -> str:
    if not isinstance(auth_ref, str) or auth_ref.strip() == "":
        raise AnthropicCompatibleTextAdapterError("text adapter requires resolved auth_ref")
    return auth_ref
