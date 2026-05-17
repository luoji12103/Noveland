from __future__ import annotations

from typing import Any


def slot_values_from_plan(
    *,
    prompt_plan_json: dict[str, Any],
    model_plan_json: dict[str, Any],
    output_plan_json: dict[str, Any],
) -> dict[str, Any]:
    slots: dict[str, Any] = {}
    for key in (
        "positive_prompt",
        "negative_prompt",
        "prompt",
        "reference_assets",
        "mask_asset_id",
        "control_asset_id",
    ):
        if key in prompt_plan_json:
            slots[key] = prompt_plan_json[key]
    for key in (
        "checkpoint",
        "checkpoint_id",
        "loras",
        "lora_ids",
        "vae",
        "embedding",
        "controlnet",
        "ip_adapter",
        "sampler",
        "seed",
        "steps",
        "cfg",
        "steps_cfg",
    ):
        if key in model_plan_json:
            slots[key] = model_plan_json[key]
    for key in (
        "width",
        "height",
        "size",
        "aspect_ratio",
        "transparent_background",
        "output_format",
        "output_node",
        "asset_kind",
    ):
        if key in output_plan_json:
            slots[key] = output_plan_json[key]
    return slots
