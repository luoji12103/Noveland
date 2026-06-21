from __future__ import annotations

from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderCapabilityCreate,
    ProviderKind,
    ProviderTemplateRead,
)
from noveland.providers.routing import validate_provider_adapter_compatibility


def provider_templates() -> list[ProviderTemplateRead]:
    """Static v0.9 provider setup templates.

    These are code-owned presets over provider_integrations, not persisted template records.
    """

    templates = [
        ProviderTemplateRead(
            template_key="openai-compatible-llm",
            display_name="OpenAI-compatible LLM",
            provider_kind=ProviderKind.TEXT_GENERATION,
            adapter_kind=ProviderAdapterKind.OPENAI_COMPATIBLE,
            description="Chat/completions-compatible text provider with custom base URL.",
            base_url_placeholder="https://gateway.example/v1",
            model_name_placeholder="model-name",
            auth_ref_placeholder="env:OPENAI_API_KEY",
            config_json={
                "model_discovery_path": "/models",
                "chat_completions_path": "/chat/completions",
            },
            default_params_json={"temperature": 0.7},
            capabilities=(
                _cap("text.generate", streaming=False, model_discovery=True),
            ),
            model_discovery={"strategy": "openai_models", "path": "/models"},
        ),
        ProviderTemplateRead(
            template_key="anthropic-compatible-llm",
            display_name="Anthropic-compatible LLM",
            provider_kind=ProviderKind.TEXT_GENERATION,
            adapter_kind=ProviderAdapterKind.ANTHROPIC_COMPATIBLE,
            description="Messages-compatible text provider with custom base URL.",
            base_url_placeholder="https://gateway.example",
            model_name_placeholder="model-name",
            auth_ref_placeholder="env:ANTHROPIC_API_KEY",
            config_json={
                "model_discovery_path": "/v1/models",
                "messages_path": "/v1/messages",
                "anthropic_version": "2023-06-01",
            },
            default_params_json={"max_tokens": 1024},
            capabilities=(
                _cap("text.generate", streaming=False, model_discovery=True),
            ),
            model_discovery={"strategy": "anthropic_models", "path": "/v1/models"},
        ),
        ProviderTemplateRead(
            template_key="mimo-v2-5-tts",
            display_name="MiMo V2.5 TTS",
            provider_kind=ProviderKind.TEXT_TO_SPEECH,
            adapter_kind=ProviderAdapterKind.MIMO_TTS,
            description="MiMo-compatible TTS routed through configurable endpoint or gateway.",
            base_url_placeholder="https://gateway.example",
            model_name_placeholder="mimo-tts-model",
            auth_ref_placeholder="env:MIMO_API_KEY",
            config_json={"endpoint": "/tts", "model_discovery_path": "/models"},
            default_params_json={"output_format": "wav"},
            capabilities=(_cap("speech.tts", model_discovery=True),),
            model_discovery={"strategy": "generic_models", "path": "/models"},
        ),
        ProviderTemplateRead(
            template_key="mimo-v2-5-asr",
            display_name="MiMo V2.5 ASR",
            provider_kind=ProviderKind.SPEECH_TO_TEXT,
            adapter_kind=ProviderAdapterKind.MIMO_ASR,
            description="MiMo-compatible ASR routed through configurable endpoint or gateway.",
            base_url_placeholder="https://gateway.example",
            model_name_placeholder="mimo-asr-model",
            auth_ref_placeholder="env:MIMO_API_KEY",
            config_json={
                "endpoint": "/v1/chat/completions",
                "request_format": "chat_completions",
                "model_discovery_path": "/v1/models",
            },
            capabilities=(_cap("speech.asr", model_discovery=True),),
            model_discovery={"strategy": "generic_models", "path": "/v1/models"},
        ),
        ProviderTemplateRead(
            template_key="z-image",
            display_name="Z-Image",
            provider_kind=ProviderKind.IMAGE_GENERATION,
            adapter_kind=ProviderAdapterKind.CUSTOM_HTTP,
            description="Z-Image image generation through a configurable compatible gateway.",
            base_url_placeholder="https://gateway.example/v1",
            model_name_placeholder="z-image-turbo",
            auth_ref_placeholder="env:IMAGE_API_KEY",
            config_json={"model_discovery_path": "/models"},
            default_params_json={"response_format": "b64_json"},
            capabilities=(
                _image_cap(
                    "image.generate",
                    text_to_image=True,
                    reference_images=False,
                    edit=False,
                    output_formats=["png"],
                ),
            ),
            model_discovery={"strategy": "openai_models", "path": "/models"},
        ),
        ProviderTemplateRead(
            template_key="gpt-image",
            display_name="GPT Image",
            provider_kind=ProviderKind.IMAGE_GENERATION,
            adapter_kind=ProviderAdapterKind.OPENAI,
            description="OpenAI image generation/editing with configurable base URL.",
            base_url_placeholder="https://gateway.example/v1",
            model_name_placeholder="gpt-image-2",
            auth_ref_placeholder="env:OPENAI_API_KEY",
            config_json={"model_discovery_path": "/models"},
            default_params_json={"model": "gpt-image-2"},
            capabilities=(
                _image_cap(
                    "image.generate",
                    text_to_image=True,
                    image_to_image=True,
                    edit=True,
                    reference_images=True,
                    output_formats=["png", "jpeg", "webp"],
                ),
            ),
            model_discovery={"strategy": "openai_models", "path": "/models"},
        ),
        ProviderTemplateRead(
            template_key="comfyui",
            display_name="ComfyUI",
            provider_kind=ProviderKind.WORKFLOW_ENGINE,
            adapter_kind=ProviderAdapterKind.COMFYUI,
            description="ComfyUI workflow engine with configurable base URL.",
            base_url_placeholder="http://127.0.0.1:8188",
            model_name_placeholder="workflow-key",
            config_json={"dry_run": True},
            capabilities=(
                _image_cap(
                    "workflow.execute",
                    workflow_templates=True,
                    lora_slots=True,
                    checkpoint_slots=True,
                    seed=True,
                    sampler=True,
                ),
            ),
            model_discovery={"strategy": "none"},
        ),
        ProviderTemplateRead(
            template_key="openai-compatible-image",
            display_name="OpenAI-compatible image",
            provider_kind=ProviderKind.IMAGE_GENERATION,
            adapter_kind=ProviderAdapterKind.OPENAI_COMPATIBLE,
            description="Image generation through an OpenAI-compatible/custom gateway.",
            base_url_placeholder="https://gateway.example/v1",
            model_name_placeholder="image-model",
            auth_ref_placeholder="env:IMAGE_API_KEY",
            config_json={"model_discovery_path": "/models"},
            default_params_json={"response_format": "b64_json"},
            capabilities=(
                _image_cap("image.generate", text_to_image=True, output_formats=["png"]),
            ),
            model_discovery={"strategy": "openai_models", "path": "/models"},
        ),
        ProviderTemplateRead(
            template_key="generic-image-custom-http",
            display_name="Generic image/custom HTTP",
            provider_kind=ProviderKind.IMAGE_GENERATION,
            adapter_kind=ProviderAdapterKind.CUSTOM_HTTP,
            description="Custom image provider configuration placeholder for manual smoke setup.",
            base_url_placeholder="https://provider.example",
            model_name_placeholder="image-model",
            auth_ref_placeholder="env:IMAGE_API_KEY",
            config_json={"model_discovery_path": "/models"},
            capabilities=(
                _image_cap(
                    "image.generate",
                    text_to_image=True,
                    reference_images=True,
                    output_formats=["provider-specific"],
                ),
            ),
            model_discovery={"strategy": "generic_models", "path": "/models"},
        ),
    ]
    for template in templates:
        validate_provider_adapter_compatibility(template.provider_kind, template.adapter_kind)
    return templates


def get_provider_template(template_key: str) -> ProviderTemplateRead | None:
    normalized = template_key.strip().lower()
    return next((item for item in provider_templates() if item.template_key == normalized), None)


def _cap(capability_key: str, **metadata: object) -> ProviderCapabilityCreate:
    return ProviderCapabilityCreate(capability_key=capability_key, capability_json=dict(metadata))


def _image_cap(capability_key: str, **metadata: object) -> ProviderCapabilityCreate:
    return _cap(capability_key, **metadata, provider_surface="image")
