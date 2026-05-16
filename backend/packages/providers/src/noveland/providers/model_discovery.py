from __future__ import annotations

import uuid
from typing import Any

import httpx
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderKind,
    ProviderModelDiscoveryRead,
    ProviderModelDiscoveryRequest,
)
from noveland.providers.models import ProviderIntegration
from noveland.providers.registry import ProviderNotFoundError, ProviderRegistryService
from noveland.providers.secrets import (
    ProviderSecretMissingError,
    ProviderSecretResolver,
    reject_sensitive_config,
)
from sqlalchemy.orm import Session


class ProviderModelDiscoveryError(RuntimeError):
    pass


class ProviderModelDiscoveryService:
    def __init__(
        self,
        session: Session,
        *,
        secret_resolver: ProviderSecretResolver | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._session = session
        self._secret_resolver = secret_resolver or ProviderSecretResolver()
        self._http_client = http_client

    def discover(
        self,
        world_id: uuid.UUID,
        request: ProviderModelDiscoveryRequest,
        *,
        platform_admin: bool = False,
    ) -> ProviderModelDiscoveryRead:
        try:
            (
                provider_id,
                provider_kind,
                adapter_kind,
                base_url,
                auth_ref,
                config_json,
                default_params_json,
                model,
            ) = self._provider_config(world_id, request, platform_admin)
        except (ProviderNotFoundError, ProviderModelDiscoveryError, ValueError) as exc:
            if request.provider_kind is None or request.adapter_kind is None:
                raise
            return _failure(
                provider_id=request.provider_id,
                provider_kind=request.provider_kind,
                adapter_kind=request.adapter_kind,
                error_code="invalid_provider",
                error_message=_safe_error_message(str(exc)),
            )

        if request.provider_id is None:
            reject_sensitive_config(request.config_json, field_name="config_json")
            reject_sensitive_config(request.default_params_json, field_name="default_params_json")
            base_url = request.base_url
            auth_ref = request.auth_ref
            config_json = dict(request.config_json)
            default_params_json = dict(request.default_params_json)
            model = None

        try:
            models = self._discover_models(
                provider_kind,
                adapter_kind,
                base_url=base_url,
                auth_ref=auth_ref,
                config_json=config_json,
                default_params_json=default_params_json,
            )
        except ProviderModelDiscoveryError as exc:
            return _failure(
                provider_id=provider_id,
                provider_kind=provider_kind,
                adapter_kind=adapter_kind,
                error_code=_safe_error_code(str(exc)),
                error_message=_safe_error_message(str(exc)),
            )

        return ProviderModelDiscoveryRead(
            provider_id=provider_id,
            provider_kind=provider_kind,
            adapter_kind=adapter_kind,
            discovery_status="succeeded",
            models=models,
            manual_fallback_allowed=True,
            metadata_json={
                "model_count": len(models),
                "auth_ref_present": bool(auth_ref),
                "provider_status": None if model is None else model.status,
            },
        )

    def _provider_config(
        self,
        world_id: uuid.UUID,
        request: ProviderModelDiscoveryRequest,
        platform_admin: bool,
    ) -> tuple[
        uuid.UUID | None,
        ProviderKind,
        ProviderAdapterKind,
        str | None,
        str | None,
        dict[str, Any],
        dict[str, Any],
        ProviderIntegration | None,
    ]:
        if request.provider_id is None:
            if request.provider_kind is None or request.adapter_kind is None:
                raise ProviderModelDiscoveryError(
                    "provider_id or provider_kind/adapter_kind is required"
                )
            return (
                None,
                request.provider_kind,
                request.adapter_kind,
                request.base_url,
                request.auth_ref,
                dict(request.config_json),
                dict(request.default_params_json),
                None,
            )
        provider = ProviderRegistryService(self._session).get_provider(
            world_id,
            request.provider_id,
            include_hidden=True,
            platform_admin=platform_admin,
        )
        if provider is None:
            raise ProviderNotFoundError("provider integration not found")
        return (
            provider.id,
            provider.provider_kind,
            provider.adapter_kind,
            provider.base_url,
            provider.auth_ref,
            dict(provider.config_json),
            dict(provider.default_params_json),
            self._session.get(ProviderIntegration, provider.id),
        )

    def _discover_models(
        self,
        provider_kind: ProviderKind,
        adapter_kind: ProviderAdapterKind,
        *,
        base_url: str | None,
        auth_ref: str | None,
        config_json: dict[str, Any],
        default_params_json: dict[str, Any],
    ) -> list[str]:
        del provider_kind
        configured = config_json.get("available_models")
        if isinstance(configured, list):
            return sorted({str(item) for item in configured if str(item).strip()})
        if bool(config_json.get("disable_model_discovery", False)):
            raise ProviderModelDiscoveryError("model discovery disabled")
        if base_url is None or base_url.strip() == "":
            raise ProviderModelDiscoveryError("model discovery requires base_url")
        path = _discovery_path(adapter_kind, config_json)
        if path is None:
            raise ProviderModelDiscoveryError("model discovery unsupported for adapter")
        token = None
        if auth_ref is not None and auth_ref.strip():
            try:
                token = self._secret_resolver.resolve_auth_ref(auth_ref)
            except ProviderSecretMissingError as exc:
                raise ProviderModelDiscoveryError("auth_missing") from exc
        headers = _headers(adapter_kind, config_json, None if token is None else token.value)
        timeout = float(config_json.get("timeout_seconds", 30))
        endpoint = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        client = self._http_client
        close_client = False
        if client is None:
            client = httpx.Client(timeout=timeout)
            close_client = True
        try:
            response = client.get(endpoint, headers=headers, params=_query(default_params_json))
            response.raise_for_status()
            return _extract_models(response.json())
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ProviderModelDiscoveryError("model discovery failed") from exc
        finally:
            if close_client:
                client.close()


def _discovery_path(adapter_kind: ProviderAdapterKind, config_json: dict[str, Any]) -> str | None:
    configured = config_json.get("model_discovery_path")
    if isinstance(configured, str) and configured.strip():
        return configured
    strategy = str(config_json.get("model_discovery_strategy") or "").strip()
    if strategy == "none":
        return None
    if adapter_kind in {
        ProviderAdapterKind.OPENAI,
        ProviderAdapterKind.OPENAI_COMPATIBLE,
        ProviderAdapterKind.ANTHROPIC,
        ProviderAdapterKind.ANTHROPIC_COMPATIBLE,
        ProviderAdapterKind.MIMO_TTS,
        ProviderAdapterKind.MIMO_ASR,
        ProviderAdapterKind.CUSTOM_HTTP,
    }:
        return "/models"
    return None


def _headers(
    adapter_kind: ProviderAdapterKind,
    config_json: dict[str, Any],
    secret: str | None,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    if secret:
        if adapter_kind in {
            ProviderAdapterKind.ANTHROPIC,
            ProviderAdapterKind.ANTHROPIC_COMPATIBLE,
        }:
            headers["x-api-key"] = secret
            headers["anthropic-version"] = str(
                config_json.get("anthropic_version") or "2023-06-01"
            )
        else:
            headers["Authorization"] = f"Bearer {secret}"
    return headers


def _query(default_params_json: dict[str, Any]) -> dict[str, str]:
    value = default_params_json.get("model_discovery_query")
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def _extract_models(raw: object) -> list[str]:
    if isinstance(raw, dict):
        for key in ("data", "models"):
            value = raw.get(key)
            if isinstance(value, list):
                return _models_from_list(value)
        value = raw.get("id")
        if isinstance(value, str):
            return [value]
    if isinstance(raw, list):
        return _models_from_list(raw)
    raise ProviderModelDiscoveryError("model discovery response did not include models")


def _models_from_list(value: list[object]) -> list[str]:
    models: set[str] = set()
    for item in value:
        if isinstance(item, str) and item.strip():
            models.add(item.strip())
        elif isinstance(item, dict):
            model_id = item.get("id") or item.get("name") or item.get("model")
            if isinstance(model_id, str) and model_id.strip():
                models.add(model_id.strip())
    if not models:
        raise ProviderModelDiscoveryError("model discovery response did not include models")
    return sorted(models)


def _safe_error_code(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "_")
    return normalized if normalized else "model_discovery_failed"


def _safe_error_message(value: str) -> str:
    lower = value.lower()
    if "auth" in lower:
        return "Model discovery could not authenticate with the configured provider."
    if "base_url" in lower:
        return "Model discovery needs a provider base URL."
    if "unsupported" in lower:
        return "Model discovery is not supported for this provider adapter."
    return "Model discovery failed. Enter a model name manually."


def _failure(
    *,
    provider_id: uuid.UUID | None,
    provider_kind: ProviderKind,
    adapter_kind: ProviderAdapterKind,
    error_code: str,
    error_message: str,
) -> ProviderModelDiscoveryRead:
    return ProviderModelDiscoveryRead(
        provider_id=provider_id,
        provider_kind=provider_kind,
        adapter_kind=adapter_kind,
        discovery_status="failed",
        models=[],
        manual_fallback_allowed=True,
        error_code=error_code,
        error_message=error_message,
        metadata_json={"model_count": 0},
    )
