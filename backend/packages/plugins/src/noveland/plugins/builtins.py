from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from functools import lru_cache
from typing import Any, Protocol

import httpx
from noveland.adapters.model_provider import (
    AnthropicCompatibleProvider,
    ModelProvider,
    OpenAICompatibleProvider,
    ProviderProfileRecord,
)
from noveland.agents.contracts import AgentObservationRecord, AgentPersonaRecord
from noveland.agents.models import Agent
from noveland.calendar.contracts import ScheduleRuleKind, ScheduleRuleRecord
from noveland.conversations.contracts import (
    ConversationParticipantRecord,
    ConversationSessionRecord,
    ConversationSpeakerKind,
    ConversationTurnRecord,
)
from noveland.core.settings import AppSettings
from noveland.memory.backends.mem0_oss import Mem0OssMemoryBackend
from noveland.memory.contracts import (
    MemoryBackend,
    MemoryBackendProfileRecord,
)
from noveland.memory.local_pgvector import LocalPgvectorMemoryBackend
from noveland.plugins.categories import PluginCategory
from noveland.plugins.constants import (
    BUILTIN_ANTHROPIC_COMPATIBLE,
    BUILTIN_DEFAULT_NARRATIVE_WRITER,
    BUILTIN_DEFAULT_PERSONA_POLICY,
    BUILTIN_DEFAULT_WORLD_RULES,
    BUILTIN_LOCAL_PGVECTOR_MEMORY,
    BUILTIN_MEM0_OSS_MEMORY,
    BUILTIN_OPENAI_COMPATIBLE,
)
from noveland.plugins.definition import PluginDefinition
from noveland.plugins.manifest import PluginManifest
from noveland.plugins.registry import PluginRegistry
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session


class ModelProviderPlugin(Protocol):
    def create_provider(
        self,
        profile: ProviderProfileRecord,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
    ) -> ModelProvider: ...


class MemoryBackendPlugin(Protocol):
    def create_backend(
        self,
        *,
        profile: MemoryBackendProfileRecord,
        settings: AppSettings,
        session: Session,
    ) -> MemoryBackend: ...


class WorldRulesPlugin(Protocol):
    def due_rules(
        self,
        rules: Sequence[ScheduleRuleRecord],
        world_time: datetime,
    ) -> list[ScheduleRuleRecord]: ...


class PersonaPolicyPlugin(Protocol):
    def build_prompt(
        self,
        *,
        agent: Agent,
        task_prompt: str,
        persona: AgentPersonaRecord | None,
        observations: Sequence[AgentObservationRecord],
        memory_context: str | None = None,
    ) -> str: ...


class NarrativeWriterPlugin(Protocol):
    def build_summary_prompt(
        self,
        *,
        session: ConversationSessionRecord,
        participants: Sequence[ConversationParticipantRecord],
        turns: Sequence[ConversationTurnRecord],
        agents_by_id: dict[Any, Agent],
    ) -> str: ...

    def build_chapter_prompt(
        self,
        *,
        session: ConversationSessionRecord,
        participants: Sequence[ConversationParticipantRecord],
        turns: Sequence[ConversationTurnRecord],
        agents_by_id: dict[Any, Agent],
        summary_text: str,
    ) -> str: ...


class _FrozenConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class HeaderPluginConfig(_FrozenConfig):
    headers: dict[str, str] = Field(default_factory=dict)


class EmptyPluginConfig(_FrozenConfig):
    pass


class OpenAICompatibleProviderPlugin:
    def __init__(self, config: HeaderPluginConfig) -> None:
        self._config = config

    def create_provider(
        self,
        profile: ProviderProfileRecord,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
    ) -> ModelProvider:
        return OpenAICompatibleProvider(
            _profile_with_plugin_headers(profile, self._config.headers),
            api_key,
            transport,
        )


class AnthropicCompatibleProviderPlugin:
    def __init__(self, config: HeaderPluginConfig) -> None:
        self._config = config

    def create_provider(
        self,
        profile: ProviderProfileRecord,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
    ) -> ModelProvider:
        return AnthropicCompatibleProvider(
            _profile_with_plugin_headers(profile, self._config.headers),
            api_key,
            transport,
        )


class LocalPgvectorMemoryPlugin:
    def __init__(self, config: EmptyPluginConfig) -> None:
        del config

    def create_backend(
        self,
        *,
        profile: MemoryBackendProfileRecord,
        settings: AppSettings,
        session: Session,
    ) -> MemoryBackend:
        del profile, settings
        return LocalPgvectorMemoryBackend(session)


class Mem0OssMemoryPlugin:
    def __init__(self, config: EmptyPluginConfig) -> None:
        del config

    def create_backend(
        self,
        *,
        profile: MemoryBackendProfileRecord,
        settings: AppSettings,
        session: Session,
    ) -> MemoryBackend:
        del session
        return Mem0OssMemoryBackend(profile, settings)


class DefaultWorldRulesPlugin:
    def __init__(self, config: EmptyPluginConfig) -> None:
        del config

    def due_rules(
        self,
        rules: Sequence[ScheduleRuleRecord],
        world_time: datetime,
    ) -> list[ScheduleRuleRecord]:
        return [rule for rule in rules if _schedule_rule_matches(rule, world_time)]


class DefaultPersonaPolicyPlugin:
    def __init__(self, config: EmptyPluginConfig) -> None:
        del config

    def build_prompt(
        self,
        *,
        agent: Agent,
        task_prompt: str,
        persona: AgentPersonaRecord | None,
        observations: Sequence[AgentObservationRecord],
        memory_context: str | None = None,
    ) -> str:
        lines = [
            task_prompt,
            "",
            f"Agent: {agent.display_name} ({agent.agent_key}).",
        ]
        if persona is not None and persona.is_enabled:
            lines.extend(
                [
                    "Persona:",
                    persona.persona_text or "No persona text configured.",
                    f"Behavior policy: {persona.behavior_policy}",
                ],
            )
        else:
            lines.append("Persona: disabled or not configured.")
        if observations:
            lines.append("Recent filtered observations:")
            lines.extend(f"- {observation.content}" for observation in observations[:8])
        else:
            lines.append("Recent filtered observations: none.")
        if memory_context:
            lines.extend(["Relevant long-term memory:", memory_context])
        else:
            lines.append("Relevant long-term memory: none.")
        lines.append(
            "Use only the persona, policy, task, filtered observations, and memory above.",
        )
        return "\n".join(lines)


class DefaultNarrativeWriterPlugin:
    def __init__(self, config: EmptyPluginConfig) -> None:
        del config

    def build_summary_prompt(
        self,
        *,
        session: ConversationSessionRecord,
        participants: Sequence[ConversationParticipantRecord],
        turns: Sequence[ConversationTurnRecord],
        agents_by_id: dict[Any, Agent],
    ) -> str:
        return "\n".join(
            [
                "Write a concise but complete conversation summary.",
                _conversation_context(session, participants, turns, agents_by_id),
                "Output plain text only.",
            ],
        )

    def build_chapter_prompt(
        self,
        *,
        session: ConversationSessionRecord,
        participants: Sequence[ConversationParticipantRecord],
        turns: Sequence[ConversationTurnRecord],
        agents_by_id: dict[Any, Agent],
        summary_text: str,
    ) -> str:
        return "\n".join(
            [
                "Write a chapter draft based on this Noveland conversation.",
                _conversation_context(session, participants, turns, agents_by_id),
                "Conversation summary:",
                summary_text,
                "Output plain text only.",
            ],
        )


@lru_cache(maxsize=1)
def get_builtin_plugin_registry() -> PluginRegistry:
    return PluginRegistry(
        [
            PluginDefinition.from_config_model(
                manifest=PluginManifest(
                    identifier=BUILTIN_OPENAI_COMPATIBLE,
                    category=PluginCategory.MODEL_PROVIDER,
                    version="0.1.0",
                    config_schema=HeaderPluginConfig.model_json_schema(),
                    capabilities=("chat.completions", "custom.headers"),
                ),
                config_model=HeaderPluginConfig,
                implementation_factory=OpenAICompatibleProviderPlugin,
            ),
            PluginDefinition.from_config_model(
                manifest=PluginManifest(
                    identifier=BUILTIN_ANTHROPIC_COMPATIBLE,
                    category=PluginCategory.MODEL_PROVIDER,
                    version="0.1.0",
                    config_schema=HeaderPluginConfig.model_json_schema(),
                    capabilities=("messages", "custom.headers"),
                ),
                config_model=HeaderPluginConfig,
                implementation_factory=AnthropicCompatibleProviderPlugin,
            ),
            PluginDefinition.from_config_model(
                manifest=PluginManifest(
                    identifier=BUILTIN_MEM0_OSS_MEMORY,
                    category=PluginCategory.MEMORY_BACKEND,
                    version="0.1.0",
                    config_schema=EmptyPluginConfig.model_json_schema(),
                    capabilities=(
                        "memory.record_turn",
                        "memory.record_events",
                        "memory.list",
                        "memory.search",
                        "memory.delete_scope",
                        "memory.healthcheck",
                    ),
                ),
                config_model=EmptyPluginConfig,
                implementation_factory=Mem0OssMemoryPlugin,
            ),
            PluginDefinition.from_config_model(
                manifest=PluginManifest(
                    identifier=BUILTIN_LOCAL_PGVECTOR_MEMORY,
                    category=PluginCategory.MEMORY_BACKEND,
                    version="0.1.0",
                    config_schema=EmptyPluginConfig.model_json_schema(),
                    capabilities=(
                        "memory.record_turn",
                        "memory.record_events",
                        "memory.list",
                        "memory.search",
                        "memory.delete_scope",
                        "memory.healthcheck",
                    ),
                ),
                config_model=EmptyPluginConfig,
                implementation_factory=LocalPgvectorMemoryPlugin,
            ),
            PluginDefinition.from_config_model(
                manifest=PluginManifest(
                    identifier=BUILTIN_DEFAULT_WORLD_RULES,
                    category=PluginCategory.WORLD_RULES,
                    version="0.1.0",
                    config_schema=EmptyPluginConfig.model_json_schema(),
                    capabilities=("schedule.resolve_due_rules",),
                ),
                config_model=EmptyPluginConfig,
                implementation_factory=DefaultWorldRulesPlugin,
            ),
            PluginDefinition.from_config_model(
                manifest=PluginManifest(
                    identifier=BUILTIN_DEFAULT_PERSONA_POLICY,
                    category=PluginCategory.PERSONA_POLICY,
                    version="0.1.0",
                    config_schema=EmptyPluginConfig.model_json_schema(),
                    capabilities=("agent.prompt_context",),
                ),
                config_model=EmptyPluginConfig,
                implementation_factory=DefaultPersonaPolicyPlugin,
            ),
            PluginDefinition.from_config_model(
                manifest=PluginManifest(
                    identifier=BUILTIN_DEFAULT_NARRATIVE_WRITER,
                    category=PluginCategory.NARRATIVE_WRITER,
                    version="0.1.0",
                    config_schema=EmptyPluginConfig.model_json_schema(),
                    capabilities=("conversation.summary", "conversation.chapter"),
                ),
                config_model=EmptyPluginConfig,
                implementation_factory=DefaultNarrativeWriterPlugin,
            ),
        ],
    )


def _profile_with_plugin_headers(
    profile: ProviderProfileRecord,
    plugin_headers: dict[str, str],
) -> ProviderProfileRecord:
    if not plugin_headers:
        return profile
    headers = profile.capabilities.get("headers", {})
    merged_headers = {}
    if isinstance(headers, dict):
        merged_headers.update(
            {
                str(key): str(value)
                for key, value in headers.items()
                if isinstance(key, str) and isinstance(value, str)
            },
        )
    merged_headers.update(plugin_headers)
    return profile.model_copy(
        update={
            "capabilities": {
                **profile.capabilities,
                "headers": merged_headers,
            },
        },
    )


def _schedule_rule_matches(rule: ScheduleRuleRecord, world_time: datetime) -> bool:
    if rule.kind is ScheduleRuleKind.WEEKDAY:
        return world_time.weekday() < 5
    if rule.kind is ScheduleRuleKind.WEEKEND:
        return world_time.weekday() >= 5
    hours = rule.config.get("hours")
    if isinstance(hours, Sequence) and not isinstance(hours, str | bytes):
        return world_time.hour in {int(hour) for hour in hours}
    return False


def _conversation_context(
    session: ConversationSessionRecord,
    participants: Sequence[ConversationParticipantRecord],
    turns: Sequence[ConversationTurnRecord],
    agents_by_id: dict[Any, Agent],
) -> str:
    participant_lines = _participant_lines(participants, agents_by_id)
    transcript_lines = _transcript_lines(turns, agents_by_id)
    terminal_reason = "None" if session.terminal_reason is None else session.terminal_reason.value
    return "\n".join(
        [
            f"Session title: {session.title}",
            f"Objective: {session.objective or 'No explicit objective.'}",
            (
                f"Scope metadata: scope_type={session.scope_type.value}; "
                f"scene_id={session.scene_id}"
            ),
            f"Terminal status: {session.status.value}",
            f"Terminal reason: {terminal_reason}",
            "Participants:",
            *(participant_lines or ["- none"]),
            "Transcript:",
            *(transcript_lines or ["- no turns recorded"]),
        ],
    )


def _participant_lines(
    participants: Sequence[ConversationParticipantRecord],
    agents_by_id: dict[Any, Agent],
) -> list[str]:
    lines: list[str] = []
    for participant in participants:
        agent = agents_by_id.get(participant.agent_id)
        if agent is None:
            continue
        lines.append(f"- {agent.display_name} ({agent.agent_key}) order={participant.turn_order}")
    return lines


def _transcript_lines(
    turns: Sequence[ConversationTurnRecord],
    agents_by_id: dict[Any, Agent],
) -> list[str]:
    lines: list[str] = []
    for turn in turns:
        speaker = "operator"
        if turn.speaker_kind == ConversationSpeakerKind.AGENT and turn.speaker_agent_id is not None:
            agent = agents_by_id.get(turn.speaker_agent_id)
            speaker = agent.display_name if agent is not None else str(turn.speaker_agent_id)
        body = turn.output_text or turn.error_text or turn.input_text
        lines.append(f"{turn.turn_index}. {speaker} [{turn.status.value}]: {body}")
    return lines
