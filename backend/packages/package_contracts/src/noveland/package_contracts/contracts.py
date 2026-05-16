from __future__ import annotations

import re
import uuid
from enum import StrEnum
from typing import Any

from noveland.plugins import PluginCategory
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderIntegrationStatus,
    ProviderKind,
    ProviderScopeKind,
    ProviderVisibility,
)
from pydantic import BaseModel, ConfigDict, Field, field_validator

PACKAGE_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")


class PackageContractIssueSeverity(StrEnum):
    BLOCKER = "blocker"
    WARNING = "warning"


class PackageSafetyReviewStatus(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    BLOCKED = "blocked"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class PackageContractIssue(_FrozenContract):
    severity: PackageContractIssueSeverity
    code: str = Field(min_length=1, max_length=80)
    field: str = Field(min_length=1, max_length=240)
    message: str = Field(min_length=1, max_length=400)


class PackageMetadata(_FrozenContract):
    package_key: str = Field(min_length=1, max_length=80)
    version: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    publisher_ref: str | None = Field(default=None, max_length=160)
    safety_review_status: PackageSafetyReviewStatus = PackageSafetyReviewStatus.DRAFT
    safety_notes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("package_key", mode="after")
    @classmethod
    def validate_package_key(cls, value: str) -> str:
        normalized = value.strip().lower()
        if PACKAGE_KEY_PATTERN.fullmatch(normalized) is None:
            raise ValueError(
                "package_key must use lowercase letters, numbers, dashes, or underscores"
            )
        return normalized


class PluginPackageDeclaration(_FrozenContract):
    plugin_identifier: str = Field(min_length=1, max_length=120)
    category: PluginCategory
    version: str | None = Field(default=None, min_length=1, max_length=80)
    capabilities: tuple[str, ...] = Field(default_factory=tuple)
    config_schema: dict[str, Any] = Field(default_factory=dict)
    config_template: dict[str, Any] = Field(default_factory=dict)
    safety_notes: dict[str, Any] = Field(default_factory=dict)


class PackageProviderDeclaration(_FrozenContract):
    provider_kind: ProviderKind
    adapter_kind: ProviderAdapterKind
    capability_keys: tuple[str, ...] = Field(default_factory=tuple)
    config_template: dict[str, Any] = Field(default_factory=dict)
    default_params_template: dict[str, Any] = Field(default_factory=dict)
    auth_ref: str | None = Field(default=None, min_length=1, max_length=200)
    safety_notes: dict[str, Any] = Field(default_factory=dict)


class PackageContractValidationRequest(_FrozenContract):
    metadata: PackageMetadata
    plugins: tuple[PluginPackageDeclaration, ...] = Field(default_factory=tuple)
    providers: tuple[PackageProviderDeclaration, ...] = Field(default_factory=tuple)


class PackageContractValidationResult(_FrozenContract):
    metadata: PackageMetadata
    issues: tuple[PackageContractIssue, ...]
    blocker_count: int
    warning_count: int
    safety_review_status: PackageSafetyReviewStatus
    provider_execution: bool = False
    marketplace_install: bool = False
    resolved_secrets: bool = False


class PackageProviderCapabilityExport(_FrozenContract):
    capability_key: str
    capability_json: dict[str, Any]


class PackageProviderConfigExportItem(_FrozenContract):
    provider_id: uuid.UUID
    scope_kind: ProviderScopeKind
    scope_key: str
    provider_kind: ProviderKind
    adapter_kind: ProviderAdapterKind
    provider_key: str
    display_name: str
    auth_ref: str | None
    auth_ref_configured: bool
    config_json: dict[str, Any]
    default_params_json: dict[str, Any]
    capabilities: tuple[PackageProviderCapabilityExport, ...]
    status: ProviderIntegrationStatus
    visibility: ProviderVisibility
    safety_review_status: PackageSafetyReviewStatus = PackageSafetyReviewStatus.PENDING_REVIEW


class PackageProviderConfigExport(_FrozenContract):
    providers: tuple[PackageProviderConfigExportItem, ...]
    issues: tuple[PackageContractIssue, ...] = Field(default_factory=tuple)
    provider_execution: bool = False
    marketplace_install: bool = False
    resolved_secrets: bool = False
