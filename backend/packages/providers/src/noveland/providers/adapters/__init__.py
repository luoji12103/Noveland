from __future__ import annotations

from typing import Any

_EXPORTS = {
    "OpenAIImageAdapter": ("noveland.providers.adapters.openai_image", "OpenAIImageAdapter"),
    "OpenAICompatibleImageAdapter": (
        "noveland.providers.adapters.openai_compatible_image",
        "OpenAICompatibleImageAdapter",
    ),
    "ComfyUIAdapter": ("noveland.providers.adapters.comfyui", "ComfyUIAdapter"),
    "OpenAISpeechAdapter": (
        "noveland.providers.adapters.openai_speech",
        "OpenAISpeechAdapter",
    ),
    "MiMOTTSAdapter": ("noveland.providers.adapters.mimo_tts", "MiMOTTSAdapter"),
    "MiMOASRAdapter": ("noveland.providers.adapters.mimo_asr", "MiMOASRAdapter"),
    "OmniVoiceAdapter": ("noveland.providers.adapters.omnivoice", "OmniVoiceAdapter"),
    "GPTSoVITSAdapter": ("noveland.providers.adapters.gpt_sovits", "GPTSoVITSAdapter"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    module = __import__(module_name, fromlist=[attr_name])
    return getattr(module, attr_name)


__all__ = sorted(_EXPORTS)
