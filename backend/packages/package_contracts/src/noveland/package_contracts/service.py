from __future__ import annotations

import uuid
from typing import Any

from noveland.package_contracts.contracts import (
    PackageContractIssue,
    PackageContractIssueSeverity,
    PackageContractValidationRequest,
    PackageContractValidationResult,
    PackageProviderCapabilityExport,
    PackageProviderConfigExport,
    PackageProviderConfigExportItem,
    PackageSafetyReviewStatus,
)
from noveland.plugins import PluginConfigValidationError, PluginNotFoundError, PluginRegistry
from noveland.plugins.builtins import get_builtin_plugin_registry
from noveland.providers.contracts import ProviderIntegrationListFilters
from noveland.providers.registry import ProviderRegistryService
from noveland.providers.routing import ProviderRoutingError, validate_provider_adapter_compatibility
from noveland.providers.secrets import (
    ProviderSecretValidationError,
    reject_sensitive_config,
    validate_auth_ref_reference,
)
from sqlalchemy.orm import Session

FORBIDDEN_EXPORT_KEYS = {
    "storage_uri",
    "preview_uri",
    "thumbnail_uri",
    "object_storage_path",
    "filesystem_path",
    "file_path",
    "path",
    "base64",
    "bytes",
    "raw_prompt",
    "raw_output",
    "prompt_snapshot",
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
FORBIDDEN_VALUE_MARKERS = (
    "media://",
    "file://",
    "s3://",
    "gs://",
    "storage_uri",
    "base64,",
    "raw_prompt",
    "raw_output",
    "prompt_snapshot",
    "/tmp/",
    "/root/",
    "api_key",
    "bearer ",
)
REDACTED = "[redacted]"


class PackageContractService:
    def __init__(
        self,
        session: Session,
        *,
        plugin_registry: PluginRegistry | None = None,
    ) -> None:
        self._session = session
        self._plugin_registry = plugin_registry or get_builtin_plugin_registry()

    def validate_package_contract(
        self,
        world_id: uuid.UUID,
        request: PackageContractValidationRequest,
    ) -> PackageContractValidationResult:
        issues: list[PackageContractIssue] = []
        issues.extend(_safety_issues(request.metadata.safety_notes, "metadata.safety_notes"))
        for index, plugin in enumerate(request.plugins):
            field = f"plugins[{index}]"
            issues.extend(_safety_issues(plugin.config_schema, f"{field}.config_schema"))
            issues.extend(_safety_issues(plugin.config_template, f"{field}.config_template"))
            issues.extend(_safety_issues(plugin.safety_notes, f"{field}.safety_notes"))
            try:
                definition = self._plugin_registry.get(plugin.plugin_identifier)
            except PluginNotFoundError:
                issues.append(
                    _blocker(
                        "missing_plugin",
                        f"{field}.plugin_identifier",
                        "Package references a plugin that is not registered.",
                    )
                )
                continue
            if definition.manifest.category != plugin.category:
                issues.append(
                    _blocker(
                        "plugin_category_mismatch",
                        f"{field}.category",
                        "Package plugin category does not match the registered plugin.",
                    )
                )
            registered_capabilities = set(definition.manifest.capabilities)
            for capability in plugin.capabilities:
                if capability not in registered_capabilities:
                    issues.append(
                        _blocker(
                            "unknown_plugin_capability",
                            f"{field}.capabilities",
                            "Package declares a plugin capability not present in the registry.",
                        )
                    )
            if plugin.config_template:
                try:
                    self._plugin_registry.validate_config(
                        plugin.plugin_identifier,
                        plugin.config_template,
                    )
                except PluginConfigValidationError:
                    issues.append(
                        _blocker(
                            "invalid_plugin_config_template",
                            f"{field}.config_template",
                            "Package plugin config template does not match the registered schema.",
                        )
                    )

        known_provider_capabilities = self._provider_capability_keys(world_id)
        for index, provider in enumerate(request.providers):
            field = f"providers[{index}]"
            issues.extend(_safety_issues(provider.config_template, f"{field}.config_template"))
            issues.extend(
                _safety_issues(
                    provider.default_params_template,
                    f"{field}.default_params_template",
                )
            )
            issues.extend(_safety_issues(provider.safety_notes, f"{field}.safety_notes"))
            try:
                validate_provider_adapter_compatibility(
                    provider.provider_kind,
                    provider.adapter_kind,
                )
            except ProviderRoutingError:
                issues.append(
                    _blocker(
                        "provider_adapter_mismatch",
                        f"{field}.adapter_kind",
                        "Package provider adapter does not support the declared provider kind.",
                    )
                )
            try:
                validate_auth_ref_reference(provider.auth_ref)
            except ProviderSecretValidationError:
                issues.append(
                    _blocker(
                        "invalid_auth_ref",
                        f"{field}.auth_ref",
                        "Package provider auth_ref must be an opaque secret reference.",
                    )
            )
            for capability_key in provider.capability_keys:
                if (
                    known_provider_capabilities
                    and capability_key not in known_provider_capabilities
                ):
                    issues.append(
                        _warning(
                            "provider_capability_not_installed",
                            f"{field}.capability_keys",
                            (
                                "Package declares a provider capability not present "
                                "in current integrations."
                            ),
                        )
                    )

        blockers = [
            issue for issue in issues if issue.severity == PackageContractIssueSeverity.BLOCKER
        ]
        warnings = [
            issue for issue in issues if issue.severity == PackageContractIssueSeverity.WARNING
        ]
        status = (
            PackageSafetyReviewStatus.BLOCKED
            if blockers
            else request.metadata.safety_review_status
        )
        return PackageContractValidationResult(
            metadata=request.metadata,
            issues=tuple(issues),
            blocker_count=len(blockers),
            warning_count=len(warnings),
            safety_review_status=status,
            provider_execution=False,
            marketplace_install=False,
            resolved_secrets=False,
        )

    def export_provider_configs(
        self,
        world_id: uuid.UUID,
        *,
        platform_admin: bool,
        include_global: bool = True,
        include_hidden: bool = False,
    ) -> PackageProviderConfigExport:
        registry = ProviderRegistryService(self._session)
        effective_include_global = include_global and platform_admin
        providers = registry.list_providers(
            world_id,
            ProviderIntegrationListFilters(
                include_global=effective_include_global,
                include_hidden=include_hidden,
            ),
            platform_admin=platform_admin,
        )
        exports: list[PackageProviderConfigExportItem] = []
        for provider in providers:
            capabilities = tuple(
                PackageProviderCapabilityExport(
                    capability_key=capability.capability_key,
                    capability_json=_safe_export_json(capability.capability_json),
                )
                for capability in registry.list_capabilities(
                    world_id,
                    provider.id,
                    platform_admin=platform_admin,
                )
            )
            exports.append(
                PackageProviderConfigExportItem(
                    provider_id=provider.id,
                    scope_kind=provider.scope_kind,
                    scope_key=provider.scope_key,
                    provider_kind=provider.provider_kind,
                    adapter_kind=provider.adapter_kind,
                    provider_key=provider.provider_key,
                    display_name=provider.display_name,
                    auth_ref=provider.auth_ref,
                    auth_ref_configured=provider.auth_ref_configured,
                    config_json=_safe_export_json(provider.config_json),
                    default_params_json=_safe_export_json(provider.default_params_json),
                    capabilities=capabilities,
                    status=provider.status,
                    visibility=provider.visibility,
                )
            )
        return PackageProviderConfigExport(
            providers=tuple(exports),
            issues=(),
            provider_execution=False,
            marketplace_install=False,
            resolved_secrets=False,
        )

    def _provider_capability_keys(self, world_id: uuid.UUID) -> set[str]:
        registry = ProviderRegistryService(self._session)
        providers = registry.list_providers(
            world_id,
            ProviderIntegrationListFilters(include_global=True),
            platform_admin=True,
        )
        keys: set[str] = set()
        for provider in providers:
            keys.update(
                capability.capability_key
                for capability in registry.list_capabilities(
                    world_id,
                    provider.id,
                    platform_admin=True,
                )
            )
        return keys


def _safety_issues(value: dict[str, Any], field: str) -> list[PackageContractIssue]:
    issues: list[PackageContractIssue] = []
    try:
        reject_sensitive_config(value, field_name=field)
    except ProviderSecretValidationError:
        issues.append(
            _blocker(
                "forbidden_config_key",
                field,
                "Package contract contains a forbidden secret-bearing key.",
            )
        )
    if _contains_forbidden_export_marker(value):
        issues.append(
            _blocker(
                "forbidden_config_marker",
                field,
                "Package contract contains a forbidden storage, prompt, binary, or secret marker.",
            )
        )
    return issues


def _contains_forbidden_export_marker(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).strip().lower() in FORBIDDEN_EXPORT_KEYS
            or _contains_forbidden_export_marker(child)
            for key, child in value.items()
        )
    if isinstance(value, list | tuple):
        return any(_contains_forbidden_export_marker(child) for child in value)
    if isinstance(value, str):
        normalized = value.lower()
        return any(marker in normalized for marker in FORBIDDEN_VALUE_MARKERS)
    return False


def _safe_export_json(value: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, child in value.items():
        if str(key).strip().lower() in FORBIDDEN_EXPORT_KEYS:
            continue
        safe[str(key)] = _safe_export_value(child)
    return safe


def _safe_export_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _safe_export_json(value)
    if isinstance(value, list):
        return [_safe_export_value(item) for item in value]
    if isinstance(value, tuple):
        return [_safe_export_value(item) for item in value]
    if isinstance(value, str):
        normalized = value.lower()
        if any(marker in normalized for marker in FORBIDDEN_VALUE_MARKERS):
            return REDACTED
    return value


def _blocker(code: str, field: str, message: str) -> PackageContractIssue:
    return PackageContractIssue(
        severity=PackageContractIssueSeverity.BLOCKER,
        code=code,
        field=field,
        message=message,
    )


def _warning(code: str, field: str, message: str) -> PackageContractIssue:
    return PackageContractIssue(
        severity=PackageContractIssueSeverity.WARNING,
        code=code,
        field=field,
        message=message,
    )
