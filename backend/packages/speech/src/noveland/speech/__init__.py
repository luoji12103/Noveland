from __future__ import annotations

from importlib import import_module
from typing import Any

PACKAGE_NAME = "speech"

_EXPORTS = {
    "SpeechService": ("noveland.speech.service", "SpeechService"),
    "VoiceProfileService": ("noveland.speech.voice_profiles", "VoiceProfileService"),
    "SpeechStyleMappingService": (
        "noveland.speech.style_mapping",
        "SpeechStyleMappingService",
    ),
    "VoiceProfileCreate": ("noveland.speech.contracts", "VoiceProfileCreate"),
    "VoiceProfileRead": ("noveland.speech.contracts", "VoiceProfileRead"),
    "TTSRequest": ("noveland.speech.contracts", "TTSRequest"),
    "TTSResult": ("noveland.speech.contracts", "TTSResult"),
    "STTRequest": ("noveland.speech.contracts", "STTRequest"),
    "STTResult": ("noveland.speech.contracts", "STTResult"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    return getattr(import_module(module_name), attr_name)


__all__ = sorted((*_EXPORTS, "PACKAGE_NAME"))
