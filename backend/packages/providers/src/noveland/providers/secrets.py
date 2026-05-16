from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from noveland.core.settings import AppSettings

SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "token",
    "bearer_token",
    "authorization",
    "secret",
    "client_secret",
    "access_key",
    "password",
    "private_key",
}
REDACTED = "[REDACTED]"
_ALIASES = {
    "openai:default": "env:OPENAI_API_KEY",
    "mimo:default": "env:MIMO_API_KEY",
}
_ALLOWED_REFERENCE_PREFIXES = ("env:", "secret:")
_AUTH_REQUIRED_ADAPTERS = {
    "openai",
    "openai_compatible",
    "anthropic",
    "anthropic_compatible",
    "mimo_tts",
    "mimo_asr",
    "omnivoice",
    "gpt_sovits",
}


class ProviderSecretError(ValueError):
    pass


class ProviderSecretValidationError(ProviderSecretError):
    pass


class ProviderSecretMissingError(ProviderSecretError):
    pass


@dataclass(frozen=True, slots=True)
class ResolvedProviderSecret:
    auth_ref: str
    source: str
    value: str


class ProviderSecretResolver:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self._settings = settings

    def resolve_auth_ref(self, auth_ref: str | None) -> ResolvedProviderSecret | None:
        if auth_ref is None or auth_ref.strip() == "":
            return None
        normalized = _normalize_auth_ref(auth_ref)
        if not normalized.startswith("env:"):
            raise ProviderSecretMissingError("unsupported auth_ref source")
        env_name = normalized.removeprefix("env:")
        if not env_name:
            raise ProviderSecretMissingError("auth_ref environment variable is empty")
        value = os.environ.get(env_name)
        if value is None and self._settings is not None:
            value = self._settings.provider_api_keys_json.get(
                auth_ref,
                self._settings.provider_api_keys_json.get(normalized),
            )
        if value is None or value == "":
            raise ProviderSecretMissingError("auth_ref secret is missing")
        return ResolvedProviderSecret(auth_ref=auth_ref, source=normalized, value=value)


def reject_sensitive_config(value: Any, *, field_name: str) -> None:
    path = _first_sensitive_path(value)
    if path is not None:
        raise ProviderSecretValidationError(f"{field_name} contains sensitive key: {path}")


def validate_auth_ref_reference(auth_ref: str | None) -> str | None:
    if auth_ref is None:
        return None
    stripped = auth_ref.strip()
    if stripped == "":
        raise ProviderSecretValidationError("auth_ref must not be empty")
    if stripped in _ALIASES:
        return stripped
    if any(
        stripped.startswith(prefix) and len(stripped) > len(prefix)
        for prefix in _ALLOWED_REFERENCE_PREFIXES
    ):
        return stripped
    raise ProviderSecretValidationError("auth_ref must be a provider secret reference")


def sanitize_for_persistence(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if _is_sensitive_key(str(key)):
                sanitized[str(key)] = REDACTED
            else:
                sanitized[str(key)] = sanitize_for_persistence(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_for_persistence(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_for_persistence(item) for item in value]
    return value


def safe_auth_metadata(
    auth_ref: str | None,
    resolved: ResolvedProviderSecret | None,
) -> dict[str, bool]:
    return {
        "auth_ref_present": auth_ref is not None and auth_ref.strip() != "",
        "auth_resolved": resolved is not None,
        "auth_failed": False,
    }


def failed_auth_metadata(auth_ref: str | None) -> dict[str, bool]:
    return {
        "auth_ref_present": auth_ref is not None and auth_ref.strip() != "",
        "auth_resolved": False,
        "auth_failed": True,
    }


def adapter_requires_auth(adapter_kind: object, config_json: dict[str, Any]) -> bool:
    if bool(config_json.get("dry_run", False)):
        return False
    raw_value = getattr(adapter_kind, "value", adapter_kind)
    return str(raw_value) in _AUTH_REQUIRED_ADAPTERS


def _normalize_auth_ref(auth_ref: str) -> str:
    stripped = auth_ref.strip()
    return _ALIASES.get(stripped, stripped)


def _first_sensitive_path(value: Any, *, prefix: str = "") -> str | None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            path = key_text if prefix == "" else f"{prefix}.{key_text}"
            if _is_sensitive_key(key_text):
                return path
            nested = _first_sensitive_path(item, prefix=path)
            if nested is not None:
                return nested
    elif isinstance(value, list):
        for index, item in enumerate(value):
            path = f"{prefix}[{index}]"
            nested = _first_sensitive_path(item, prefix=path)
            if nested is not None:
                return nested
    return None


def _is_sensitive_key(key: str) -> bool:
    return key.strip().lower() in SENSITIVE_KEYS
