from __future__ import annotations

import base64
import copy
import uuid
from dataclasses import dataclass
from typing import Any

import httpx


class ComfyUIAdapterError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ComfyUIAdapterResult:
    output_text: str | None
    output_json: dict[str, Any]
    raw_response_json: dict[str, Any]
    media_bytes: bytes | None
    media_mime_type: str | None
    media_filename: str | None


class ComfyUIAdapter:
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
    ) -> ComfyUIAdapterResult:
        if bool(config_json.get("dry_run", False)):
            return self._dry_run(input_text, input_json, request_json)
        if base_url is None:
            raise ComfyUIAdapterError("ComfyUI adapter requires base_url unless dry_run is enabled")
        workflow_template = config_json.get("workflow_template_json") or default_params_json.get(
            "workflow_template_json"
        )
        workflow = _mapped_workflow(
            workflow_template,
            config_json.get("input_mapping_json", {}),
            input_text=input_text,
            input_json=input_json,
            request_json=request_json,
        )
        client_id = str(uuid.uuid4())
        headers = {"Authorization": f"Bearer {auth_ref}"} if auth_ref else {}
        timeout = float(config_json.get("timeout_seconds", 60))
        with httpx.Client(timeout=timeout) as client:
            prompt_response = client.post(
                f"{base_url.rstrip('/')}/prompt",
                headers=headers,
                json={"prompt": workflow, "client_id": client_id},
            )
            prompt_response.raise_for_status()
            submitted = prompt_response.json()
            prompt_id = submitted.get("prompt_id")
            if not isinstance(prompt_id, str):
                raise ComfyUIAdapterError("ComfyUI prompt response missing prompt_id")
            history_response = client.get(
                f"{base_url.rstrip('/')}/history/{prompt_id}",
                headers=headers,
            )
            history_response.raise_for_status()
            history = history_response.json()
            output_mapping = config_json.get("output_mapping_json", {})
            filename = _first_output_filename(history, output_mapping)
            view_response = client.get(
                f"{base_url.rstrip('/')}/view",
                headers=headers,
                params={"filename": filename},
            )
            view_response.raise_for_status()
        return ComfyUIAdapterResult(
            output_text="comfyui image generated",
            output_json={"media": "image", "prompt_id": prompt_id},
            raw_response_json={"prompt": submitted, "history": history},
            media_bytes=view_response.content,
            media_mime_type=view_response.headers.get("content-type", "image/png"),
            media_filename=filename,
        )

    def _dry_run(
        self,
        input_text: str | None,
        input_json: dict[str, Any],
        request_json: dict[str, Any],
    ) -> ComfyUIAdapterResult:
        workflow = {
            "prompt": input_text or request_json.get("prompt") or input_json.get("prompt"),
            "request": request_json,
        }
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAA"
            "DUlEQVR4nGP4z8DwHwAFgwJ/lq9S9wAAAABJRU5ErkJggg=="
        )
        return ComfyUIAdapterResult(
            output_text="comfyui dry-run image generated",
            output_json={"media": "image", "dry_run": True},
            raw_response_json={"dry_run": True, "workflow": workflow},
            media_bytes=png,
            media_mime_type="image/png",
            media_filename="comfyui-dry-run.png",
        )


def _mapped_workflow(
    template: object,
    input_mapping: object,
    *,
    input_text: str | None,
    input_json: dict[str, Any],
    request_json: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(template, dict):
        raise ComfyUIAdapterError("ComfyUI workflow_template_json must be an object")
    workflow = copy.deepcopy(template)
    mapping = input_mapping if isinstance(input_mapping, dict) else {}
    values: dict[str, Any] = {
        "prompt": input_text or request_json.get("prompt") or input_json.get("prompt"),
        "negative_prompt": request_json.get("negative_prompt"),
        "size": request_json.get("size"),
    }
    for value_key, path in mapping.items():
        if value_key not in values or values[value_key] is None:
            continue
        if isinstance(path, list) and all(isinstance(part, str) for part in path):
            _set_nested(workflow, path, values[value_key])
    return workflow


def _set_nested(workflow: dict[str, Any], path: list[str], value: Any) -> None:
    cursor: dict[str, Any] = workflow
    for key in path[:-1]:
        next_value = cursor.setdefault(key, {})
        if not isinstance(next_value, dict):
            raise ComfyUIAdapterError("ComfyUI input mapping path crosses non-object value")
        cursor = next_value
    cursor[path[-1]] = value


def _first_output_filename(history: dict[str, Any], output_mapping: object) -> str:
    if isinstance(output_mapping, dict) and isinstance(output_mapping.get("filename"), str):
        return str(output_mapping["filename"])
    def walk(value: object) -> str | None:
        if isinstance(value, dict):
            filename = value.get("filename")
            if isinstance(filename, str):
                return filename
            for nested in value.values():
                found = walk(nested)
                if found is not None:
                    return found
        if isinstance(value, list):
            for nested in value:
                found = walk(nested)
                if found is not None:
                    return found
        return None

    filename = walk(history)
    if filename is None:
        raise ComfyUIAdapterError("ComfyUI history did not include an output filename")
    return filename
