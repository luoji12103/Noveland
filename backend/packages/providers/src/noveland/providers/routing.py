from __future__ import annotations

from collections.abc import Mapping

from noveland.invocations.contracts import InvocationKind, InvocationProviderKind
from noveland.media.contracts import MediaAssetKind, MediaAssetRole, MediaJobKind
from noveland.providers.contracts import ProviderAdapterKind, ProviderKind


class ProviderRoutingError(ValueError):
    pass


COMPATIBLE_PROVIDER_KINDS: Mapping[ProviderAdapterKind, set[ProviderKind]] = {
    ProviderAdapterKind.FAKE: set(ProviderKind),
    ProviderAdapterKind.LOCAL_STUB: set(ProviderKind),
    ProviderAdapterKind.OPENAI: {
        ProviderKind.TEXT_GENERATION,
        ProviderKind.IMAGE_GENERATION,
        ProviderKind.IMAGE_EDITING,
        ProviderKind.IMAGE_ANALYSIS,
        ProviderKind.SPEECH_TO_TEXT,
        ProviderKind.TEXT_TO_SPEECH,
        ProviderKind.EMBEDDING,
    },
    ProviderAdapterKind.OPENAI_COMPATIBLE: {
        ProviderKind.TEXT_GENERATION,
        ProviderKind.IMAGE_GENERATION,
        ProviderKind.IMAGE_EDITING,
        ProviderKind.IMAGE_ANALYSIS,
        ProviderKind.EMBEDDING,
        ProviderKind.RERANKER,
    },
    ProviderAdapterKind.ANTHROPIC: {ProviderKind.TEXT_GENERATION},
    ProviderAdapterKind.ANTHROPIC_COMPATIBLE: {ProviderKind.TEXT_GENERATION},
    ProviderAdapterKind.COMFYUI: {
        ProviderKind.WORKFLOW_ENGINE,
        ProviderKind.IMAGE_GENERATION,
        ProviderKind.IMAGE_EDITING,
        ProviderKind.IMAGE_ANALYSIS,
        ProviderKind.IMAGE_COMPOSITION,
    },
    ProviderAdapterKind.MIMO_TTS: {ProviderKind.TEXT_TO_SPEECH, ProviderKind.VOICE_CLONING},
    ProviderAdapterKind.MIMO_ASR: {ProviderKind.SPEECH_TO_TEXT},
    ProviderAdapterKind.OMNIVOICE: {ProviderKind.TEXT_TO_SPEECH, ProviderKind.VOICE_CLONING},
    ProviderAdapterKind.GPT_SOVITS: {ProviderKind.TEXT_TO_SPEECH, ProviderKind.VOICE_CLONING},
    ProviderAdapterKind.REMBG: {ProviderKind.BACKGROUND_REMOVAL},
    ProviderAdapterKind.SAM2: {ProviderKind.IMAGE_ANALYSIS, ProviderKind.IMAGE_EDITING},
    ProviderAdapterKind.CUSTOM_HTTP: set(ProviderKind),
    ProviderAdapterKind.OTHER: set(ProviderKind),
}


def validate_provider_adapter_compatibility(
    provider_kind: ProviderKind,
    adapter_kind: ProviderAdapterKind,
) -> None:
    allowed = COMPATIBLE_PROVIDER_KINDS[adapter_kind]
    if provider_kind not in allowed:
        raise ProviderRoutingError(
            f"adapter_kind={adapter_kind.value} does not support "
            f"provider_kind={provider_kind.value}"
        )


def invocation_kind_for_provider(provider_kind: ProviderKind) -> InvocationKind:
    if provider_kind == ProviderKind.IMAGE_GENERATION:
        return InvocationKind.IMAGE_GENERATION
    if provider_kind == ProviderKind.IMAGE_EDITING:
        return InvocationKind.IMAGE_EDIT
    if provider_kind == ProviderKind.IMAGE_ANALYSIS:
        return InvocationKind.IMAGE_ANALYSIS
    if provider_kind == ProviderKind.SPEECH_TO_TEXT:
        return InvocationKind.SPEECH_TO_TEXT
    if provider_kind == ProviderKind.TEXT_TO_SPEECH:
        return InvocationKind.TEXT_TO_SPEECH
    if provider_kind == ProviderKind.VOICE_CLONING:
        return InvocationKind.VOICE_CLONE
    if provider_kind == ProviderKind.TEXT_GENERATION:
        return InvocationKind.CONVERSATION_TURN
    return InvocationKind.OTHER


def invocation_provider_kind_for_adapter(
    provider_kind: ProviderKind,
    adapter_kind: ProviderAdapterKind,
) -> InvocationProviderKind:
    if adapter_kind in {ProviderAdapterKind.FAKE, ProviderAdapterKind.LOCAL_STUB}:
        return InvocationProviderKind.LOCAL_STUB
    if adapter_kind == ProviderAdapterKind.OPENAI_COMPATIBLE:
        return InvocationProviderKind.OPENAI_COMPATIBLE
    if adapter_kind == ProviderAdapterKind.ANTHROPIC_COMPATIBLE:
        return InvocationProviderKind.ANTHROPIC_COMPATIBLE
    if adapter_kind == ProviderAdapterKind.COMFYUI:
        return InvocationProviderKind.COMFYUI
    if adapter_kind == ProviderAdapterKind.MIMO_TTS:
        return InvocationProviderKind.MIMO_TTS
    if adapter_kind == ProviderAdapterKind.MIMO_ASR:
        return InvocationProviderKind.MIMO_ASR
    if adapter_kind == ProviderAdapterKind.OMNIVOICE:
        return InvocationProviderKind.OMNIVOICE
    if adapter_kind == ProviderAdapterKind.GPT_SOVITS:
        return InvocationProviderKind.GPT_SOVITS
    if adapter_kind == ProviderAdapterKind.OPENAI:
        if provider_kind in {ProviderKind.IMAGE_GENERATION, ProviderKind.IMAGE_EDITING}:
            return InvocationProviderKind.OPENAI_IMAGE
        if provider_kind in {ProviderKind.SPEECH_TO_TEXT, ProviderKind.TEXT_TO_SPEECH}:
            return InvocationProviderKind.OPENAI_AUDIO
        return InvocationProviderKind.OPENAI_COMPATIBLE
    return InvocationProviderKind.CUSTOM_HTTP


def media_job_kind_for_provider(provider_kind: ProviderKind) -> MediaJobKind | None:
    if provider_kind == ProviderKind.IMAGE_GENERATION:
        return MediaJobKind.IMAGE_GENERATION
    if provider_kind == ProviderKind.IMAGE_EDITING:
        return MediaJobKind.IMAGE_EDIT
    if provider_kind == ProviderKind.IMAGE_COMPOSITION:
        return MediaJobKind.COMPOSITION
    if provider_kind == ProviderKind.IMAGE_ANALYSIS:
        return MediaJobKind.VISION_ANALYSIS
    if provider_kind == ProviderKind.TEXT_TO_SPEECH:
        return MediaJobKind.SPEECH_GENERATION
    if provider_kind == ProviderKind.SPEECH_TO_TEXT:
        return MediaJobKind.SPEECH_TRANSCRIPTION
    if provider_kind == ProviderKind.BACKGROUND_REMOVAL:
        return MediaJobKind.BACKGROUND_REMOVAL
    return None


def output_asset_shape_for_provider(
    provider_kind: ProviderKind,
) -> tuple[MediaAssetKind, MediaAssetRole]:
    if provider_kind == ProviderKind.TEXT_TO_SPEECH:
        return MediaAssetKind.AUDIO, MediaAssetRole.SPEECH_AUDIO
    if provider_kind == ProviderKind.SPEECH_TO_TEXT:
        return MediaAssetKind.AUDIO, MediaAssetRole.TRANSCRIPT_AUDIO
    return MediaAssetKind.IMAGE, MediaAssetRole.ORIGINAL_IMAGE
