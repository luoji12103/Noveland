from __future__ import annotations

import builtins
import uuid
from datetime import UTC, datetime

from noveland.adapters.models import ProviderProfile
from noveland.agents.models import Agent, AgentRuntimeRun
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.events.models import WorldEventModel
from noveland.invocations.contracts import (
    AgentRuntimeRunInvocationLinkCreate,
    AgentRuntimeRunInvocationLinkRecord,
    InvocationActorKind,
    InvocationKind,
    InvocationProviderKind,
    InvocationRecordCreate,
    InvocationRecordView,
    InvocationRedactionStatus,
    InvocationRedactRequest,
    InvocationRetentionPolicy,
    InvocationRole,
    InvocationSearchFilters,
    InvocationSearchResult,
    InvocationStatus,
    InvocationStatusUpdate,
    InvocationTagCreate,
    InvocationTagRecord,
    InvocationVisibility,
    PromptSnapshotCreate,
    PromptSnapshotRecord,
    PromptSnapshotUpdate,
    PromptTemplateCreate,
    PromptTemplateRecord,
    PromptTemplateScopeKind,
    PromptTemplateStatus,
    PromptTemplateUpdate,
    RedactionMode,
    SortOrder,
)
from noveland.invocations.models import (
    AgentRuntimeRunModelInvocation,
    ModelInvocation,
    ModelInvocationTag,
    PromptSnapshot,
    PromptTemplate,
)
from noveland.invocations.redaction import (
    checksum_json,
    checksum_text,
    prompt_checksum,
    redaction_status_for_mode,
)
from noveland.media.models import MediaAsset, MediaJob
from noveland.memory.models import MemoryWriteJob
from noveland.worlds.models import World
from noveland.worlds.worldlines import primary_worldline_or_none, worldline_or_404
from sqlalchemy import Select, and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

ADMIN_VISIBLE = {
    InvocationVisibility.PRIVATE.value,
    InvocationVisibility.WORLD_ADMIN.value,
}
PLATFORM_VISIBLE = {
    InvocationVisibility.PRIVATE.value,
    InvocationVisibility.WORLD_ADMIN.value,
    InvocationVisibility.DEVELOPER_ONLY.value,
    InvocationVisibility.HIDDEN.value,
}


class InvocationValidationError(ValueError):
    pass


class InvocationNotFoundError(LookupError):
    pass


class InvocationLedgerService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(self, create: InvocationRecordCreate) -> InvocationRecordView:
        worldline_id = _worldline_id(self._session, create.world_id, create.worldline_id)
        self._validate_refs(create.world_id, worldline_id, create)
        model = ModelInvocation(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=worldline_id,
            trace_id=create.trace_id or uuid.uuid4(),
            parent_invocation_id=create.parent_invocation_id,
            invocation_kind=create.invocation_kind.value,
            actor_kind=create.actor_kind.value,
            actor_ref=create.actor_ref,
            agent_id=create.agent_id,
            conversation_id=create.conversation_id,
            turn_id=create.turn_id,
            world_event_id=create.world_event_id,
            media_job_id=create.media_job_id,
            media_asset_id=create.media_asset_id,
            memory_write_job_id=create.memory_write_job_id,
            provider_kind=create.provider_kind.value,
            provider_profile_id=create.provider_profile_id,
            model_name=create.model_name,
            model_version=create.model_version,
            prompt_template_key=create.prompt_template_key,
            prompt_template_version=create.prompt_template_version,
            input_text=create.input_text,
            output_text=create.output_text,
            input_json=create.input_json,
            output_json=create.output_json,
            request_params_json=create.request_params_json,
            response_metadata_json=create.response_metadata_json,
            usage_json=create.usage_json,
            latency_ms=create.latency_ms,
            estimated_cost=create.estimated_cost,
            status=create.status.value,
            error_text=create.error_text,
            visibility=create.visibility.value,
            redaction_status=create.redaction_status.value,
            retention_policy=create.retention_policy.value,
            contains_sensitive_context=create.contains_sensitive_context,
            purge_after=create.purge_after,
        )
        self._session.add(model)
        self._session.flush()
        if create.prompt_snapshot is not None:
            PromptSnapshotService(self._session).create_snapshot(
                model.id,
                create.prompt_snapshot,
                world_id=create.world_id,
                worldline_id=worldline_id,
            )
        self._session.refresh(model)
        return _invocation_record(model)

    def get(
        self,
        world_id: uuid.UUID,
        invocation_id: uuid.UUID,
        *,
        include_hidden: bool = False,
        platform_admin: bool = False,
    ) -> InvocationRecordView | None:
        model = self._visible_invocation_or_none(
            world_id,
            invocation_id,
            include_hidden=include_hidden,
            platform_admin=platform_admin,
        )
        if model is None:
            return None
        return _invocation_record(model, raw_allowed=_raw_allowed(model, platform_admin))

    def list(
        self,
        world_id: uuid.UUID,
        filters: InvocationSearchFilters,
        *,
        include_hidden: bool = False,
        platform_admin: bool = False,
    ) -> InvocationSearchResult:
        worldline_id = _worldline_id(self._session, world_id, filters.worldline_id)
        statement = select(ModelInvocation).where(
            ModelInvocation.world_id == world_id,
            ModelInvocation.worldline_id == worldline_id,
        )
        statement = _apply_visibility(statement, include_hidden, platform_admin)
        statement = self._apply_filters(statement, filters)
        statement = self._apply_tag_filters(statement, world_id, worldline_id, filters)
        direction = ModelInvocation.created_at.asc()
        if filters.order == SortOrder.DESC:
            direction = ModelInvocation.created_at.desc()
        statement = statement.order_by(direction).limit(filters.limit)
        return InvocationSearchResult(
            invocations=[
                _invocation_record(model, raw_allowed=_raw_allowed(model, platform_admin))
                for model in self._session.scalars(statement).all()
            ]
        )

    def update_status(
        self,
        world_id: uuid.UUID,
        invocation_id: uuid.UUID,
        update: InvocationStatusUpdate,
    ) -> InvocationRecordView:
        model = self._required(world_id, invocation_id)
        model.status = update.status.value
        if update.output_text is not None:
            model.output_text = update.output_text
        if update.output_json is not None:
            model.output_json = update.output_json
        if update.response_metadata_json is not None:
            model.response_metadata_json = update.response_metadata_json
        if update.usage_json is not None:
            model.usage_json = update.usage_json
        if update.latency_ms is not None:
            model.latency_ms = update.latency_ms
        if update.estimated_cost is not None:
            model.estimated_cost = update.estimated_cost
        if update.error_text is not None:
            model.error_text = update.error_text
        self._session.flush()
        self._session.refresh(model)
        return _invocation_record(model)

    def fail(self, world_id: uuid.UUID, invocation_id: uuid.UUID, error_text: str) -> None:
        self.update_status(
            world_id,
            invocation_id,
            InvocationStatusUpdate(status=InvocationStatus.FAILED, error_text=error_text),
        )

    def redact(
        self,
        world_id: uuid.UUID,
        invocation_id: uuid.UUID,
        request: InvocationRedactRequest,
    ) -> InvocationRecordView:
        model = self._required(world_id, invocation_id)
        status = (
            request.redaction_status
            if request.redaction_status != InvocationRedactionStatus.RAW
            else redaction_status_for_mode(request.mode)
        )
        if request.mode in {RedactionMode.CLEAR_RAW_PAYLOADS, RedactionMode.CHECKSUM_ONLY}:
            model.input_text = None
            model.output_text = None
            if request.mode == RedactionMode.CHECKSUM_ONLY:
                model.input_json = None
                model.output_json = None
                model.request_params_json = None
                model.response_metadata_json = None
        if request.mode == RedactionMode.HIDE:
            model.visibility = InvocationVisibility.HIDDEN.value
        model.redaction_status = status.value
        if request.mode != RedactionMode.HIDE:
            model.status = InvocationStatus.REDACTED.value
        PromptSnapshotService(self._session).redact_snapshot_for_invocation(
            invocation_id,
            request,
        )
        self._session.flush()
        self._session.refresh(model)
        return _invocation_record(model)

    def attach_tag(
        self,
        create: InvocationTagCreate,
    ) -> InvocationTagRecord:
        worldline_id = _worldline_id(self._session, create.world_id, create.worldline_id)
        invocation = self._required(create.world_id, create.invocation_id)
        if invocation.worldline_id != worldline_id:
            raise InvocationValidationError("tag invocation must belong to the tag worldline")
        model = ModelInvocationTag(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=worldline_id,
            invocation_id=create.invocation_id,
            tag_type=create.tag_type,
            tag_key=create.tag_key,
            tag_value=create.tag_value,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise InvocationValidationError("model invocation tag already exists") from exc
        self._session.refresh(model)
        return _tag_record(model)

    def list_tags(
        self,
        world_id: uuid.UUID,
        invocation_id: uuid.UUID,
    ) -> builtins.list[InvocationTagRecord]:
        invocation = self._required(world_id, invocation_id)
        statement = (
            select(ModelInvocationTag)
            .where(
                ModelInvocationTag.world_id == world_id,
                ModelInvocationTag.worldline_id == invocation.worldline_id,
                ModelInvocationTag.invocation_id == invocation_id,
            )
            .order_by(
                ModelInvocationTag.tag_type,
                ModelInvocationTag.tag_key,
                ModelInvocationTag.tag_value,
            )
        )
        return [_tag_record(model) for model in self._session.scalars(statement).all()]

    def delete_tag(self, world_id: uuid.UUID, invocation_id: uuid.UUID, tag_id: uuid.UUID) -> None:
        model = self._session.get(ModelInvocationTag, tag_id)
        if model is None or model.world_id != world_id or model.invocation_id != invocation_id:
            raise InvocationNotFoundError("model invocation tag not found")
        self._session.delete(model)
        self._session.flush()

    def link_runtime_run(
        self,
        create: AgentRuntimeRunInvocationLinkCreate,
    ) -> AgentRuntimeRunInvocationLinkRecord:
        run = self._session.get(AgentRuntimeRun, create.agent_runtime_run_id)
        invocation = self._session.get(ModelInvocation, create.model_invocation_id)
        if run is None or invocation is None:
            raise InvocationValidationError("runtime run and invocation are required")
        if (
            run.world_id != create.world_id
            or invocation.world_id != create.world_id
            or run.worldline_id != create.worldline_id
            or invocation.worldline_id != create.worldline_id
        ):
            raise InvocationValidationError("runtime run and invocation must share worldline")
        model = AgentRuntimeRunModelInvocation(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=create.worldline_id,
            agent_runtime_run_id=create.agent_runtime_run_id,
            model_invocation_id=create.model_invocation_id,
            invocation_role=create.invocation_role.value,
            sequence_index=create.sequence_index,
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _link_record(model)

    def _required(self, world_id: uuid.UUID, invocation_id: uuid.UUID) -> ModelInvocation:
        model = self._session.get(ModelInvocation, invocation_id)
        if model is None or model.world_id != world_id:
            raise InvocationNotFoundError("model invocation not found")
        return model

    def _visible_invocation_or_none(
        self,
        world_id: uuid.UUID,
        invocation_id: uuid.UUID,
        *,
        include_hidden: bool,
        platform_admin: bool,
    ) -> ModelInvocation | None:
        model = self._session.get(ModelInvocation, invocation_id)
        if model is None or model.world_id != world_id:
            return None
        allowed = PLATFORM_VISIBLE if platform_admin else ADMIN_VISIBLE
        if model.visibility not in allowed:
            return None
        if model.visibility == InvocationVisibility.HIDDEN.value and not (
            platform_admin and include_hidden
        ):
            return None
        return model

    def _validate_refs(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        create: InvocationRecordCreate,
    ) -> None:
        if create.parent_invocation_id is not None:
            parent = self._session.get(ModelInvocation, create.parent_invocation_id)
            if parent is None or parent.world_id != world_id or parent.worldline_id != worldline_id:
                raise InvocationValidationError("parent invocation must share worldline")
        if create.agent_id is not None:
            agent = self._session.get(Agent, create.agent_id)
            if agent is None or agent.world_id != world_id:
                raise InvocationValidationError("agent must belong to invocation world")
        if create.conversation_id is not None:
            conversation = self._session.get(ConversationSession, create.conversation_id)
            if (
                conversation is None
                or conversation.world_id != world_id
                or not _matches_worldline(
                    self._session,
                    world_id,
                    conversation.worldline_id,
                    worldline_id,
                )
            ):
                raise InvocationValidationError("conversation must belong to invocation worldline")
        if create.turn_id is not None:
            turn = self._session.get(ConversationTurn, create.turn_id)
            if turn is None:
                raise InvocationValidationError("turn must belong to invocation worldline")
            conversation = self._session.get(ConversationSession, turn.session_id)
            if (
                conversation is None
                or conversation.world_id != world_id
                or not _matches_worldline(
                    self._session,
                    world_id,
                    conversation.worldline_id,
                    worldline_id,
                )
            ):
                raise InvocationValidationError("turn must belong to invocation worldline")
            if create.conversation_id is not None and create.conversation_id != conversation.id:
                raise InvocationValidationError("turn must belong to referenced conversation")
        if create.world_event_id is not None:
            event = self._session.get(WorldEventModel, create.world_event_id)
            if event is None or event.world_id != world_id or event.worldline_id != worldline_id:
                raise InvocationValidationError("event must belong to invocation worldline")
        if create.media_job_id is not None:
            job = self._session.get(MediaJob, create.media_job_id)
            if job is None or job.world_id != world_id or job.worldline_id != worldline_id:
                raise InvocationValidationError("media job must belong to invocation worldline")
        if create.media_asset_id is not None:
            asset = self._session.get(MediaAsset, create.media_asset_id)
            if asset is None or asset.world_id != world_id or asset.worldline_id != worldline_id:
                raise InvocationValidationError("media asset must belong to invocation worldline")
        if create.memory_write_job_id is not None:
            memory_job = self._session.get(MemoryWriteJob, create.memory_write_job_id)
            if (
                memory_job is None
                or memory_job.world_id != world_id
                or not _matches_worldline(
                    self._session,
                    world_id,
                    memory_job.worldline_id,
                    worldline_id,
                )
            ):
                raise InvocationValidationError("memory job must belong to invocation worldline")
        if create.provider_profile_id is not None:
            if self._session.get(ProviderProfile, create.provider_profile_id) is None:
                raise InvocationValidationError("provider profile not found")

    def _apply_filters(
        self,
        statement: Select[tuple[ModelInvocation]],
        filters: InvocationSearchFilters,
    ) -> Select[tuple[ModelInvocation]]:
        if filters.created_after is not None:
            statement = statement.where(ModelInvocation.created_at >= filters.created_after)
        if filters.created_before is not None:
            statement = statement.where(ModelInvocation.created_at <= filters.created_before)
        if filters.cursor is not None:
            if filters.order == SortOrder.DESC:
                statement = statement.where(ModelInvocation.created_at < filters.cursor)
            else:
                statement = statement.where(ModelInvocation.created_at > filters.cursor)
        for attr_name in (
            "trace_id",
            "parent_invocation_id",
            "agent_id",
            "conversation_id",
            "turn_id",
            "world_event_id",
            "media_job_id",
            "media_asset_id",
            "memory_write_job_id",
        ):
            value = getattr(filters, attr_name)
            if value is not None:
                statement = statement.where(getattr(ModelInvocation, attr_name) == value)
        if filters.invocation_kind is not None:
            statement = statement.where(
                ModelInvocation.invocation_kind == filters.invocation_kind.value
            )
        if filters.provider_kind is not None:
            statement = statement.where(
                ModelInvocation.provider_kind == filters.provider_kind.value
            )
        if filters.model_name is not None:
            statement = statement.where(ModelInvocation.model_name == filters.model_name)
        if filters.status is not None:
            statement = statement.where(ModelInvocation.status == filters.status.value)
        if filters.visibility is not None:
            statement = statement.where(ModelInvocation.visibility == filters.visibility.value)
        if filters.redaction_status is not None:
            statement = statement.where(
                ModelInvocation.redaction_status == filters.redaction_status.value
            )
        if filters.retention_policy is not None:
            statement = statement.where(
                ModelInvocation.retention_policy == filters.retention_policy.value
            )
        if filters.contains_sensitive_context is not None:
            statement = statement.where(
                ModelInvocation.contains_sensitive_context.is_(
                    filters.contains_sensitive_context
                )
            )
        if filters.contains_text is not None:
            pattern = f"%{filters.contains_text}%"
            predicates = [
                and_(
                    ModelInvocation.redaction_status == InvocationRedactionStatus.RAW.value,
                    or_(
                        ModelInvocation.input_text.ilike(pattern),
                        ModelInvocation.output_text.ilike(pattern),
                        ModelInvocation.error_text.ilike(pattern),
                    ),
                ),
                and_(
                    ModelInvocation.redaction_status == InvocationRedactionStatus.RAW.value,
                    select(PromptSnapshot.id)
                    .where(
                        PromptSnapshot.invocation_id == ModelInvocation.id,
                        PromptSnapshot.redaction_status == InvocationRedactionStatus.RAW.value,
                        or_(
                            PromptSnapshot.raw_prompt_text.ilike(pattern),
                            PromptSnapshot.raw_output_text.ilike(pattern),
                        ),
                    )
                    .exists(),
                ),
            ]
            statement = statement.where(or_(*predicates))
        return statement

    def _apply_tag_filters(
        self,
        statement: Select[tuple[ModelInvocation]],
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        filters: InvocationSearchFilters,
    ) -> Select[tuple[ModelInvocation]]:
        for tag_filter in filters.tags:
            tag_exists = (
                select(ModelInvocationTag.id)
                .where(
                    ModelInvocationTag.world_id == world_id,
                    ModelInvocationTag.worldline_id == worldline_id,
                    ModelInvocationTag.invocation_id == ModelInvocation.id,
                    ModelInvocationTag.tag_type == tag_filter.tag_type,
                    ModelInvocationTag.tag_key == tag_filter.tag_key,
                    ModelInvocationTag.tag_value == tag_filter.tag_value,
                )
                .limit(1)
            )
            statement = statement.where(tag_exists.exists())
        return statement


class PromptSnapshotService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_template(self, create: PromptTemplateCreate) -> PromptTemplateRecord:
        scope_key = _scope_key(create.scope_kind, create.world_id)
        if create.scope_kind == PromptTemplateScopeKind.WORLD:
            if self._session.get(World, create.world_id) is None:
                raise InvocationValidationError("template world not found")
        model = PromptTemplate(
            id=uuid.uuid4(),
            scope_kind=create.scope_kind.value,
            world_id=create.world_id,
            scope_key=scope_key,
            template_key=create.template_key,
            version=create.version,
            invocation_kind=create.invocation_kind.value,
            title=create.title,
            content=create.content,
            input_schema_json=create.input_schema_json,
            output_schema_json=create.output_schema_json,
            metadata_json=create.metadata_json,
            status=create.status.value,
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _template_record(model)

    def list_templates(
        self,
        world_id: uuid.UUID,
        *,
        scope_kind: PromptTemplateScopeKind | None = None,
        template_key: str | None = None,
        status: PromptTemplateStatus | None = None,
        include_global: bool = True,
    ) -> list[PromptTemplateRecord]:
        statement = select(PromptTemplate)
        if scope_kind is not None:
            statement = statement.where(PromptTemplate.scope_kind == scope_kind.value)
        else:
            clauses = [PromptTemplate.world_id == world_id]
            if include_global:
                clauses.append(PromptTemplate.scope_kind == PromptTemplateScopeKind.GLOBAL.value)
            statement = statement.where(or_(*clauses))
        if template_key is not None:
            statement = statement.where(PromptTemplate.template_key == template_key)
        if status is not None:
            statement = statement.where(PromptTemplate.status == status.value)
        return [
            _template_record(model)
            for model in self._session.scalars(
                statement.order_by(PromptTemplate.template_key, PromptTemplate.version.desc())
            ).all()
        ]

    def get_template(
        self,
        world_id: uuid.UUID,
        template_id: uuid.UUID,
        *,
        platform_admin: bool = False,
    ) -> PromptTemplateRecord | None:
        model = self._session.get(PromptTemplate, template_id)
        if model is None:
            return None
        if model.world_id is not None and model.world_id != world_id:
            return None
        return _template_record(model)

    def update_template(
        self,
        world_id: uuid.UUID,
        template_id: uuid.UUID,
        update: PromptTemplateUpdate,
        *,
        platform_admin: bool = False,
    ) -> PromptTemplateRecord:
        model = self._session.get(PromptTemplate, template_id)
        if model is None:
            raise InvocationNotFoundError("prompt template not found")
        if model.scope_kind == PromptTemplateScopeKind.GLOBAL.value and not platform_admin:
            raise InvocationNotFoundError("prompt template not found")
        if model.world_id is not None and model.world_id != world_id:
            raise InvocationNotFoundError("prompt template not found")
        if update.title is not None:
            model.title = update.title
        if update.content is not None:
            model.content = update.content
        if "input_schema_json" in update.model_fields_set:
            model.input_schema_json = update.input_schema_json
        if "output_schema_json" in update.model_fields_set:
            model.output_schema_json = update.output_schema_json
        if "metadata_json" in update.model_fields_set:
            model.metadata_json = update.metadata_json
        if update.status is not None:
            model.status = update.status.value
        self._session.flush()
        self._session.refresh(model)
        return _template_record(model)

    def resolve_template(self, world_id: uuid.UUID, template_key: str) -> PromptTemplateRecord:
        world_template = self._session.scalars(
            select(PromptTemplate)
            .where(
                PromptTemplate.world_id == world_id,
                PromptTemplate.template_key == template_key,
                PromptTemplate.status == PromptTemplateStatus.ACTIVE.value,
            )
            .order_by(PromptTemplate.version.desc())
            .limit(1)
        ).first()
        if world_template is not None:
            return _template_record(world_template)
        global_template = self._session.scalars(
            select(PromptTemplate)
            .where(
                PromptTemplate.scope_kind == PromptTemplateScopeKind.GLOBAL.value,
                PromptTemplate.template_key == template_key,
                PromptTemplate.status == PromptTemplateStatus.ACTIVE.value,
            )
            .order_by(PromptTemplate.version.desc())
            .limit(1)
        ).first()
        if global_template is None:
            raise InvocationNotFoundError("prompt template not found")
        return _template_record(global_template)

    def create_snapshot(
        self,
        invocation_id: uuid.UUID,
        create: PromptSnapshotCreate,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> PromptSnapshotRecord:
        invocation = self._session.get(ModelInvocation, invocation_id)
        if (
            invocation is None
            or invocation.world_id != world_id
            or invocation.worldline_id != worldline_id
        ):
            raise InvocationValidationError("snapshot invocation must belong to worldline")
        if create.template_id is not None:
            template = self._session.get(PromptTemplate, create.template_id)
            if template is None:
                raise InvocationValidationError("prompt template not found")
            if template.world_id is not None and template.world_id != world_id:
                raise InvocationValidationError("prompt template world must match invocation world")
        model = PromptSnapshot(
            id=uuid.uuid4(),
            invocation_id=invocation_id,
            template_id=create.template_id,
            template_key=create.template_key,
            template_version=create.template_version,
            raw_prompt_text=create.raw_prompt_text,
            raw_messages_json=create.raw_messages_json,
            raw_request_json=create.raw_request_json,
            raw_response_json=create.raw_response_json,
            raw_output_text=create.raw_output_text,
            normalized_output_json=create.normalized_output_json,
            prompt_context_snapshot_json=create.prompt_context_snapshot_json,
            tool_definitions_json=create.tool_definitions_json,
            context_pack_refs_json=create.context_pack_refs_json,
            input_asset_refs_json=create.input_asset_refs_json,
            prompt_checksum_sha256=prompt_checksum(
                raw_prompt_text=create.raw_prompt_text,
                raw_messages_json=create.raw_messages_json,
                raw_request_json=create.raw_request_json,
            ),
            request_checksum_sha256=checksum_json(create.raw_request_json),
            response_checksum_sha256=checksum_json(create.raw_response_json),
            output_checksum_sha256=checksum_text(create.raw_output_text),
            visibility=create.visibility.value,
            redaction_status=create.redaction_status.value,
            contains_sensitive_context=create.contains_sensitive_context,
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _snapshot_record(model)

    def get_snapshot(
        self,
        world_id: uuid.UUID,
        invocation_id: uuid.UUID,
        *,
        platform_admin: bool = False,
    ) -> PromptSnapshotRecord | None:
        invocation = self._session.get(ModelInvocation, invocation_id)
        if invocation is None or invocation.world_id != world_id:
            return None
        if not _raw_allowed(invocation, platform_admin):
            return None
        model = self._session.scalars(
            select(PromptSnapshot).where(PromptSnapshot.invocation_id == invocation_id)
        ).one_or_none()
        return None if model is None else _snapshot_record(model)

    def update_snapshot_for_invocation(
        self,
        invocation_id: uuid.UUID,
        update: PromptSnapshotUpdate,
    ) -> PromptSnapshotRecord | None:
        model = self._session.scalars(
            select(PromptSnapshot).where(PromptSnapshot.invocation_id == invocation_id)
        ).one_or_none()
        if model is None:
            return None
        if "raw_response_json" in update.model_fields_set:
            model.raw_response_json = update.raw_response_json
            model.response_checksum_sha256 = checksum_json(update.raw_response_json)
        if "raw_output_text" in update.model_fields_set:
            model.raw_output_text = update.raw_output_text
            model.output_checksum_sha256 = checksum_text(update.raw_output_text)
        if "normalized_output_json" in update.model_fields_set:
            model.normalized_output_json = update.normalized_output_json
        self._session.flush()
        self._session.refresh(model)
        return _snapshot_record(model)

    def redact_snapshot_for_invocation(
        self,
        invocation_id: uuid.UUID,
        request: InvocationRedactRequest,
    ) -> None:
        model = self._session.scalars(
            select(PromptSnapshot).where(PromptSnapshot.invocation_id == invocation_id)
        ).one_or_none()
        if model is None:
            return
        if request.mode in {RedactionMode.CLEAR_RAW_PAYLOADS, RedactionMode.CHECKSUM_ONLY}:
            model.raw_prompt_text = None
            model.raw_messages_json = None
            model.raw_request_json = None
            model.raw_response_json = None
            model.raw_output_text = None
            if request.mode == RedactionMode.CHECKSUM_ONLY:
                model.normalized_output_json = None
                model.prompt_context_snapshot_json = None
                model.tool_definitions_json = None
                model.context_pack_refs_json = None
                model.input_asset_refs_json = None
        if request.mode == RedactionMode.HIDE:
            model.visibility = InvocationVisibility.HIDDEN.value
        model.redaction_status = redaction_status_for_mode(request.mode).value


def _apply_visibility(
    statement: Select[tuple[ModelInvocation]],
    include_hidden: bool,
    platform_admin: bool,
) -> Select[tuple[ModelInvocation]]:
    allowed = PLATFORM_VISIBLE if platform_admin else ADMIN_VISIBLE
    statement = statement.where(ModelInvocation.visibility.in_(allowed))
    if not (platform_admin and include_hidden):
        statement = statement.where(ModelInvocation.visibility != InvocationVisibility.HIDDEN.value)
    return statement


def _worldline_id(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID | None,
) -> uuid.UUID:
    try:
        return worldline_or_404(session, world_id, worldline_id).id
    except ValueError as exc:
        raise InvocationValidationError("worldline not found") from exc


def _matches_worldline(
    session: Session,
    world_id: uuid.UUID,
    candidate_worldline_id: uuid.UUID | None,
    target_worldline_id: uuid.UUID,
) -> bool:
    if candidate_worldline_id is not None:
        return candidate_worldline_id == target_worldline_id
    primary = primary_worldline_or_none(session, world_id)
    return primary is not None and primary.id == target_worldline_id


def _scope_key(scope_kind: PromptTemplateScopeKind, world_id: uuid.UUID | None) -> str:
    if scope_kind == PromptTemplateScopeKind.GLOBAL:
        return "global"
    if world_id is None:
        raise InvocationValidationError("world prompt templates require world_id")
    return f"world:{world_id}"


def _raw_allowed(model: ModelInvocation, platform_admin: bool) -> bool:
    if model.redaction_status != InvocationRedactionStatus.RAW.value:
        return False
    if model.visibility == InvocationVisibility.DEVELOPER_ONLY.value:
        return platform_admin
    if model.visibility == InvocationVisibility.HIDDEN.value:
        return platform_admin
    return model.visibility in ADMIN_VISIBLE


def _invocation_record(model: ModelInvocation, *, raw_allowed: bool = True) -> InvocationRecordView:
    return InvocationRecordView(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        trace_id=model.trace_id,
        parent_invocation_id=model.parent_invocation_id,
        invocation_kind=InvocationKind(model.invocation_kind),
        actor_kind=InvocationActorKind(model.actor_kind),
        actor_ref=model.actor_ref,
        agent_id=model.agent_id,
        conversation_id=model.conversation_id,
        turn_id=model.turn_id,
        world_event_id=model.world_event_id,
        media_job_id=model.media_job_id,
        media_asset_id=model.media_asset_id,
        memory_write_job_id=model.memory_write_job_id,
        provider_kind=InvocationProviderKind(model.provider_kind),
        provider_profile_id=model.provider_profile_id,
        model_name=model.model_name,
        model_version=model.model_version,
        prompt_template_key=model.prompt_template_key,
        prompt_template_version=model.prompt_template_version,
        input_text=model.input_text if raw_allowed else None,
        output_text=model.output_text if raw_allowed else None,
        input_json=model.input_json if raw_allowed else None,
        output_json=model.output_json if raw_allowed else None,
        request_params_json=model.request_params_json if raw_allowed else None,
        response_metadata_json=model.response_metadata_json if raw_allowed else None,
        usage_json=model.usage_json,
        latency_ms=model.latency_ms,
        estimated_cost=model.estimated_cost,
        status=InvocationStatus(model.status),
        error_text=model.error_text if raw_allowed else None,
        visibility=InvocationVisibility(model.visibility),
        redaction_status=InvocationRedactionStatus(model.redaction_status),
        retention_policy=InvocationRetentionPolicy(model.retention_policy),
        contains_sensitive_context=model.contains_sensitive_context,
        purge_after=model.purge_after,
        created_at=_utc(model.created_at),
        updated_at=_utc(model.updated_at),
    )


def _tag_record(model: ModelInvocationTag) -> InvocationTagRecord:
    return InvocationTagRecord(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        invocation_id=model.invocation_id,
        tag_type=model.tag_type,
        tag_key=model.tag_key,
        tag_value=model.tag_value,
        created_at=_utc(model.created_at),
    )


def _template_record(model: PromptTemplate) -> PromptTemplateRecord:
    return PromptTemplateRecord(
        id=model.id,
        scope_kind=PromptTemplateScopeKind(model.scope_kind),
        world_id=model.world_id,
        scope_key=model.scope_key,
        template_key=model.template_key,
        version=model.version,
        invocation_kind=InvocationKind(model.invocation_kind),
        title=model.title,
        content=model.content,
        input_schema_json=model.input_schema_json,
        output_schema_json=model.output_schema_json,
        metadata_json=model.metadata_json,
        status=PromptTemplateStatus(model.status),
        created_at=_utc(model.created_at),
        updated_at=_utc(model.updated_at),
    )


def _snapshot_record(model: PromptSnapshot) -> PromptSnapshotRecord:
    return PromptSnapshotRecord(
        id=model.id,
        invocation_id=model.invocation_id,
        template_id=model.template_id,
        template_key=model.template_key,
        template_version=model.template_version,
        raw_prompt_text=model.raw_prompt_text,
        raw_messages_json=model.raw_messages_json,
        raw_request_json=model.raw_request_json,
        raw_response_json=model.raw_response_json,
        raw_output_text=model.raw_output_text,
        normalized_output_json=model.normalized_output_json,
        prompt_context_snapshot_json=model.prompt_context_snapshot_json,
        tool_definitions_json=model.tool_definitions_json,
        context_pack_refs_json=model.context_pack_refs_json,
        input_asset_refs_json=model.input_asset_refs_json,
        prompt_checksum_sha256=model.prompt_checksum_sha256,
        request_checksum_sha256=model.request_checksum_sha256,
        response_checksum_sha256=model.response_checksum_sha256,
        output_checksum_sha256=model.output_checksum_sha256,
        visibility=InvocationVisibility(model.visibility),
        redaction_status=InvocationRedactionStatus(model.redaction_status),
        contains_sensitive_context=model.contains_sensitive_context,
        created_at=_utc(model.created_at),
        updated_at=_utc(model.updated_at),
    )


def _link_record(model: AgentRuntimeRunModelInvocation) -> AgentRuntimeRunInvocationLinkRecord:
    return AgentRuntimeRunInvocationLinkRecord(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        agent_runtime_run_id=model.agent_runtime_run_id,
        model_invocation_id=model.model_invocation_id,
        invocation_role=InvocationRole(model.invocation_role),
        sequence_index=model.sequence_index,
        created_at=_utc(model.created_at),
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
