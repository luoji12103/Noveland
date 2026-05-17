from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from noveland.providers.contracts import ProviderAdapterKind
from noveland.visual_generation.contracts import (
    ValidationIssue,
    ValidationSeverity,
    VisualGenerationPlanValidationResult,
)


@dataclass(frozen=True, slots=True)
class ProviderMappingResult:
    mapping_kind: str
    request_json: dict[str, Any]
    validation: VisualGenerationPlanValidationResult


def map_provider_request(
    *,
    adapter_kind: ProviderAdapterKind,
    provider_key: str,
    template_payload_json: dict[str, Any],
    slot_values: dict[str, Any],
    prompt_plan_json: dict[str, Any],
    model_plan_json: dict[str, Any],
    output_plan_json: dict[str, Any],
) -> ProviderMappingResult:
    if adapter_kind == ProviderAdapterKind.COMFYUI:
        return _map_comfyui(
            template_payload_json=template_payload_json,
            slot_values=slot_values,
            prompt_plan_json=prompt_plan_json,
            model_plan_json=model_plan_json,
            output_plan_json=output_plan_json,
        )
    if adapter_kind in {ProviderAdapterKind.OPENAI, ProviderAdapterKind.OPENAI_COMPATIBLE}:
        return _map_openai_image(
            adapter_kind=adapter_kind,
            slot_values=slot_values,
            prompt_plan_json=prompt_plan_json,
            model_plan_json=model_plan_json,
            output_plan_json=output_plan_json,
        )
    if adapter_kind == ProviderAdapterKind.CUSTOM_HTTP:
        if _is_z_image(provider_key, model_plan_json):
            return _map_z_image(
                slot_values=slot_values,
                prompt_plan_json=prompt_plan_json,
                output_plan_json=output_plan_json,
            )
        return _map_generic(
            slot_values=slot_values,
            prompt_plan_json=prompt_plan_json,
            model_plan_json=model_plan_json,
            output_plan_json=output_plan_json,
        )
    return _mapping_failure(adapter_kind.value, "adapter is not supported by visual generation")


def _map_comfyui(
    *,
    template_payload_json: dict[str, Any],
    slot_values: dict[str, Any],
    prompt_plan_json: dict[str, Any],
    model_plan_json: dict[str, Any],
    output_plan_json: dict[str, Any],
) -> ProviderMappingResult:
    if not template_payload_json:
        return _mapping_failure("comfyui", "ComfyUI mapping requires a registered template payload")
    request = {
        "adapter": "comfyui",
        "template_payload_configured": True,
        "slots": slot_values,
        "prompt_plan": prompt_plan_json,
        "model_plan": model_plan_json,
        "output_plan": output_plan_json,
    }
    return _mapping_success("comfyui", request)


def _map_openai_image(
    *,
    adapter_kind: ProviderAdapterKind,
    slot_values: dict[str, Any],
    prompt_plan_json: dict[str, Any],
    model_plan_json: dict[str, Any],
    output_plan_json: dict[str, Any],
) -> ProviderMappingResult:
    unsupported = {
        key
        for key in ("checkpoint", "loras", "workflow", "sampler", "steps_cfg")
        if key in slot_values or key in model_plan_json
    }
    if unsupported:
        return _mapping_failure(
            adapter_kind.value,
            f"{adapter_kind.value} does not support fields: {', '.join(sorted(unsupported))}",
        )
    prompt = (
        prompt_plan_json.get("positive")
        or prompt_plan_json.get("prompt")
        or slot_values.get("positive_prompt")
        or slot_values.get("prompt")
    )
    if not isinstance(prompt, str) or not prompt.strip():
        return _mapping_failure(adapter_kind.value, "image mapping requires a prompt")
    request = {
        "adapter": adapter_kind.value,
        "prompt": prompt.strip(),
        "reference_assets": slot_values.get("reference_assets", []),
        "output": output_plan_json,
    }
    return _mapping_success(adapter_kind.value, request)


def _map_z_image(
    *,
    slot_values: dict[str, Any],
    prompt_plan_json: dict[str, Any],
    output_plan_json: dict[str, Any],
) -> ProviderMappingResult:
    unsupported = {
        key
        for key in ("loras", "lora_ids", "workflow", "mask_asset_id", "control_asset_id")
        if key in slot_values
    }
    if unsupported:
        return _mapping_failure(
            "z_image",
            f"z_image does not support fields: {', '.join(sorted(unsupported))}",
        )
    prompt = (
        prompt_plan_json.get("positive")
        or prompt_plan_json.get("prompt")
        or slot_values.get("positive_prompt")
        or slot_values.get("prompt")
    )
    if not isinstance(prompt, str) or not prompt.strip():
        return _mapping_failure("z_image", "Z-Image mapping requires a prompt")
    request = {
        "adapter": "custom_http",
        "provider_family": "z_image",
        "prompt": prompt.strip(),
        "output": output_plan_json,
    }
    return _mapping_success("z_image", request)


def _map_generic(
    *,
    slot_values: dict[str, Any],
    prompt_plan_json: dict[str, Any],
    model_plan_json: dict[str, Any],
    output_plan_json: dict[str, Any],
) -> ProviderMappingResult:
    request = {
        "adapter": "custom_http",
        "slots": slot_values,
        "prompt_plan": prompt_plan_json,
        "model_plan": model_plan_json,
        "output_plan": output_plan_json,
    }
    return _mapping_success("custom_http", request)


def _is_z_image(provider_key: str, model_plan_json: dict[str, Any]) -> bool:
    provider_family = model_plan_json.get("provider_family")
    if isinstance(provider_family, str) and provider_family.strip().lower() in {
        "z_image",
        "z-image",
    }:
        return True
    return "z-image" in provider_key.lower() or "z_image" in provider_key.lower()


def _mapping_success(mapping_kind: str, request_json: dict[str, Any]) -> ProviderMappingResult:
    return ProviderMappingResult(
        mapping_kind=mapping_kind,
        request_json=request_json,
        validation=VisualGenerationPlanValidationResult(
            passed=True,
            mapping_kind=mapping_kind,
            provider_call_made=False,
        ),
    )


def _mapping_failure(mapping_kind: str, message: str) -> ProviderMappingResult:
    return ProviderMappingResult(
        mapping_kind=mapping_kind,
        request_json={},
        validation=VisualGenerationPlanValidationResult(
            passed=False,
            mapping_kind=mapping_kind,
            provider_call_made=False,
            issues=(
                ValidationIssue(
                    code="provider_mapping_failed",
                    message=message,
                    severity=ValidationSeverity.ERROR,
                ),
            ),
        ),
    )
