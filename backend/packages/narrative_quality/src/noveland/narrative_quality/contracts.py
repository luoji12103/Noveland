from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from noveland.providers.contracts import ProviderAdapterKind, ProviderKind
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class NarrativeQualityContextKind(StrEnum):
    AGENT = "agent"
    CONVERSATION = "conversation"
    GM = "gm"
    NARRATIVE = "narrative"
    EVAL = "eval"


class NarrativeQualityGMImportance(StrEnum):
    DAILY = "daily"
    RELATIONSHIP = "relationship"
    ORGANIZATION = "organization"
    ROUTE = "route"
    MAIN_PLOT = "main_plot"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class NarrativeQualityEvidenceRef(_FrozenContract):
    kind: str = Field(min_length=1, max_length=120)
    id: str = Field(min_length=1, max_length=200)


class NarrativeQualityContextPreviewRequest(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    context_kind: NarrativeQualityContextKind
    agent_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    limit: int = Field(default=5, ge=1, le=20)

    @model_validator(mode="after")
    def validate_subject(self) -> NarrativeQualityContextPreviewRequest:
        if self.context_kind == NarrativeQualityContextKind.AGENT and self.agent_id is None:
            raise ValueError("agent context requires agent_id")
        if (
            self.context_kind == NarrativeQualityContextKind.CONVERSATION
            and self.conversation_id is None
        ):
            raise ValueError("conversation context requires conversation_id")
        return self


class NarrativeQualityContextPreview(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    context_kind: NarrativeQualityContextKind
    subject_ref: str
    prompt_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[NarrativeQualityEvidenceRef] = Field(default_factory=list)
    generated_at: datetime

    @field_validator("generated_at", mode="after")
    @classmethod
    def normalize_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class NarrativeQualityGMProposalGenerateRequest(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    provider_id: uuid.UUID | None = None
    capability_key: str | None = Field(default=None, min_length=1, max_length=120)
    model_name: str | None = Field(default=None, min_length=1, max_length=200)
    prompt_goal: str = Field(min_length=1, max_length=1200)
    title: str | None = Field(default=None, min_length=1, max_length=160)
    event_name: str = Field(default="gm.provider_proposal", min_length=1, max_length=120)
    importance: NarrativeQualityGMImportance = NarrativeQualityGMImportance.DAILY
    risk_score: int = Field(default=20, ge=0, le=100)
    affected_agents: list[str] = Field(default_factory=list)
    affected_organizations: list[str] = Field(default_factory=list)
    payload_json: dict[str, Any] = Field(default_factory=dict)
    provider_request_json: dict[str, Any] = Field(default_factory=dict)
    context_limit: int = Field(default=5, ge=1, le=20)
    dry_run: bool = False

    @field_validator("event_name", mode="after")
    @classmethod
    def normalize_event_name(cls, value: str) -> str:
        normalized = value.strip()
        if normalized == "":
            raise ValueError("event_name must not be empty")
        return normalized

    @field_validator("prompt_goal", mode="after")
    @classmethod
    def normalize_prompt_goal(cls, value: str) -> str:
        normalized = value.strip()
        if normalized == "":
            raise ValueError("prompt_goal must not be empty")
        return normalized

    @field_validator("title", mode="after")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if normalized == "":
            raise ValueError("title must not be empty")
        return normalized

    @field_validator("affected_agents", "affected_organizations", mode="after")
    @classmethod
    def normalize_string_list(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            text = item.strip()
            if text and text not in normalized:
                normalized.append(text)
        return normalized

    @field_validator("payload_json", "provider_request_json", mode="after")
    @classmethod
    def validate_json_values(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value, "GM proposal JSON")
        return value


class NarrativeQualityProviderRef(_FrozenContract):
    id: uuid.UUID
    provider_kind: ProviderKind
    adapter_kind: ProviderAdapterKind
    provider_key: str


class NarrativeQualityInvocationRef(_FrozenContract):
    id: uuid.UUID
    status: str
    provider_kind: str
    error_text: str | None = None


class NarrativeQualityGMProposalCandidate(_FrozenContract):
    id: uuid.UUID | None = None
    status: str
    title: str
    reason: str
    event_name: str
    proposed_payload: dict[str, Any]
    importance: NarrativeQualityGMImportance
    risk_score: int
    affected_agents: list[str]
    affected_organizations: list[str]
    source_context: dict[str, Any]
    created_at: datetime | None = None

    @field_validator("created_at", mode="after")
    @classmethod
    def normalize_created_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class NarrativeQualityGMProposalGenerationResult(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    dry_run: bool
    provider: NarrativeQualityProviderRef
    invocation: NarrativeQualityInvocationRef
    proposal: NarrativeQualityGMProposalCandidate
    diagnostics: dict[str, Any] = Field(default_factory=dict)


def _assert_json_serializable(value: Any, field_name: str) -> None:
    try:
        import json

        json.dumps(value)
    except TypeError as exc:
        raise ValueError(f"{field_name} must be JSON serializable") from exc
