from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

LEAKY_KEYS = {
    "storage_uri",
    "preview_uri",
    "thumbnail_uri",
    "base64",
    "bytes",
    "path",
    "file_path",
    "filesystem_path",
    "object_storage_path",
    "object_path",
    "prompt_snapshot",
    "prompt_snapshot_id",
    "raw_prompt",
    "raw_output",
    "raw_source",
    "full_raw_source",
}
LEAKY_KEY_MARKERS = {re.sub(r"[^a-z0-9]+", "", key.lower()) for key in LEAKY_KEYS}


class AuthoringSourceBatchStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class AuthoringSourceVisibility(StrEnum):
    PRIVATE = "private"
    WORLD_ADMIN = "world_admin"
    WORLD_MEMBER = "world_member"
    DEVELOPER_ONLY = "developer_only"


class AuthoringSourceAssetKind(StrEnum):
    SCRIPT = "script"
    LORE = "lore"
    CHARACTER_SHEET = "character_sheet"
    LOCATION_SHEET = "location_sheet"
    IMAGE = "image"
    AUDIO = "audio"
    DOCUMENT = "document"
    LEGACY_REFERENCE = "legacy_reference"
    OTHER = "other"


class AuthoringSourceFragmentKind(StrEnum):
    DIALOGUE = "dialogue"
    LORE = "lore"
    CHARACTER = "character"
    RELATIONSHIP = "relationship"
    ASSET = "asset"
    MEMORY = "memory"
    SCENE = "scene"
    OTHER = "other"


class AuthoringImportRunKind(StrEnum):
    MANUAL = "manual"
    PREVIEW = "preview"
    APPLY = "apply"


class AuthoringImportRunStatus(StrEnum):
    DRAFT = "draft"
    PREVIEWED = "previewed"
    APPLIED = "applied"
    FAILED = "failed"


class AuthoringScriptParserMode(StrEnum):
    DETERMINISTIC = "deterministic"


class AuthoringCharacterExtractorMode(StrEnum):
    DETERMINISTIC = "deterministic"


class AuthoringLoreExtractorMode(StrEnum):
    DETERMINISTIC = "deterministic"


class AuthoringConflictReviewMode(StrEnum):
    DETERMINISTIC = "deterministic"


class AuthoringMemoryMigrationMode(StrEnum):
    DETERMINISTIC = "deterministic"


class AuthoringAssetMatchingMode(StrEnum):
    DETERMINISTIC = "deterministic"


class AuthoringCharacterMemoryDistillationMode(StrEnum):
    PROVIDER_BACKED = "provider_backed"


class DemoWorldAssemblyMode(StrEnum):
    DETERMINISTIC = "deterministic"


class BetaContentRepairKind(StrEnum):
    PERSONA = "persona"
    MEMORY = "memory"
    DIALOGUE_STYLE = "dialogue_style"
    SPRITE_BINDING = "sprite_binding"
    VOICE_BINDING = "voice_binding"
    BACKGROUND_BINDING = "background_binding"
    PROVIDER_PROFILE = "provider_profile"
    VISUAL_GENERATION_PROFILE = "visual_generation_profile"
    ROUTE = "route"


class GalgameSourceIntakeFileStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SKIPPED = "skipped"


class GalgameSourceIntakeAssetRole(StrEnum):
    CHARACTER_SPRITE = "character_sprite"
    EXPRESSION_VARIANT = "expression_variant"
    BACKGROUND = "background"
    CG = "cg"
    VOICE_REFERENCE = "voice_reference"
    BGM = "bgm"
    SOUND_EFFECT = "sound_effect"
    SCRIPT_DIALOGUE = "script_dialogue"
    CHARACTER_PROFILE = "character_profile"
    ROUTE_CHOICE = "route_choice"
    OTHER = "other"


class AuthoringProposalKind(StrEnum):
    DIALOGUE = "dialogue"
    CHARACTER = "character"
    RELATIONSHIP = "relationship"
    LORE = "lore"
    ASSET_MATCH = "asset_match"
    MEMORY = "memory"
    OTHER = "other"


class AuthoringProposalStatus(StrEnum):
    PROPOSED = "proposed"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    BLOCKED = "blocked"


class AuthoringReviewDecisionKind(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    NEEDS_CHANGES = "needs_changes"
    DISMISS = "dismiss"


class AuthoringTraceKind(StrEnum):
    PROPOSAL_CREATED = "proposal_created"
    PROPOSAL_REVIEWED = "proposal_reviewed"
    PROPOSAL_APPLIED = "proposal_applied"
    APPLY_BLOCKED = "apply_blocked"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class AuthoringSourceBatchCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    batch_key: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    source_kind: AuthoringSourceAssetKind = AuthoringSourceAssetKind.OTHER
    status: AuthoringSourceBatchStatus = AuthoringSourceBatchStatus.ACTIVE
    visibility: AuthoringSourceVisibility = AuthoringSourceVisibility.PRIVATE
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("batch_key", mode="after")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        return _normalize_key(value, "batch_key")

    @field_validator("metadata_json", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value, "source batch metadata")
        return value


class AuthoringSourceBatchRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    batch_key: str
    display_name: str
    description: str | None
    source_kind: AuthoringSourceAssetKind
    status: AuthoringSourceBatchStatus
    visibility: AuthoringSourceVisibility
    metadata_json: dict[str, Any]
    created_by_actor_ref: str
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class AuthoringSourceAssetCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    batch_id: uuid.UUID
    media_asset_id: uuid.UUID | None = None
    source_asset_kind: AuthoringSourceAssetKind = AuthoringSourceAssetKind.OTHER
    source_label: str = Field(min_length=1, max_length=160)
    source_ref: str | None = Field(default=None, max_length=240)
    status: AuthoringSourceBatchStatus = AuthoringSourceBatchStatus.ACTIVE
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata_json", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value, "source asset metadata")
        return value


class AuthoringSourceAssetRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    batch_id: uuid.UUID
    media_asset_id: uuid.UUID | None
    source_asset_kind: AuthoringSourceAssetKind
    source_label: str
    source_ref: str | None
    status: AuthoringSourceBatchStatus
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class AuthoringSourceFragmentCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    source_asset_id: uuid.UUID
    fragment_key: str = Field(min_length=1, max_length=120)
    fragment_kind: AuthoringSourceFragmentKind = AuthoringSourceFragmentKind.OTHER
    sequence: int = Field(ge=0)
    excerpt_text: str | None = Field(default=None, max_length=4000)
    locator_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("fragment_key", mode="after")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        return _normalize_key(value, "fragment_key")

    @field_validator("locator_json", "metadata_json", mode="after")
    @classmethod
    def validate_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value, "source fragment JSON")
        return value

    @field_validator("excerpt_text", mode="after")
    @classmethod
    def validate_excerpt(cls, value: str | None) -> str | None:
        if value is not None:
            _reject_leaky_text(value)
        return value


class AuthoringSourceFragmentRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    source_asset_id: uuid.UUID
    fragment_key: str
    fragment_kind: AuthoringSourceFragmentKind
    sequence: int
    excerpt_text: str | None
    locator_json: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class AuthoringProposalDraft(_FrozenContract):
    source_fragment_id: uuid.UUID | None = None
    proposal_kind: AuthoringProposalKind = AuthoringProposalKind.OTHER
    target_ref_kind: str | None = Field(default=None, max_length=60)
    target_ref_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=2000)
    proposed_payload_json: dict[str, Any] = Field(default_factory=dict)
    evidence_json: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0, le=1)
    priority: int = Field(default=100, ge=0)

    @field_validator("proposed_payload_json", "evidence_json", mode="after")
    @classmethod
    def validate_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value, "authoring proposal JSON")
        return value


class AuthoringImportRunCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    source_batch_id: uuid.UUID | None = None
    run_kind: AuthoringImportRunKind = AuthoringImportRunKind.PREVIEW
    summary_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("summary_json", mode="after")
    @classmethod
    def validate_summary(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value, "import run summary")
        return value


class AuthoringProposalCreate(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    run_id: uuid.UUID
    source_fragment_id: uuid.UUID | None = None
    proposal_kind: AuthoringProposalKind = AuthoringProposalKind.OTHER
    target_ref_kind: str | None = Field(default=None, max_length=60)
    target_ref_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=2000)
    proposed_payload_json: dict[str, Any] = Field(default_factory=dict)
    evidence_json: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0, le=1)
    priority: int = Field(default=100, ge=0)
    status: AuthoringProposalStatus = AuthoringProposalStatus.PROPOSED

    @classmethod
    def from_draft(
        cls,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        run_id: uuid.UUID,
        draft: AuthoringProposalDraft,
    ) -> AuthoringProposalCreate:
        return cls(
            world_id=world_id,
            worldline_id=worldline_id,
            run_id=run_id,
            **draft.model_dump(),
        )

    @field_validator("proposed_payload_json", "evidence_json", mode="after")
    @classmethod
    def validate_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value, "authoring proposal JSON")
        return value


class AuthoringProposalRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    run_id: uuid.UUID
    source_fragment_id: uuid.UUID | None
    proposal_kind: AuthoringProposalKind
    target_ref_kind: str | None
    target_ref_id: uuid.UUID | None
    title: str
    summary: str
    proposed_payload_json: dict[str, Any]
    evidence_json: dict[str, Any]
    confidence: float | None
    priority: int
    status: AuthoringProposalStatus
    applied_ref_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class AuthoringImportRunRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    source_batch_id: uuid.UUID | None
    run_kind: AuthoringImportRunKind
    status: AuthoringImportRunStatus
    summary_json: dict[str, Any]
    created_by_actor_ref: str
    created_at: datetime
    updated_at: datetime
    proposals: list[AuthoringProposalRead] = Field(default_factory=list)

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class AuthoringReviewDecisionCreate(_FrozenContract):
    decision: AuthoringReviewDecisionKind
    reason: str | None = Field(default=None, max_length=2000)
    decision_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("decision_json", mode="after")
    @classmethod
    def validate_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value, "review decision JSON")
        return value


class AuthoringReviewDecisionRead(_FrozenContract):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    proposal_id: uuid.UUID
    decision: AuthoringReviewDecisionKind
    reason: str | None
    decision_json: dict[str, Any]
    decided_by_actor_ref: str
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _utc(value)


class AuthoringPreviewRequest(_FrozenContract):
    worldline_id: uuid.UUID
    proposals: tuple[AuthoringProposalDraft, ...] = ()


class AuthoringPreviewResult(_FrozenContract):
    run: AuthoringImportRunRead


class AuthoringScriptParseRequest(_FrozenContract):
    worldline_id: uuid.UUID
    source_fragment_ids: tuple[uuid.UUID, ...]
    parser_mode: AuthoringScriptParserMode = AuthoringScriptParserMode.DETERMINISTIC

    @model_validator(mode="after")
    def validate_fragments(self) -> AuthoringScriptParseRequest:
        if not self.source_fragment_ids:
            raise ValueError("source_fragment_ids is required")
        return self


class AuthoringScriptParseResult(_FrozenContract):
    run: AuthoringImportRunRead
    created_proposal_count: int
    dialogue_count: int
    scene_count: int
    choice_count: int
    route_count: int
    event_count: int
    emotion_hint_count: int = 0
    relationship_hint_count: int = 0
    manual_label_count: int = 0
    unresolved_speaker_count: int


class AuthoringCharacterExtractRequest(_FrozenContract):
    worldline_id: uuid.UUID
    source_fragment_ids: tuple[uuid.UUID, ...]
    extractor_mode: AuthoringCharacterExtractorMode = (
        AuthoringCharacterExtractorMode.DETERMINISTIC
    )
    include_dialogue_proposals: bool = True

    @model_validator(mode="after")
    def validate_fragments(self) -> AuthoringCharacterExtractRequest:
        if not self.source_fragment_ids:
            raise ValueError("source_fragment_ids is required")
        return self


class AuthoringCharacterExtractResult(_FrozenContract):
    run: AuthoringImportRunRead
    created_proposal_count: int
    character_count: int
    relationship_count: int
    alias_count: int
    faction_count: int
    identity_count: int
    emotional_baseline_count: int


class AuthoringLoreExtractRequest(_FrozenContract):
    worldline_id: uuid.UUID
    source_fragment_ids: tuple[uuid.UUID, ...]
    extractor_mode: AuthoringLoreExtractorMode = AuthoringLoreExtractorMode.DETERMINISTIC

    @model_validator(mode="after")
    def validate_fragments(self) -> AuthoringLoreExtractRequest:
        if not self.source_fragment_ids:
            raise ValueError("source_fragment_ids is required")
        return self


class AuthoringLoreExtractResult(_FrozenContract):
    run: AuthoringImportRunRead
    created_proposal_count: int
    lore_count: int
    location_count: int
    organization_count: int
    world_rule_count: int
    secret_count: int
    knowledge_boundary_count: int
    uncertain_count: int


class AuthoringConflictReviewRequest(_FrozenContract):
    worldline_id: uuid.UUID
    review_mode: AuthoringConflictReviewMode = AuthoringConflictReviewMode.DETERMINISTIC
    include_statuses: tuple[AuthoringProposalStatus, ...] = (
        AuthoringProposalStatus.PROPOSED,
        AuthoringProposalStatus.REVIEWED,
        AuthoringProposalStatus.APPROVED,
    )

    @model_validator(mode="after")
    def validate_statuses(self) -> AuthoringConflictReviewRequest:
        if not self.include_statuses:
            raise ValueError("include_statuses is required")
        return self


class AuthoringConflictReviewResult(_FrozenContract):
    run: AuthoringImportRunRead
    created_proposal_count: int
    duplicate_count: int
    contradiction_count: int
    uncertain_count: int
    ooc_risk_count: int


class AuthoringMemoryMigrateRequest(_FrozenContract):
    worldline_id: uuid.UUID
    source_fragment_ids: tuple[uuid.UUID, ...]
    migration_mode: AuthoringMemoryMigrationMode = AuthoringMemoryMigrationMode.DETERMINISTIC
    include_proposals: bool = True

    @model_validator(mode="after")
    def validate_fragments(self) -> AuthoringMemoryMigrateRequest:
        if not self.source_fragment_ids:
            raise ValueError("source_fragment_ids is required")
        return self


class AuthoringMemoryMigrateResult(_FrozenContract):
    run: AuthoringImportRunRead
    created_proposal_count: int
    fact_count: int
    episodic_count: int
    relationship_count: int
    preference_count: int
    style_count: int


class AuthoringCharacterMemoryDistillRequest(_FrozenContract):
    worldline_id: uuid.UUID
    agent_id: uuid.UUID
    source_fragment_ids: tuple[uuid.UUID, ...]
    provider_id: uuid.UUID
    model_name: str | None = Field(default=None, min_length=1, max_length=200)
    distillation_mode: AuthoringCharacterMemoryDistillationMode = (
        AuthoringCharacterMemoryDistillationMode.PROVIDER_BACKED
    )
    include_visual_profile_recommendation: bool = True

    @model_validator(mode="after")
    def validate_fragments(self) -> AuthoringCharacterMemoryDistillRequest:
        if not self.source_fragment_ids:
            raise ValueError("source_fragment_ids is required")
        return self


class AuthoringCharacterMemoryDistillResult(_FrozenContract):
    run: AuthoringImportRunRead
    created_proposal_count: int
    persona_proposal_count: int
    memory_candidate_count: int
    visual_profile_recommendation_count: int
    model_invocation_id: uuid.UUID
    provider_execution: bool = True


class AuthoringAssetMatchRequest(_FrozenContract):
    worldline_id: uuid.UUID
    source_asset_ids: tuple[uuid.UUID, ...] = ()
    source_fragment_ids: tuple[uuid.UUID, ...] = ()
    matching_mode: AuthoringAssetMatchingMode = AuthoringAssetMatchingMode.DETERMINISTIC
    include_visual_matches: bool = True
    include_voice_matches: bool = True
    include_cg_matches: bool = True

    @model_validator(mode="after")
    def validate_sources(self) -> AuthoringAssetMatchRequest:
        if not self.source_asset_ids and not self.source_fragment_ids:
            raise ValueError("source_asset_ids or source_fragment_ids is required")
        return self


class AuthoringAssetMatchResult(_FrozenContract):
    run: AuthoringImportRunRead
    created_proposal_count: int
    sprite_match_count: int
    background_match_count: int
    cg_match_count: int
    voice_match_count: int
    blocked_count: int


class DemoWorldAssemblyRequest(_FrozenContract):
    worldline_id: uuid.UUID
    agent_ids: tuple[uuid.UUID, ...]
    dialogue_proposal_ids: tuple[uuid.UUID, ...]
    persona_proposal_ids: tuple[uuid.UUID, ...] = ()
    memory_proposal_ids: tuple[uuid.UUID, ...] = ()
    visual_proposal_ids: tuple[uuid.UUID, ...] = ()
    voice_proposal_ids: tuple[uuid.UUID, ...] = ()
    visual_profile_proposal_ids: tuple[uuid.UUID, ...] = ()
    visual_generation_profile_ids: tuple[uuid.UUID, ...] = ()
    title: str = Field(default="Self-use MVP Demo World", min_length=1, max_length=160)
    session_key: str | None = Field(default=None, min_length=3, max_length=80)
    opening_prompt: str = Field(default="Begin the demo world conversation.", max_length=4000)
    objective: str = Field(default="Play a source-grounded self-use demo world.", max_length=4000)
    max_turns: int = Field(default=48, ge=2, le=200)
    assembly_mode: DemoWorldAssemblyMode = DemoWorldAssemblyMode.DETERMINISTIC
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata_json", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value, "demo assembly metadata")
        return value

    @model_validator(mode="after")
    def validate_request(self) -> DemoWorldAssemblyRequest:
        if not 2 <= len(self.agent_ids) <= 3:
            raise ValueError("demo assembly requires 2-3 agents")
        if len(set(self.agent_ids)) != len(self.agent_ids):
            raise ValueError("demo assembly agents must be unique")
        if not self.dialogue_proposal_ids:
            raise ValueError("dialogue_proposal_ids is required")
        return self


class DemoWorldAssemblyResult(_FrozenContract):
    run: AuthoringImportRunRead
    proposal: AuthoringProposalRead
    report_json: dict[str, Any]
    created_proposal_count: int = 1
    provider_execution: bool = False


class BetaContentRepairCandidate(_FrozenContract):
    repair_kind: BetaContentRepairKind
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=2000)
    target_ref_id: uuid.UUID | None = None
    source_fragment_id: uuid.UUID | None = None
    feedback_report_ids: tuple[uuid.UUID, ...] = ()
    diagnostic_refs: tuple[dict[str, Any], ...] = ()
    proposed_payload_json: dict[str, Any] = Field(default_factory=dict)
    evidence_json: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0, le=1)
    priority: int = Field(default=100, ge=0)

    @field_validator("proposed_payload_json", "evidence_json", mode="after")
    @classmethod
    def validate_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value, "beta repair JSON")
        return value

    @field_validator("diagnostic_refs", mode="after")
    @classmethod
    def validate_diagnostic_refs(
        cls,
        value: tuple[dict[str, Any], ...],
    ) -> tuple[dict[str, Any], ...]:
        for item in value:
            _assert_safe_json(item, "beta repair diagnostic refs")
        return value


class BetaContentRepairRequest(_FrozenContract):
    worldline_id: uuid.UUID
    candidates: tuple[BetaContentRepairCandidate, ...]
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata_json", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value, "beta repair metadata")
        return value

    @model_validator(mode="after")
    def validate_candidates(self) -> BetaContentRepairRequest:
        if not self.candidates:
            raise ValueError("repair candidates are required")
        return self


class BetaContentRepairImpact(_FrozenContract):
    proposal_count: int = 0
    feedback_report_count: int = 0
    repair_counts: dict[str, int] = Field(default_factory=dict)
    provider_execution: bool = False
    canonical_mutation: bool = False


class BetaContentRepairResult(_FrozenContract):
    run: AuthoringImportRunRead
    proposals: tuple[AuthoringProposalRead, ...]
    impact: BetaContentRepairImpact
    report_json: dict[str, Any]


class GalgameSourceIntakePreviewRequest(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    source_directory: str = Field(min_length=1, max_length=1000)
    batch_key: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    max_text_fragment_chars: int = Field(default=2000, ge=200, le=4000)
    max_files: int = Field(default=500, ge=1, le=5000)

    @field_validator("batch_key", mode="after")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        return _normalize_key(value, "batch_key")


class GalgameSourceIntakeApplyRequest(GalgameSourceIntakePreviewRequest):
    confirm_already_unpacked_user_provided: bool = False

    @model_validator(mode="after")
    def validate_confirmation(self) -> GalgameSourceIntakeApplyRequest:
        if not self.confirm_already_unpacked_user_provided:
            raise ValueError("already-unpacked user-provided confirmation is required")
        return self


class GalgameSourceIntakeFilePreview(_FrozenContract):
    source_ref: str
    file_name: str
    status: GalgameSourceIntakeFileStatus
    asset_role: GalgameSourceIntakeAssetRole
    source_asset_kind: AuthoringSourceAssetKind
    media_asset_kind: str | None = None
    media_asset_role: str | None = None
    mime_type: str | None = None
    size_bytes: int = Field(ge=0)
    fragment_count: int = Field(default=0, ge=0)
    reason: str | None = None


class GalgameSourceIntakePreviewResult(_FrozenContract):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    batch_key: str
    display_name: str
    root_label: str
    accepted_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    media_file_count: int = Field(ge=0)
    text_file_count: int = Field(ge=0)
    fragment_count: int = Field(ge=0)
    provider_execution: bool = False
    canon_mutation: bool = False
    files: tuple[GalgameSourceIntakeFilePreview, ...]


class GalgameSourceIntakeApplyResult(_FrozenContract):
    preview: GalgameSourceIntakePreviewResult
    batch: AuthoringSourceBatchRead
    run: AuthoringImportRunRead
    source_assets: tuple[AuthoringSourceAssetRead, ...]
    source_fragments: tuple[AuthoringSourceFragmentRead, ...]
    media_asset_ids: tuple[uuid.UUID, ...]


class AuthoringApplyRequest(_FrozenContract):
    worldline_id: uuid.UUID
    proposal_ids: tuple[uuid.UUID, ...]

    @model_validator(mode="after")
    def validate_proposals(self) -> AuthoringApplyRequest:
        if not self.proposal_ids:
            raise ValueError("proposal_ids is required")
        return self


class AuthoringApplyResult(_FrozenContract):
    run: AuthoringImportRunRead
    applied_proposals: list[AuthoringProposalRead]
    blocked_proposals: list[AuthoringProposalRead]


def _assert_safe_json(value: dict[str, Any], field_name: str) -> None:
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be JSON serializable") from exc
    _reject_leaky_json(value)


def _is_leaky_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "", key.lower())
    return normalized in LEAKY_KEY_MARKERS


def _reject_leaky_json(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if _is_leaky_key(str(key)):
                raise ValueError(f"{key} is not allowed in authoring JSON")
            _reject_leaky_json(item)
    elif isinstance(value, list | tuple):
        for item in value:
            _reject_leaky_json(item)
    elif isinstance(value, str):
        _reject_leaky_text(value)


def _reject_leaky_text(value: str) -> None:
    lowered = value.lower()
    if lowered.startswith(("local://", "file://")):
        raise ValueError("storage or file paths are not allowed in authoring JSON")
    if lowered.startswith("data:") or "base64," in lowered:
        raise ValueError("base64 data is not allowed in authoring JSON")


def _normalize_key(value: str, field_name: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
