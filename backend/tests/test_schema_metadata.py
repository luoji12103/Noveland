from noveland.core.database import Base, import_model_modules
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, UniqueConstraint


def table_names() -> set[str]:
    import_model_modules()
    return set(Base.metadata.tables)


def constraint_names(table_name: str, constraint_type: type[object]) -> set[str]:
    table = Base.metadata.tables[table_name]
    return {
        str(constraint.name)
        for constraint in table.constraints
        if isinstance(constraint, constraint_type) and constraint.name is not None
    }


def index_names(table_name: str) -> set[str]:
    table = Base.metadata.tables[table_name]
    return {
        str(index.name)
        for index in table.indexes
        if isinstance(index, Index) and index.name is not None
    }


def column_names(table_name: str) -> set[str]:
    table = Base.metadata.tables[table_name]
    return {column.name for column in table.columns}


def foreign_key_targets(table_name: str) -> set[str]:
    table = Base.metadata.tables[table_name]
    targets: set[str] = set()
    for constraint in table.constraints:
        if isinstance(constraint, ForeignKeyConstraint):
            for element in constraint.elements:
                targets.add(element.target_fullname)
    return targets


def test_core_schema_tables_are_registered() -> None:
    assert {
        "agents",
        "agent_relationship_edges",
        "agent_presets",
        "agent_observations",
        "agent_personas",
        "agent_runtime_runs",
        "asset_generation_policies",
        "asset_generation_proposals",
        "asset_generation_runs",
        "agent_presence_states",
        "agent_calendar_entries",
        "agent_memory_items",
        "agent_profile_snapshots",
        "authoring_import_proposals",
        "authoring_import_runs",
        "authoring_review_decisions",
        "authoring_source_assets",
        "authoring_source_batches",
        "authoring_source_fragments",
        "authoring_source_traceability",
        "auth_sessions",
        "authoring_import_jobs",
        "authoring_templates",
        "beta_checklist_items",
        "beta_checklist_runs",
        "conversation_participants",
        "conversation_sessions",
        "conversation_turn_presentations",
        "conversation_turns",
        "character_emotional_states",
        "character_knowledge_facts",
        "character_sprite_sets",
        "character_sprite_variants",
        "daily_episode_drafts",
        "daily_life_event_candidates",
        "ending_candidates",
        "event_resolution_rules",
        "event_trigger_conditions",
        "faction_progress_tracks",
        "gm_agendas",
        "gm_event_proposals",
        "gm_style_reviews",
        "group_interaction_contexts",
        "in_world_notifications",
        "living_world_release_profiles",
        "long_run_eval_runs",
        "memory_backend_profiles",
        "media_asset_collection_items",
        "media_asset_collections",
        "media_asset_contexts",
        "media_asset_inputs",
        "media_asset_tags",
        "media_assets",
        "media_jobs",
        "media_objects",
        "media_references",
        "model_invocation_tags",
        "model_invocations",
        "memory_retrieval_logs",
        "memory_write_jobs",
        "memory_write_logs",
        "narrative_continuity_reviews",
        "offscreen_event_queue",
        "organization_conflict_events",
        "organization_memberships",
        "player_actor_profiles",
        "player_choice_records",
        "player_intervention_records",
        "player_journal_entries",
        "player_privacy_requests",
        "platform_settings",
        "plot_threads",
        "platform_role_assignments",
        "prompt_snapshots",
        "prompt_templates",
        "provider_capabilities",
        "provider_health_checks",
        "provider_integrations",
        "provider_profiles",
        "agent_voice_profile_bindings",
        "relationship_repair_records",
        "relationship_event_suggestions",
        "runtime_control_states",
        "runtime_diagnostic_events",
        "narrative_artifacts",
        "narrative_publications",
        "route_affinities",
        "route_milestones",
        "rumor_propagations",
        "rumor_records",
        "scenes",
        "scene_beat_drafts",
        "scene_background_profiles",
        "scene_location_edges",
        "secret_records",
        "story_hooks",
        "speech_style_mappings",
        "speech_transcripts",
        "user_credentials",
        "users",
        "voice_profiles",
        "world_events",
        "world_clock_states",
        "world_clock_transitions",
        "world_bibles",
        "worldlines",
        "world_memberships",
        "world_organizations",
        "world_schedule_rules",
        "world_snapshots",
        "worlds",
    } <= table_names()


def test_agent_preset_version_columns_are_registered() -> None:
    assert "source_preset_version" in column_names("agents")
    assert "version" in column_names("agent_presets")


def test_living_world_character_foundation_columns_are_registered() -> None:
    assert {
        "source_material",
        "canon_timeline",
        "setting_rules",
        "forbidden_changes",
        "sequel_boundaries",
        "continuity_config",
        "metadata",
    } <= column_names("world_bibles")
    assert {
        "narrative_role",
        "importance",
        "canon_status",
        "character_category",
        "character_profile",
    } <= column_names("agents")
    assert {
        "world_id",
        "source_agent_id",
        "target_agent_id",
        "relationship_type",
        "affection",
        "trust",
        "hostility",
        "intimacy",
        "obligation",
        "rivalry",
        "debt",
        "metadata",
    } <= column_names("agent_relationship_edges")


def test_media_kernel_foundation_tables_are_registered() -> None:
    assert {
        "world_id",
        "worldline_id",
        "asset_kind",
        "asset_role",
        "source_kind",
        "status",
        "visibility",
        "storage_uri",
        "preview_uri",
        "thumbnail_uri",
        "mime_type",
        "size_bytes",
        "checksum_sha256",
        "source_job_id",
        "source_event_id",
        "source_invocation_id",
        "metadata",
    } <= column_names("media_assets")
    assert {
        "world_id",
        "worldline_id",
        "conversation_id",
        "turn_id",
        "agent_id",
        "job_kind",
        "provider_kind",
        "source_event_id",
        "source_invocation_id",
        "provider_config_json",
        "status",
        "request_json",
        "result_json",
    } <= column_names("media_jobs")
    assert {
        "world_id",
        "worldline_id",
        "asset_id",
        "conversation_id",
        "turn_id",
        "agent_id",
        "world_event_id",
        "narrative_artifact_id",
        "context_role",
        "metadata",
    } <= column_names("media_asset_contexts")
    assert {
        "world_id",
        "worldline_id",
        "output_asset_id",
        "input_asset_id",
        "source_job_id",
        "input_role",
        "display_order",
    } <= column_names("media_asset_inputs")
    assert {
        "ix_media_assets_worldline_created",
        "ix_media_assets_worldline_kind_role",
        "ix_media_assets_worldline_status",
        "ix_media_assets_source_invocation_id",
    } <= index_names("media_assets")
    assert {
        "media_jobs.id",
        "model_invocations.id",
        "world_events.id",
        "worldlines.id",
        "worlds.id",
    } <= foreign_key_targets("media_assets")
    assert "provider_profiles.id" not in foreign_key_targets("media_jobs")
    assert "model_invocations.id" in foreign_key_targets("media_jobs")
    assert {
        "asset_id",
        "world_id",
        "worldline_id",
        "object_role",
        "storage_uri",
        "filename",
        "mime_type",
        "size_bytes",
        "checksum_sha256",
        "width",
        "height",
        "duration_ms",
        "sample_rate_hz",
        "audio_channels",
        "frame_rate",
        "metadata",
    } <= column_names("media_objects")
    assert {
        "world_id",
        "worldline_id",
        "asset_id",
        "ref_kind",
        "ref_id",
        "ref_role",
        "display_order",
        "metadata",
    } <= column_names("media_references")
    assert {
        "ix_media_objects_worldline_created",
        "ix_media_objects_asset_role",
        "ix_media_objects_checksum",
    } <= index_names("media_objects")
    assert {
        "ix_media_references_worldline_created",
        "ix_media_references_asset_id",
        "ix_media_references_target",
    } <= index_names("media_references")
    assert "uq_media_objects_storage_uri" in constraint_names(
        "media_objects", UniqueConstraint
    )
    assert "uq_media_references_identity" in constraint_names(
        "media_references", UniqueConstraint
    )
    assert {
        "media_assets.id",
        "worldlines.id",
        "worlds.id",
    } <= foreign_key_targets("media_objects")
    assert {
        "media_assets.id",
        "worldlines.id",
        "worlds.id",
    } <= foreign_key_targets("media_references")


def test_provider_execution_kernel_tables_are_registered() -> None:
    assert {
        "world_id",
        "scope_kind",
        "scope_key",
        "provider_kind",
        "adapter_kind",
        "provider_key",
        "display_name",
        "base_url",
        "auth_ref",
        "config_json",
        "default_params_json",
        "status",
        "visibility",
    } <= column_names("provider_integrations")
    assert {
        "provider_integration_id",
        "capability_key",
        "capability_json",
    } <= column_names("provider_capabilities")
    assert {
        "provider_integration_id",
        "status",
        "latency_ms",
        "checked_at",
        "error_text",
        "metadata",
    } <= column_names("provider_health_checks")
    assert {
        "ix_provider_integrations_scope_status",
        "ix_provider_integrations_world_kind",
        "ix_provider_integrations_adapter",
    } <= index_names("provider_integrations")
    assert {
        "ix_provider_capabilities_provider",
        "ix_provider_capabilities_key",
    } <= index_names("provider_capabilities")
    assert {
        "ix_provider_health_checks_provider_checked",
        "ix_provider_health_checks_status",
    } <= index_names("provider_health_checks")
    assert "uq_provider_integrations_key" in constraint_names(
        "provider_integrations", UniqueConstraint
    )
    assert "uq_provider_capabilities_key" in constraint_names(
        "provider_capabilities", UniqueConstraint
    )
    assert foreign_key_targets("provider_integrations") == {"worlds.id"}
    assert foreign_key_targets("provider_capabilities") == {"provider_integrations.id"}
    assert foreign_key_targets("provider_health_checks") == {"provider_integrations.id"}


def test_speech_voice_pipeline_tables_are_registered() -> None:
    assert {
        "world_id",
        "worldline_id",
        "profile_key",
        "display_name",
        "status",
        "visibility",
        "owner_kind",
        "owner_agent_id",
        "provider_integration_id",
        "provider_voice_id",
        "default_language",
        "supported_languages",
        "voice_kind",
        "reference_asset_id",
        "consent_status",
        "usage_policy",
        "metadata",
    } <= column_names("voice_profiles")
    assert {
        "world_id",
        "worldline_id",
        "agent_id",
        "voice_profile_id",
        "binding_role",
        "priority",
        "is_default",
        "style_overrides",
    } <= column_names("agent_voice_profile_bindings")
    assert {
        "world_id",
        "worldline_id",
        "source_asset_id",
        "media_job_id",
        "model_invocation_id",
        "conversation_id",
        "turn_id",
        "speaker_actor_ref",
        "language",
        "transcript_text",
        "segments",
        "confidence",
        "status",
        "visibility",
    } <= column_names("speech_transcripts")
    assert {
        "world_id",
        "mapping_key",
        "provider_kind",
        "emotion_key",
        "style",
    } <= column_names("speech_style_mappings")
    assert {
        "ix_voice_profiles_worldline_status",
        "ix_voice_profiles_owner_agent",
        "ix_voice_profiles_provider",
        "ix_voice_profiles_reference_asset",
    } <= index_names("voice_profiles")
    assert {
        "ix_agent_voice_profile_bindings_agent",
        "ix_agent_voice_profile_bindings_profile",
    } <= index_names("agent_voice_profile_bindings")
    assert {
        "ix_speech_transcripts_worldline_created",
        "ix_speech_transcripts_source_asset",
        "ix_speech_transcripts_media_job",
        "ix_speech_transcripts_invocation",
        "ix_speech_transcripts_turn",
    } <= index_names("speech_transcripts")
    assert "ix_speech_style_mappings_world_provider" in index_names(
        "speech_style_mappings"
    )
    assert "uq_voice_profiles_key" in constraint_names("voice_profiles", UniqueConstraint)
    assert "uq_agent_voice_profile_bindings_role" in constraint_names(
        "agent_voice_profile_bindings",
        UniqueConstraint,
    )
    assert "uq_speech_style_mappings_key" in constraint_names(
        "speech_style_mappings",
        UniqueConstraint,
    )
    assert foreign_key_targets("voice_profiles") == {
        "agents.id",
        "media_assets.id",
        "provider_integrations.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("agent_voice_profile_bindings") == {
        "agents.id",
        "voice_profiles.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("speech_transcripts") == {
        "conversation_sessions.id",
        "conversation_turns.id",
        "media_assets.id",
        "media_jobs.id",
        "model_invocations.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("speech_style_mappings") == {"worlds.id"}


def test_visual_asset_system_tables_are_registered() -> None:
    assert {
        "world_id",
        "worldline_id",
        "agent_id",
        "style_key",
        "display_name",
        "default_variant_id",
        "status",
        "visibility",
        "metadata",
    } <= column_names("character_sprite_sets")
    assert {
        "world_id",
        "worldline_id",
        "sprite_set_id",
        "asset_id",
        "expression_key",
        "pose_key",
        "outfit_key",
        "mood_tags",
        "priority",
        "is_default",
        "status",
        "visibility",
        "metadata",
    } <= column_names("character_sprite_variants")
    assert {
        "world_id",
        "worldline_id",
        "scene_id",
        "location_key",
        "time_of_day",
        "weather_key",
        "asset_id",
        "priority",
        "is_default",
        "status",
        "visibility",
        "metadata",
    } <= column_names("scene_background_profiles")
    assert Base.metadata.tables["character_sprite_sets"].c.worldline_id.nullable is False
    assert Base.metadata.tables["character_sprite_variants"].c.worldline_id.nullable is False
    assert Base.metadata.tables["scene_background_profiles"].c.worldline_id.nullable is False
    assert {
        "ix_character_sprite_sets_worldline_agent",
        "ix_character_sprite_sets_worldline_status",
    } <= index_names("character_sprite_sets")
    assert {
        "ix_character_sprite_variants_set",
        "ix_character_sprite_variants_worldline_expr",
        "ix_character_sprite_variants_asset",
    } <= index_names("character_sprite_variants")
    assert {
        "ix_scene_background_profiles_worldline_scene",
        "ix_scene_background_profiles_worldline_location",
        "ix_scene_background_profiles_asset",
    } <= index_names("scene_background_profiles")
    assert "uq_character_sprite_sets_agent_style" in constraint_names(
        "character_sprite_sets",
        UniqueConstraint,
    )
    assert "uq_character_sprite_variants_asset_keys" in constraint_names(
        "character_sprite_variants",
        UniqueConstraint,
    )
    assert foreign_key_targets("character_sprite_sets") == {
        "agents.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("character_sprite_variants") == {
        "character_sprite_sets.id",
        "media_assets.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("scene_background_profiles") == {
        "media_assets.id",
        "scenes.id",
        "worldlines.id",
        "worlds.id",
    }


def test_conversation_turn_presentation_tables_are_registered() -> None:
    assert {
        "world_id",
        "worldline_id",
        "conversation_id",
        "turn_id",
        "speaker_agent_id",
        "emotion_key",
        "emotion_intensity",
        "sprite_set_id",
        "sprite_variant_id",
        "voice_profile_id",
        "tts_media_asset_id",
        "background_asset_id",
        "composite_scene_asset_id",
        "transcript_id",
        "presentation",
        "render_state",
    } <= column_names("conversation_turn_presentations")
    assert (
        Base.metadata.tables["conversation_turn_presentations"].c.worldline_id.nullable
        is False
    )
    assert {
        "ix_conversation_turn_presentations_worldline_turn",
        "ix_conversation_turn_presentations_conversation",
        "ix_conversation_turn_presentations_speaker",
    } <= index_names("conversation_turn_presentations")
    assert "uq_conversation_turn_presentations_turn" in constraint_names(
        "conversation_turn_presentations",
        UniqueConstraint,
    )
    assert foreign_key_targets("conversation_turn_presentations") == {
        "agents.id",
        "character_sprite_sets.id",
        "character_sprite_variants.id",
        "conversation_sessions.id",
        "conversation_turns.id",
        "media_assets.id",
        "speech_transcripts.id",
        "voice_profiles.id",
        "worldlines.id",
        "worlds.id",
    }


def test_authoring_import_core_tables_are_registered() -> None:
    assert {
        "world_id",
        "worldline_id",
        "batch_key",
        "display_name",
        "description",
        "source_kind",
        "status",
        "visibility",
        "metadata",
        "created_by_actor_ref",
    } <= column_names("authoring_source_batches")
    assert {
        "world_id",
        "worldline_id",
        "batch_id",
        "media_asset_id",
        "source_asset_kind",
        "source_label",
        "source_ref",
        "status",
        "metadata",
    } <= column_names("authoring_source_assets")
    assert {
        "world_id",
        "worldline_id",
        "source_asset_id",
        "fragment_key",
        "fragment_kind",
        "sequence",
        "excerpt_text",
        "locator",
        "metadata",
    } <= column_names("authoring_source_fragments")
    assert {
        "world_id",
        "worldline_id",
        "source_batch_id",
        "run_kind",
        "status",
        "summary",
        "created_by_actor_ref",
    } <= column_names("authoring_import_runs")
    assert {
        "world_id",
        "worldline_id",
        "run_id",
        "source_fragment_id",
        "proposal_kind",
        "target_ref_kind",
        "target_ref_id",
        "title",
        "summary",
        "proposed_payload",
        "evidence",
        "confidence",
        "priority",
        "status",
        "applied_ref",
    } <= column_names("authoring_import_proposals")
    assert {
        "world_id",
        "worldline_id",
        "proposal_id",
        "decision",
        "reason",
        "decision_payload",
        "decided_by_actor_ref",
    } <= column_names("authoring_review_decisions")
    assert {
        "world_id",
        "worldline_id",
        "source_fragment_id",
        "proposal_id",
        "applied_ref_kind",
        "applied_ref_id",
        "trace_kind",
        "metadata",
    } <= column_names("authoring_source_traceability")
    assert Base.metadata.tables["authoring_source_batches"].c.worldline_id.nullable is False
    assert Base.metadata.tables["authoring_source_assets"].c.worldline_id.nullable is False
    assert Base.metadata.tables["authoring_source_fragments"].c.worldline_id.nullable is False
    assert Base.metadata.tables["authoring_import_runs"].c.worldline_id.nullable is False
    assert Base.metadata.tables["authoring_import_proposals"].c.worldline_id.nullable is False
    assert {
        "ix_authoring_source_batches_worldline_status",
        "ix_authoring_source_batches_kind",
    } <= index_names("authoring_source_batches")
    assert {
        "ix_authoring_source_assets_batch",
        "ix_authoring_source_assets_worldline_status",
        "ix_authoring_source_assets_media_asset",
    } <= index_names("authoring_source_assets")
    assert {
        "ix_authoring_source_fragments_asset_sequence",
        "ix_authoring_source_fragments_worldline_kind",
    } <= index_names("authoring_source_fragments")
    assert {
        "ix_authoring_import_runs_worldline_created",
        "ix_authoring_import_runs_source_batch",
    } <= index_names("authoring_import_runs")
    assert {
        "ix_authoring_import_proposals_run_priority",
        "ix_authoring_import_proposals_worldline_status",
        "ix_authoring_import_proposals_fragment",
    } <= index_names("authoring_import_proposals")
    assert "uq_authoring_source_batches_key" in constraint_names(
        "authoring_source_batches",
        UniqueConstraint,
    )
    assert "uq_authoring_source_fragments_key" in constraint_names(
        "authoring_source_fragments",
        UniqueConstraint,
    )
    assert foreign_key_targets("authoring_source_assets") == {
        "authoring_source_batches.id",
        "media_assets.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("authoring_import_proposals") == {
        "authoring_import_runs.id",
        "authoring_source_fragments.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("authoring_source_traceability") == {
        "authoring_import_proposals.id",
        "authoring_source_fragments.id",
        "worldlines.id",
        "worlds.id",
    }


def test_media_asset_catalog_tables_are_registered() -> None:
    assert {
        "world_id",
        "worldline_id",
        "asset_id",
        "tag_type",
        "tag_key",
        "tag_value",
        "confidence",
        "source_kind",
        "visibility",
        "created_by_actor_ref",
        "metadata",
    } <= column_names("media_asset_tags")
    assert {
        "world_id",
        "worldline_id",
        "collection_kind",
        "title",
        "description",
        "owner_agent_id",
        "visibility",
        "status",
        "created_by_actor_ref",
        "metadata",
    } <= column_names("media_asset_collections")
    assert {
        "world_id",
        "worldline_id",
        "collection_id",
        "asset_id",
        "role",
        "display_order",
        "metadata",
    } <= column_names("media_asset_collection_items")
    assert {
        "ix_media_asset_tags_worldline_tag",
        "ix_media_asset_tags_worldline_visibility",
        "ix_media_asset_tags_asset_id",
    } <= index_names("media_asset_tags")
    assert {
        "ix_media_asset_collections_worldline_kind",
        "ix_media_asset_collections_worldline_visibility",
        "ix_media_asset_collections_worldline_status_created",
        "ix_media_asset_collections_owner_agent_id",
    } <= index_names("media_asset_collections")
    assert {
        "ix_media_asset_collection_items_collection_order",
        "ix_media_asset_collection_items_asset_id",
        "ix_media_asset_collection_items_worldline_asset",
    } <= index_names("media_asset_collection_items")
    assert "uq_media_asset_tags_identity" in constraint_names(
        "media_asset_tags", UniqueConstraint
    )
    assert "uq_media_asset_collection_items_collection_asset_role" in constraint_names(
        "media_asset_collection_items", UniqueConstraint
    )
    assert {
        "media_assets.id",
        "worldlines.id",
        "worlds.id",
    } <= foreign_key_targets("media_asset_tags")
    assert {
        "agents.id",
        "worldlines.id",
        "worlds.id",
    } <= foreign_key_targets("media_asset_collections")
    assert {
        "media_asset_collections.id",
        "media_assets.id",
        "worldlines.id",
        "worlds.id",
    } <= foreign_key_targets("media_asset_collection_items")


def test_model_invocation_ledger_tables_are_registered() -> None:
    assert {
        "world_id",
        "worldline_id",
        "trace_id",
        "parent_invocation_id",
        "invocation_kind",
        "actor_kind",
        "actor_ref",
        "agent_id",
        "conversation_id",
        "turn_id",
        "world_event_id",
        "media_job_id",
        "media_asset_id",
        "memory_write_job_id",
        "provider_kind",
        "provider_profile_id",
        "model_name",
        "prompt_template_key",
        "input_text",
        "output_text",
        "request_params_json",
        "response_metadata_json",
        "usage_json",
        "latency_ms",
        "estimated_cost",
        "status",
        "visibility",
        "redaction_status",
        "retention_policy",
        "contains_sensitive_context",
        "purge_after",
    } <= column_names("model_invocations")
    assert {
        "scope_kind",
        "world_id",
        "scope_key",
        "template_key",
        "version",
        "invocation_kind",
        "title",
        "content",
        "input_schema_json",
        "output_schema_json",
        "metadata",
        "status",
    } <= column_names("prompt_templates")
    assert {
        "invocation_id",
        "template_id",
        "raw_prompt_text",
        "raw_messages_json",
        "raw_request_json",
        "raw_response_json",
        "raw_output_text",
        "normalized_output_json",
        "prompt_context_snapshot_json",
        "tool_definitions_json",
        "context_pack_refs_json",
        "input_asset_refs_json",
        "prompt_checksum_sha256",
        "request_checksum_sha256",
        "response_checksum_sha256",
        "output_checksum_sha256",
        "visibility",
        "redaction_status",
        "contains_sensitive_context",
    } <= column_names("prompt_snapshots")
    assert {
        "world_id",
        "worldline_id",
        "agent_runtime_run_id",
        "model_invocation_id",
        "invocation_role",
        "sequence_index",
    } <= column_names("agent_runtime_run_model_invocations")
    assert {
        "world_id",
        "worldline_id",
        "invocation_id",
        "tag_type",
        "tag_key",
        "tag_value",
    } <= column_names("model_invocation_tags")
    assert {
        "ix_model_invocations_worldline_created",
        "ix_model_invocations_worldline_kind",
        "ix_model_invocations_worldline_status",
        "ix_model_invocations_trace",
        "ix_model_invocations_parent",
        "ix_model_invocations_provider_model",
        "ix_model_invocations_agent",
        "ix_model_invocations_conversation_turn",
        "ix_model_invocations_media",
        "ix_model_invocations_memory_job",
    } <= index_names("model_invocations")
    assert {
        "ix_prompt_templates_scope_status",
        "ix_prompt_templates_key_status",
    } <= index_names("prompt_templates")
    assert "ix_prompt_snapshots_template_id" in index_names("prompt_snapshots")
    assert {
        "ix_agent_run_invocations_run",
        "ix_agent_run_invocations_invocation",
        "ix_agent_run_invocations_worldline",
    } <= index_names("agent_runtime_run_model_invocations")
    assert {
        "ix_model_invocation_tags_lookup",
        "ix_model_invocation_tags_invocation",
    } <= index_names("model_invocation_tags")
    assert "uq_prompt_templates_key" in constraint_names("prompt_templates", UniqueConstraint)
    assert "uq_prompt_snapshots_invocation_id" in constraint_names(
        "prompt_snapshots", UniqueConstraint
    )
    assert "uq_agent_run_invocations_run_invocation" in constraint_names(
        "agent_runtime_run_model_invocations", UniqueConstraint
    )
    assert "uq_agent_run_invocations_run_sequence" in constraint_names(
        "agent_runtime_run_model_invocations", UniqueConstraint
    )
    assert "uq_model_invocation_tags_identity" in constraint_names(
        "model_invocation_tags", UniqueConstraint
    )
    assert {
        "agents.id",
        "conversation_sessions.id",
        "conversation_turns.id",
        "media_assets.id",
        "media_jobs.id",
        "memory_write_jobs.id",
        "model_invocations.id",
        "provider_profiles.id",
        "world_events.id",
        "worldlines.id",
        "worlds.id",
    } <= foreign_key_targets("model_invocations")
    assert foreign_key_targets("prompt_templates") == {"worlds.id"}
    assert {
        "model_invocations.id",
        "prompt_templates.id",
    } <= foreign_key_targets("prompt_snapshots")
    assert {
        "agent_runtime_runs.id",
        "model_invocations.id",
        "worldlines.id",
        "worlds.id",
    } <= foreign_key_targets("agent_runtime_run_model_invocations")
    assert {
        "model_invocations.id",
        "worldlines.id",
        "worlds.id",
    } <= foreign_key_targets("model_invocation_tags")


def test_living_world_autonomous_system_columns_are_registered() -> None:
    assert {"importance"} <= column_names("world_events")
    assert {"region_key", "location_tags", "opening_rules"} <= column_names("scenes")
    assert {
        "organization_key",
        "organization_type",
        "public_summary",
        "hidden_summary",
        "metadata",
    } <= column_names("world_organizations")
    assert {"role_title", "visibility", "loyalty", "influence", "responsibilities"} <= column_names(
        "organization_memberships",
    )
    assert {"track_key", "track_type", "progress", "pressure", "summary"} <= column_names(
        "faction_progress_tracks",
    )
    assert {"source_scene_id", "target_scene_id", "traversal_rules"} <= column_names(
        "scene_location_edges",
    )
    assert {"visibility_status", "encounter_eligible", "scheduled_movement"} <= column_names(
        "agent_presence_states",
    )
    assert {"title", "summary", "importance", "starts_at", "status"} <= column_names(
        "daily_life_event_candidates",
    )
    assert {"event_name", "payload", "due_at", "importance", "status"} <= column_names(
        "offscreen_event_queue",
    )


def test_living_world_gm_choices_worldline_columns_are_registered() -> None:
    assert {
        "worldline_key",
        "parent_worldline_id",
        "forked_from_snapshot_id",
        "fork_event_sequence",
        "status",
        "created_by_actor_ref",
        "metadata",
    } <= column_names("worldlines")
    assert {"worldline_id"} <= column_names("world_events")
    assert {"worldline_id"} <= column_names("world_snapshots")
    assert {"worldline_id"} <= column_names("agent_memory_items")
    assert {"worldline_id"} <= column_names("memory_write_jobs")
    assert {"worldline_id"} <= column_names("memory_retrieval_logs")
    assert {"worldline_id"} <= column_names("agent_relationship_edges")
    assert {"worldline_id"} <= column_names("faction_progress_tracks")
    assert {"worldline_id"} <= column_names("agent_presence_states")
    assert {"worldline_id"} <= column_names("daily_life_event_candidates")
    assert {"worldline_id"} <= column_names("offscreen_event_queue")
    assert {"worldline_id", "title", "summary", "priority", "status"} <= column_names(
        "gm_agendas",
    )
    assert {
        "worldline_id",
        "agenda_id",
        "title",
        "reason",
        "proposed_payload",
        "importance",
        "risk_score",
        "status",
    } <= column_names("gm_event_proposals")
    assert {"rule_key", "conditions", "effects", "status"} <= column_names(
        "event_resolution_rules",
    )
    assert {"worldline_id", "user_id", "actor_ref", "profile"} <= column_names(
        "player_actor_profiles",
    )
    assert {
        "worldline_id",
        "player_actor_id",
        "choice_key",
        "choice_kind",
        "context",
        "consequence_preview",
    } <= column_names("player_choice_records")


def test_living_world_plot_route_rumor_flow_columns_are_registered() -> None:
    assert {
        "worldline_id",
        "hook_key",
        "hook_type",
        "summary",
        "status",
        "priority",
        "owner_agent_id",
        "target_agent_id",
        "due_at",
        "resolution",
    } <= column_names("story_hooks")
    assert {
        "worldline_id",
        "thread_key",
        "thread_type",
        "status",
        "next_beats",
        "participant_agent_ids",
        "organization_ids",
        "related_event_ids",
    } <= column_names("plot_threads")
    assert {"worldline_id", "agent_id", "route_key", "affinity", "stage", "flags"} <= column_names(
        "route_affinities",
    )
    assert {"condition_key", "conditions", "status", "priority"} <= column_names(
        "event_trigger_conditions",
    )
    assert {
        "worldline_id",
        "source_kind",
        "setup",
        "dialogue_beats",
        "choice_points",
        "aftermath",
        "participant_agent_ids",
        "scene_id",
        "status",
    } <= column_names("scene_beat_drafts")
    assert {
        "worldline_id",
        "source_candidate_id",
        "scene_beat_draft_id",
        "participant_agent_ids",
        "status",
    } <= column_names("daily_episode_drafts")
    assert {
        "worldline_id",
        "context_key",
        "interaction_type",
        "scene_id",
        "organization_id",
        "participant_agent_ids",
        "participant_roles",
        "constraints",
        "status",
    } <= column_names("group_interaction_contexts")
    assert {
        "worldline_id",
        "relationship_id",
        "source_agent_id",
        "target_agent_id",
        "suggested_event_name",
        "score",
        "status",
    } <= column_names("relationship_event_suggestions")
    assert {
        "worldline_id",
        "organization_id",
        "faction_track_id",
        "pressure_delta",
        "progress_delta",
        "resolved_event_id",
        "status",
    } <= column_names("organization_conflict_events")
    assert {
        "worldline_id",
        "rumor_key",
        "content",
        "source_agent_id",
        "source_organization_id",
        "visibility",
        "known_agent_ids",
        "status",
    } <= column_names("rumor_records")
    assert {
        "worldline_id",
        "rumor_id",
        "source_agent_id",
        "target_agent_id",
        "target_organization_id",
        "propagation_reason",
        "delivered_event_id",
        "status",
    } <= column_names("rumor_propagations")


def test_living_world_knowledge_player_guardrail_columns_are_registered() -> None:
    assert {
        "worldline_id",
        "agent_id",
        "fact_key",
        "knowledge_kind",
        "content",
        "source_event_id",
        "confidence",
        "visibility",
        "is_active",
    } <= column_names("character_knowledge_facts")
    assert {
        "worldline_id",
        "secret_key",
        "title",
        "holder_agent_ids",
        "reveal_conditions",
        "consequence_metadata",
        "visibility",
        "status",
        "revealed_event_id",
    } <= column_names("secret_records")
    assert {
        "worldline_id",
        "agent_id",
        "mood",
        "stress",
        "fatigue",
        "anticipation",
        "jealousy",
        "anger",
        "source_event_id",
        "expires_at",
    } <= column_names("character_emotional_states")
    assert {
        "worldline_id",
        "relationship_id",
        "repair_kind",
        "reason",
        "score_delta",
        "status",
        "applied_event_id",
    } <= column_names("relationship_repair_records")
    assert {
        "worldline_id",
        "user_id",
        "player_actor_id",
        "entry_kind",
        "title",
        "source_event_id",
        "visibility",
    } <= column_names("player_journal_entries")
    assert {
        "worldline_id",
        "user_id",
        "notification_kind",
        "title",
        "source_event_id",
        "status",
    } <= column_names("in_world_notifications")
    assert {
        "worldline_id",
        "user_id",
        "player_actor_id",
        "intervention_kind",
        "target_agent_id",
        "target_scene_id",
        "choice_id",
        "event_id",
        "status",
    } <= column_names("player_intervention_records")
    assert {
        "world_id",
        "worldline_id",
        "user_id",
        "request_kind",
        "status",
        "target_ref_kind",
        "target_ref_id",
        "reason",
        "summary",
        "redaction_plan",
        "created_by_actor_ref",
        "reviewed_by_actor_ref",
        "reviewed_at",
        "review_note",
        "metadata",
    } <= column_names("player_privacy_requests")
    assert Base.metadata.tables["player_privacy_requests"].c.worldline_id.nullable is False
    assert {
        "ix_player_privacy_requests_worldline_user",
        "ix_player_privacy_requests_status",
    } <= index_names("player_privacy_requests")
    assert {
        "ck_player_privacy_requests_request_kind",
        "ck_player_privacy_requests_status",
    } <= constraint_names("player_privacy_requests", CheckConstraint)
    assert foreign_key_targets("player_privacy_requests") == {
        "users.id",
        "worldlines.id",
        "worlds.id",
    }
    assert {
        "worldline_id",
        "source_kind",
        "source_ref",
        "reviewed_text",
        "status",
        "diagnostics",
    } <= column_names("gm_style_reviews")
    assert {
        "worldline_id",
        "artifact_id",
        "source_kind",
        "source_ref",
        "reviewed_text",
        "status",
        "issues",
    } <= column_names("narrative_continuity_reviews")


def test_living_world_beta_release_readiness_columns_are_registered() -> None:
    assert {
        "worldline_id",
        "route_affinity_id",
        "plot_thread_id",
        "agent_id",
        "milestone_key",
        "stage",
        "status",
        "conditions",
        "evidence_metadata",
    } <= column_names("route_milestones")
    assert {
        "worldline_id",
        "route_affinity_id",
        "plot_thread_id",
        "agent_id",
        "ending_key",
        "ending_type",
        "status",
        "requirements",
        "outcome_summary",
        "evidence_metadata",
    } <= column_names("ending_candidates")
    assert {
        "worldline_id",
        "eval_key",
        "horizon_days",
        "status",
        "started_at",
        "finished_at",
        "metrics",
        "recommendations",
        "blockers",
    } <= column_names("long_run_eval_runs")
    assert {
        "template_key",
        "template_kind",
        "name",
        "content",
        "validation_issues",
        "is_active",
    } <= column_names("authoring_templates")
    assert {
        "template_id",
        "status",
        "preview_summary",
        "applied_refs",
        "validation_issues",
    } <= column_names("authoring_import_jobs")
    assert {
        "profile_key",
        "status",
        "branch_policy",
        "backup_policy",
        "content_review_policy",
        "player_permission_policy",
        "worldline_policy",
        "checklist",
    } <= column_names("living_world_release_profiles")
    assert {
        "worldline_id",
        "run_key",
        "status",
        "summary",
        "evidence",
        "blocker_count",
        "created_by_actor_ref",
    } <= column_names("beta_checklist_runs")
    assert {"run_id", "item_key", "title", "status", "evidence", "recommendation"} <= column_names(
        "beta_checklist_items",
    )


def test_core_schema_unique_constraints_are_explicit() -> None:
    assert "uq_users_email" in constraint_names("users", UniqueConstraint)
    assert "uq_user_credentials_user_id" in constraint_names(
        "user_credentials",
        UniqueConstraint,
    )
    assert "uq_auth_sessions_token_hash" in constraint_names(
        "auth_sessions",
        UniqueConstraint,
    )
    assert "uq_platform_role_assignments_user_role" in constraint_names(
        "platform_role_assignments",
        UniqueConstraint,
    )
    assert "uq_worlds_slug" in constraint_names("worlds", UniqueConstraint)
    assert "uq_world_bibles_world_id" in constraint_names("world_bibles", UniqueConstraint)
    assert "uq_world_memberships_world_user" in constraint_names(
        "world_memberships",
        UniqueConstraint,
    )
    assert "uq_scenes_world_scene_key" in constraint_names("scenes", UniqueConstraint)
    assert "uq_agents_world_agent_key" in constraint_names("agents", UniqueConstraint)
    assert "uq_agent_presets_preset_key" in constraint_names(
        "agent_presets",
        UniqueConstraint,
    )
    assert "uq_agent_relationship_edges_source_target_type" in constraint_names(
        "agent_relationship_edges",
        UniqueConstraint,
    )
    assert "uq_world_organizations_world_key" in constraint_names(
        "world_organizations",
        UniqueConstraint,
    )
    assert "uq_organization_memberships_organization_agent" in constraint_names(
        "organization_memberships",
        UniqueConstraint,
    )
    assert "uq_faction_progress_tracks_organization_key" in constraint_names(
        "faction_progress_tracks",
        UniqueConstraint,
    )
    assert "uq_scene_location_edges_pair" in constraint_names(
        "scene_location_edges",
        UniqueConstraint,
    )
    assert "uq_agent_presence_states_world_agent" in constraint_names(
        "agent_presence_states",
        UniqueConstraint,
    )
    assert "uq_agent_personas_agent_id" in constraint_names(
        "agent_personas",
        UniqueConstraint,
    )
    assert "uq_world_schedule_rules_world_rule_key" in constraint_names(
        "world_schedule_rules",
        UniqueConstraint,
    )
    assert "uq_platform_settings_key" in constraint_names("platform_settings", UniqueConstraint)
    assert "uq_world_clock_states_world_id" in constraint_names(
        "world_clock_states",
        UniqueConstraint,
    )
    assert "uq_world_clock_transitions_world_revision" in constraint_names(
        "world_clock_transitions",
        UniqueConstraint,
    )
    assert "uq_world_events_worldline_sequence" in constraint_names(
        "world_events",
        UniqueConstraint,
    )
    assert "uq_worldlines_world_key" in constraint_names("worldlines", UniqueConstraint)
    assert "uq_event_resolution_rules_world_key" in constraint_names(
        "event_resolution_rules",
        UniqueConstraint,
    )
    assert "uq_player_actor_profiles_scope_user" in constraint_names(
        "player_actor_profiles",
        UniqueConstraint,
    )
    assert "uq_story_hooks_scope_key" in constraint_names("story_hooks", UniqueConstraint)
    assert "uq_plot_threads_scope_key" in constraint_names("plot_threads", UniqueConstraint)
    assert "uq_route_affinities_scope_agent_key" in constraint_names(
        "route_affinities",
        UniqueConstraint,
    )
    assert "uq_event_trigger_conditions_world_key" in constraint_names(
        "event_trigger_conditions",
        UniqueConstraint,
    )
    assert "uq_group_interaction_contexts_scope_key" in constraint_names(
        "group_interaction_contexts",
        UniqueConstraint,
    )
    assert "uq_rumor_records_scope_key" in constraint_names(
        "rumor_records",
        UniqueConstraint,
    )
    assert "uq_character_knowledge_facts_scope_agent_key" in constraint_names(
        "character_knowledge_facts",
        UniqueConstraint,
    )
    assert "uq_secret_records_scope_key" in constraint_names(
        "secret_records",
        UniqueConstraint,
    )
    assert "uq_character_emotional_states_scope_agent" in constraint_names(
        "character_emotional_states",
        UniqueConstraint,
    )
    assert "uq_route_milestones_scope_key" in constraint_names(
        "route_milestones",
        UniqueConstraint,
    )
    assert "uq_ending_candidates_scope_key" in constraint_names(
        "ending_candidates",
        UniqueConstraint,
    )
    assert "uq_authoring_templates_world_key" in constraint_names(
        "authoring_templates",
        UniqueConstraint,
    )
    assert "uq_living_world_release_profiles_world_id" in constraint_names(
        "living_world_release_profiles",
        UniqueConstraint,
    )
    assert "uq_beta_checklist_items_run_key" in constraint_names(
        "beta_checklist_items",
        UniqueConstraint,
    )
    assert "uq_memory_backend_profiles_profile_key" in constraint_names(
        "memory_backend_profiles",
        UniqueConstraint,
    )
    assert "uq_memory_write_jobs_dedupe_key" in constraint_names(
        "memory_write_jobs",
        UniqueConstraint,
    )
    assert "uq_agent_profile_snapshots_worldline_agent" in constraint_names(
        "agent_profile_snapshots",
        UniqueConstraint,
    )
    assert "uq_conversation_sessions_world_session_key" in constraint_names(
        "conversation_sessions",
        UniqueConstraint,
    )
    assert "uq_conversation_participants_session_agent" in constraint_names(
        "conversation_participants",
        UniqueConstraint,
    )
    assert "uq_conversation_participants_session_turn_order" in constraint_names(
        "conversation_participants",
        UniqueConstraint,
    )
    assert "uq_conversation_turns_session_turn_index" in constraint_names(
        "conversation_turns",
        UniqueConstraint,
    )
    assert "uq_provider_profiles_profile_key" in constraint_names(
        "provider_profiles",
        UniqueConstraint,
    )
    assert "uq_runtime_control_states_control_key" in constraint_names(
        "runtime_control_states",
        UniqueConstraint,
    )
    assert "uq_narrative_publications_artifact_id" in constraint_names(
        "narrative_publications",
        UniqueConstraint,
    )


def test_core_schema_check_constraints_capture_initial_enums() -> None:
    assert "ck_world_memberships_role" in constraint_names("world_memberships", CheckConstraint)
    assert "ck_user_credentials_password_hash_present" in constraint_names(
        "user_credentials",
        CheckConstraint,
    )
    assert "ck_auth_sessions_status" in constraint_names(
        "auth_sessions",
        CheckConstraint,
    )
    assert "ck_auth_sessions_token_hash_length" in constraint_names(
        "auth_sessions",
        CheckConstraint,
    )
    assert "ck_platform_role_assignments_role" in constraint_names(
        "platform_role_assignments",
        CheckConstraint,
    )
    assert "ck_agents_kind" in constraint_names("agents", CheckConstraint)
    assert "ck_agents_narrative_role" in constraint_names("agents", CheckConstraint)
    assert "ck_agents_importance" in constraint_names("agents", CheckConstraint)
    assert "ck_agents_canon_status" in constraint_names("agents", CheckConstraint)
    assert "ck_agents_character_category" in constraint_names("agents", CheckConstraint)
    assert "ck_agent_relationship_edges_relationship_type" in constraint_names(
        "agent_relationship_edges",
        CheckConstraint,
    )
    assert "ck_agent_relationship_edges_distinct_agents" in constraint_names(
        "agent_relationship_edges",
        CheckConstraint,
    )
    assert "ck_agent_presets_default_kind" in constraint_names(
        "agent_presets",
        CheckConstraint,
    )
    assert "ck_world_clock_states_status" in constraint_names(
        "world_clock_states",
        CheckConstraint,
    )
    assert "ck_world_clock_states_speed_multiplier_positive" in constraint_names(
        "world_clock_states",
        CheckConstraint,
    )
    assert "ck_world_clock_states_wall_time_anchor_matches_status" in constraint_names(
        "world_clock_states",
        CheckConstraint,
    )
    assert "ck_world_clock_transitions_transition_type" in constraint_names(
        "world_clock_transitions",
        CheckConstraint,
    )
    assert "ck_world_clock_transitions_new_status" in constraint_names(
        "world_clock_transitions",
        CheckConstraint,
    )
    assert "ck_world_events_sequence_positive" in constraint_names(
        "world_events",
        CheckConstraint,
    )
    assert "ck_world_events_event_name_format" in constraint_names(
        "world_events",
        CheckConstraint,
    )
    assert "ck_world_events_importance" in constraint_names(
        "world_events",
        CheckConstraint,
    )
    assert "ck_worldlines_status" in constraint_names("worldlines", CheckConstraint)
    assert "ck_worldlines_fork_event_sequence_nonnegative" in constraint_names(
        "worldlines",
        CheckConstraint,
    )
    assert "ck_gm_agendas_status" in constraint_names("gm_agendas", CheckConstraint)
    assert "ck_gm_event_proposals_status" in constraint_names(
        "gm_event_proposals",
        CheckConstraint,
    )
    assert "ck_event_resolution_rules_status" in constraint_names(
        "event_resolution_rules",
        CheckConstraint,
    )
    assert "ck_player_choice_records_choice_kind" in constraint_names(
        "player_choice_records",
        CheckConstraint,
    )
    assert "ck_story_hooks_hook_type" in constraint_names("story_hooks", CheckConstraint)
    assert "ck_story_hooks_status" in constraint_names("story_hooks", CheckConstraint)
    assert "ck_plot_threads_thread_type" in constraint_names("plot_threads", CheckConstraint)
    assert "ck_plot_threads_status" in constraint_names("plot_threads", CheckConstraint)
    assert "ck_route_affinities_status" in constraint_names(
        "route_affinities",
        CheckConstraint,
    )
    assert "ck_event_trigger_conditions_status" in constraint_names(
        "event_trigger_conditions",
        CheckConstraint,
    )
    assert "ck_scene_beat_drafts_source_kind" in constraint_names(
        "scene_beat_drafts",
        CheckConstraint,
    )
    assert "ck_scene_beat_drafts_status" in constraint_names(
        "scene_beat_drafts",
        CheckConstraint,
    )
    assert "ck_daily_episode_drafts_status" in constraint_names(
        "daily_episode_drafts",
        CheckConstraint,
    )
    assert "ck_group_interaction_contexts_interaction_type" in constraint_names(
        "group_interaction_contexts",
        CheckConstraint,
    )
    assert "ck_group_interaction_contexts_status" in constraint_names(
        "group_interaction_contexts",
        CheckConstraint,
    )
    assert "ck_relationship_event_suggestions_status" in constraint_names(
        "relationship_event_suggestions",
        CheckConstraint,
    )
    assert "ck_organization_conflict_events_status" in constraint_names(
        "organization_conflict_events",
        CheckConstraint,
    )
    assert "ck_rumor_records_visibility" in constraint_names("rumor_records", CheckConstraint)
    assert "ck_rumor_records_status" in constraint_names("rumor_records", CheckConstraint)
    assert "ck_rumor_propagations_status" in constraint_names(
        "rumor_propagations",
        CheckConstraint,
    )
    assert "ck_character_knowledge_facts_knowledge_kind" in constraint_names(
        "character_knowledge_facts",
        CheckConstraint,
    )
    assert "ck_character_knowledge_facts_visibility" in constraint_names(
        "character_knowledge_facts",
        CheckConstraint,
    )
    assert "ck_secret_records_status" in constraint_names("secret_records", CheckConstraint)
    assert "ck_secret_records_visibility" in constraint_names("secret_records", CheckConstraint)
    assert "ck_character_emotional_states_stress_range" in constraint_names(
        "character_emotional_states",
        CheckConstraint,
    )
    assert "ck_relationship_repair_records_repair_kind" in constraint_names(
        "relationship_repair_records",
        CheckConstraint,
    )
    assert "ck_relationship_repair_records_status" in constraint_names(
        "relationship_repair_records",
        CheckConstraint,
    )
    assert "ck_player_journal_entries_entry_kind" in constraint_names(
        "player_journal_entries",
        CheckConstraint,
    )
    assert "ck_in_world_notifications_notification_kind" in constraint_names(
        "in_world_notifications",
        CheckConstraint,
    )
    assert "ck_in_world_notifications_status" in constraint_names(
        "in_world_notifications",
        CheckConstraint,
    )
    assert "ck_player_intervention_records_intervention_kind" in constraint_names(
        "player_intervention_records",
        CheckConstraint,
    )
    assert "ck_player_intervention_records_status" in constraint_names(
        "player_intervention_records",
        CheckConstraint,
    )
    assert "ck_gm_style_reviews_status" in constraint_names(
        "gm_style_reviews",
        CheckConstraint,
    )
    assert "ck_narrative_continuity_reviews_status" in constraint_names(
        "narrative_continuity_reviews",
        CheckConstraint,
    )
    assert "ck_route_milestones_status" in constraint_names(
        "route_milestones",
        CheckConstraint,
    )
    assert "ck_ending_candidates_ending_type" in constraint_names(
        "ending_candidates",
        CheckConstraint,
    )
    assert "ck_ending_candidates_status" in constraint_names(
        "ending_candidates",
        CheckConstraint,
    )
    assert "ck_long_run_eval_runs_status" in constraint_names(
        "long_run_eval_runs",
        CheckConstraint,
    )
    assert "ck_authoring_templates_template_kind" in constraint_names(
        "authoring_templates",
        CheckConstraint,
    )
    assert "ck_authoring_import_jobs_status" in constraint_names(
        "authoring_import_jobs",
        CheckConstraint,
    )
    assert "ck_living_world_release_profiles_status" in constraint_names(
        "living_world_release_profiles",
        CheckConstraint,
    )
    assert "ck_beta_checklist_runs_status" in constraint_names(
        "beta_checklist_runs",
        CheckConstraint,
    )
    assert "ck_beta_checklist_items_status" in constraint_names(
        "beta_checklist_items",
        CheckConstraint,
    )
    assert "ck_world_organizations_organization_type" in constraint_names(
        "world_organizations",
        CheckConstraint,
    )
    assert "ck_organization_memberships_visibility" in constraint_names(
        "organization_memberships",
        CheckConstraint,
    )
    assert "ck_faction_progress_tracks_track_type" in constraint_names(
        "faction_progress_tracks",
        CheckConstraint,
    )
    assert "ck_scene_location_edges_distinct_scenes" in constraint_names(
        "scene_location_edges",
        CheckConstraint,
    )
    assert "ck_agent_presence_states_visibility_status" in constraint_names(
        "agent_presence_states",
        CheckConstraint,
    )
    assert "ck_daily_life_event_candidates_status" in constraint_names(
        "daily_life_event_candidates",
        CheckConstraint,
    )
    assert "ck_offscreen_event_queue_status" in constraint_names(
        "offscreen_event_queue",
        CheckConstraint,
    )
    assert "ck_world_snapshots_status" in constraint_names(
        "world_snapshots",
        CheckConstraint,
    )
    assert "ck_world_snapshots_payload_or_uri" in constraint_names(
        "world_snapshots",
        CheckConstraint,
    )
    assert "ck_agent_calendar_entries_status" in constraint_names(
        "agent_calendar_entries",
        CheckConstraint,
    )
    assert "ck_agent_calendar_entries_ends_after_starts" in constraint_names(
        "agent_calendar_entries",
        CheckConstraint,
    )
    assert "ck_world_schedule_rules_kind" in constraint_names(
        "world_schedule_rules",
        CheckConstraint,
    )
    assert "ck_conversation_sessions_scope_type" in constraint_names(
        "conversation_sessions",
        CheckConstraint,
    )
    assert "ck_conversation_sessions_mode" in constraint_names(
        "conversation_sessions",
        CheckConstraint,
    )
    assert "ck_conversation_sessions_status" in constraint_names(
        "conversation_sessions",
        CheckConstraint,
    )
    assert "ck_conversation_sessions_terminal_reason" in constraint_names(
        "conversation_sessions",
        CheckConstraint,
    )
    assert "ck_conversation_participants_turn_order_non_negative" in constraint_names(
        "conversation_participants",
        CheckConstraint,
    )
    assert "ck_conversation_turns_speaker_kind" in constraint_names(
        "conversation_turns",
        CheckConstraint,
    )
    assert "ck_conversation_turns_status" in constraint_names(
        "conversation_turns",
        CheckConstraint,
    )
    assert "ck_agent_memory_items_visibility" in constraint_names(
        "agent_memory_items",
        CheckConstraint,
    )
    assert "ck_agent_observations_observation_type_present" in constraint_names(
        "agent_observations",
        CheckConstraint,
    )
    assert "ck_agent_observations_review_status" in constraint_names(
        "agent_observations",
        CheckConstraint,
    )
    assert "ck_agent_observations_confidence_score_range" in constraint_names(
        "agent_observations",
        CheckConstraint,
    )
    assert "ck_agent_observations_runtime_use_count_non_negative" in constraint_names(
        "agent_observations",
        CheckConstraint,
    )
    assert "ck_provider_profiles_provider_type" in constraint_names(
        "provider_profiles",
        CheckConstraint,
    )
    assert "ck_provider_profiles_timeout_seconds_positive" in constraint_names(
        "provider_profiles",
        CheckConstraint,
    )
    assert "ck_provider_profiles_retry_attempts_non_negative" in constraint_names(
        "provider_profiles",
        CheckConstraint,
    )
    assert "ck_provider_profiles_rate_limit_per_minute_positive" in constraint_names(
        "provider_profiles",
        CheckConstraint,
    )
    assert "ck_provider_profiles_last_test_status" in constraint_names(
        "provider_profiles",
        CheckConstraint,
    )
    assert "ck_runtime_control_states_desired_state" in constraint_names(
        "runtime_control_states",
        CheckConstraint,
    )
    assert "ck_agent_runtime_runs_status" in constraint_names(
        "agent_runtime_runs",
        CheckConstraint,
    )
    assert "ck_agent_runtime_runs_trigger_source" in constraint_names(
        "agent_runtime_runs",
        CheckConstraint,
    )
    assert "ck_narrative_artifacts_artifact_kind" in constraint_names(
        "narrative_artifacts",
        CheckConstraint,
    )
    assert "ck_narrative_publications_status" in constraint_names(
        "narrative_publications",
        CheckConstraint,
    )
    assert "ck_runtime_diagnostic_events_severity" in constraint_names(
        "runtime_diagnostic_events",
        CheckConstraint,
    )
    assert "ck_runtime_diagnostic_events_component" in constraint_names(
        "runtime_diagnostic_events",
        CheckConstraint,
    )


def test_core_schema_world_scoped_foreign_keys_are_present() -> None:
    assert foreign_key_targets("user_credentials") == {"users.id"}
    assert foreign_key_targets("auth_sessions") == {"users.id"}
    assert foreign_key_targets("platform_role_assignments") == {"users.id"}
    assert foreign_key_targets("worlds") == {"memory_backend_profiles.id", "users.id"}
    assert foreign_key_targets("world_bibles") == {"worlds.id"}
    assert foreign_key_targets("world_memberships") == {"users.id", "worlds.id"}
    assert foreign_key_targets("scenes") == {"worlds.id"}
    assert foreign_key_targets("agents") == {"agent_presets.id", "scenes.id", "worlds.id"}
    assert foreign_key_targets("agent_relationship_edges") == {
        "agents.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("agent_presets") == set()
    assert foreign_key_targets("agent_personas") == {"agents.id", "worlds.id"}
    assert foreign_key_targets("agent_observations") == {
        "agents.id",
        "agent_runtime_runs.id",
        "world_events.id",
        "worlds.id",
    }
    assert foreign_key_targets("world_clock_states") == {"worlds.id"}
    assert foreign_key_targets("world_clock_transitions") == {"worlds.id"}
    assert foreign_key_targets("world_events") == {
        "worldlines.id",
        "worlds.id",
        "world_events.id",
    }
    assert foreign_key_targets("world_organizations") == {"worlds.id"}
    assert foreign_key_targets("organization_memberships") == {
        "agents.id",
        "world_organizations.id",
        "worlds.id",
    }
    assert foreign_key_targets("faction_progress_tracks") == {
        "worldlines.id",
        "world_organizations.id",
        "worlds.id",
    }
    assert foreign_key_targets("scene_location_edges") == {
        "scenes.id",
        "worlds.id",
    }
    assert foreign_key_targets("agent_presence_states") == {
        "agents.id",
        "scenes.id",
        "world_events.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("daily_life_event_candidates") == {
        "agents.id",
        "scenes.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("offscreen_event_queue") == {
        "daily_life_event_candidates.id",
        "world_events.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("world_snapshots") == {
        "worldlines.id",
        "worlds.id",
        "world_events.id",
    }
    assert foreign_key_targets("conversation_sessions") == {
        "scenes.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("conversation_participants") == {
        "agents.id",
        "conversation_sessions.id",
    }
    assert foreign_key_targets("conversation_turns") == {
        "agent_runtime_runs.id",
        "agents.id",
        "conversation_sessions.id",
    }
    assert foreign_key_targets("agent_calendar_entries") == {"agents.id", "worlds.id"}
    assert foreign_key_targets("world_schedule_rules") == {"worlds.id"}
    assert foreign_key_targets("agent_memory_items") == {
        "agents.id",
        "world_events.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("memory_backend_profiles") == set()
    assert foreign_key_targets("memory_write_jobs") == {
        "agents.id",
        "memory_backend_profiles.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("memory_write_logs") == {"memory_write_jobs.id"}
    assert foreign_key_targets("memory_retrieval_logs") == {
        "agents.id",
        "memory_backend_profiles.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("worldlines") == {
        "world_snapshots.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("gm_agendas") == {"worldlines.id", "worlds.id"}
    assert foreign_key_targets("gm_event_proposals") == {
        "gm_agendas.id",
        "world_events.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("event_resolution_rules") == {"worlds.id"}
    assert foreign_key_targets("player_actor_profiles") == {
        "scenes.id",
        "users.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("player_choice_records") == {
        "player_actor_profiles.id",
        "users.id",
        "world_events.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("story_hooks") == {
        "agents.id",
        "world_events.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("plot_threads") == {"worldlines.id", "worlds.id"}
    assert foreign_key_targets("route_affinities") == {
        "agents.id",
        "player_choice_records.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("event_trigger_conditions") == {"worlds.id"}
    assert foreign_key_targets("scene_beat_drafts") == {
        "scenes.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("daily_episode_drafts") == {
        "daily_life_event_candidates.id",
        "scene_beat_drafts.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("group_interaction_contexts") == {
        "scenes.id",
        "world_organizations.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("relationship_event_suggestions") == {
        "agent_relationship_edges.id",
        "agents.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("organization_conflict_events") == {
        "faction_progress_tracks.id",
        "world_events.id",
        "world_organizations.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("rumor_records") == {
        "agents.id",
        "world_organizations.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("rumor_propagations") == {
        "agents.id",
        "rumor_records.id",
        "world_events.id",
        "world_organizations.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("character_knowledge_facts") == {
        "agents.id",
        "world_events.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("secret_records") == {
        "world_events.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("character_emotional_states") == {
        "agents.id",
        "world_events.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("relationship_repair_records") == {
        "agent_relationship_edges.id",
        "world_events.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("player_journal_entries") == {
        "player_actor_profiles.id",
        "users.id",
        "world_events.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("in_world_notifications") == {
        "users.id",
        "world_events.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("player_intervention_records") == {
        "agents.id",
        "player_actor_profiles.id",
        "player_choice_records.id",
        "scenes.id",
        "users.id",
        "world_events.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("gm_style_reviews") == {"worldlines.id", "worlds.id"}
    assert foreign_key_targets("narrative_continuity_reviews") == {
        "narrative_artifacts.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("agent_profile_snapshots") == {
        "agents.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("provider_profiles") == set()
    assert foreign_key_targets("provider_integrations") == {"worlds.id"}
    assert foreign_key_targets("provider_capabilities") == {"provider_integrations.id"}
    assert foreign_key_targets("provider_health_checks") == {"provider_integrations.id"}
    assert foreign_key_targets("runtime_control_states") == set()
    assert foreign_key_targets("agent_runtime_runs") == {
        "agent_calendar_entries.id",
        "agents.id",
        "provider_profiles.id",
        "world_events.id",
        "worldlines.id",
        "world_schedule_rules.id",
        "worlds.id",
    }
    assert foreign_key_targets("model_invocations") == {
        "agents.id",
        "conversation_sessions.id",
        "conversation_turns.id",
        "media_assets.id",
        "media_jobs.id",
        "memory_write_jobs.id",
        "model_invocations.id",
        "provider_profiles.id",
        "world_events.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("media_objects") == {
        "media_assets.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("media_references") == {
        "media_assets.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("prompt_templates") == {"worlds.id"}
    assert foreign_key_targets("prompt_snapshots") == {
        "model_invocations.id",
        "prompt_templates.id",
    }
    assert foreign_key_targets("agent_runtime_run_model_invocations") == {
        "agent_runtime_runs.id",
        "model_invocations.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("model_invocation_tags") == {
        "model_invocations.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("narrative_artifacts") == {
        "conversation_sessions.id",
        "agent_runtime_runs.id",
        "agents.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("narrative_publications") == {
        "narrative_artifacts.id",
        "users.id",
        "worldlines.id",
        "worlds.id",
    }
    assert foreign_key_targets("runtime_diagnostic_events") == {
        "agent_runtime_runs.id",
        "agents.id",
        "provider_profiles.id",
        "worlds.id",
    }


def test_core_schema_indexes_cover_world_boundaries() -> None:
    assert "ix_user_credentials_user_id" in index_names("user_credentials")
    assert "ix_auth_sessions_user_id" in index_names("auth_sessions")
    assert "ix_auth_sessions_user_status_expires" in index_names("auth_sessions")
    assert "ix_platform_role_assignments_user_id" in index_names("platform_role_assignments")
    assert "ix_worlds_owner_user_id" in index_names("worlds")
    assert "ix_world_bibles_world_id" in index_names("world_bibles")
    assert "ix_world_memberships_world_id" in index_names("world_memberships")
    assert "ix_scenes_world_id" in index_names("scenes")
    assert "ix_agents_world_id" in index_names("agents")
    assert "ix_agents_source_preset_id" in index_names("agents")
    assert "ix_agents_world_canon_status" in index_names("agents")
    assert "ix_agents_world_character_category" in index_names("agents")
    assert "ix_agent_relationship_edges_world_source" in index_names(
        "agent_relationship_edges",
    )
    assert "ix_agent_relationship_edges_world_target" in index_names(
        "agent_relationship_edges",
    )
    assert "ix_agent_relationship_edges_worldline_source" in index_names(
        "agent_relationship_edges",
    )
    assert "ix_agent_presets_is_active" in index_names("agent_presets")
    assert "ix_agent_personas_world_agent" in index_names("agent_personas")
    assert "ix_agent_observations_world_agent_observed" in index_names("agent_observations")
    assert "ix_agent_observations_source_event_id" in index_names("agent_observations")
    assert "ix_agent_observations_world_agent_review" in index_names("agent_observations")
    assert "ix_agent_observations_last_used_run_id" in index_names("agent_observations")
    assert "uq_agent_observations_agent_source_event" in index_names("agent_observations")
    assert "ix_world_clock_states_world_id" in index_names("world_clock_states")
    assert "ix_world_clock_transitions_world_id" in index_names("world_clock_transitions")
    assert "ix_world_clock_transitions_world_wall_time" in index_names(
        "world_clock_transitions",
    )
    assert "ix_world_events_world_sequence" in index_names("world_events")
    assert "ix_world_events_world_event_name" in index_names("world_events")
    assert "ix_world_events_world_wall_time" in index_names("world_events")
    assert "ix_world_events_world_importance" in index_names("world_events")
    assert "ix_world_events_worldline_sequence" in index_names("world_events")
    assert "ix_worldlines_world_status" in index_names("worldlines")
    assert "ix_worldlines_parent_worldline_id" in index_names("worldlines")
    assert "ix_scenes_world_region" in index_names("scenes")
    assert "ix_world_organizations_world_id" in index_names("world_organizations")
    assert "ix_world_organizations_world_type" in index_names("world_organizations")
    assert "ix_organization_memberships_world_agent" in index_names("organization_memberships")
    assert "ix_organization_memberships_world_organization" in index_names(
        "organization_memberships",
    )
    assert "ix_faction_progress_tracks_world_organization" in index_names(
        "faction_progress_tracks",
    )
    assert "ix_faction_progress_tracks_world_type" in index_names("faction_progress_tracks")
    assert "ix_faction_progress_tracks_worldline_organization" in index_names(
        "faction_progress_tracks",
    )
    assert "ix_scene_location_edges_world_source" in index_names("scene_location_edges")
    assert "ix_scene_location_edges_world_target" in index_names("scene_location_edges")
    assert "ix_agent_presence_states_world_agent" in index_names("agent_presence_states")
    assert "ix_agent_presence_states_world_scene" in index_names("agent_presence_states")
    assert "ix_agent_presence_states_worldline_agent" in index_names(
        "agent_presence_states",
    )
    assert "ix_daily_life_event_candidates_world_status" in index_names(
        "daily_life_event_candidates",
    )
    assert "ix_daily_life_event_candidates_world_time" in index_names(
        "daily_life_event_candidates",
    )
    assert "ix_daily_life_event_candidates_worldline_status" in index_names(
        "daily_life_event_candidates",
    )
    assert "ix_offscreen_event_queue_world_status_due" in index_names("offscreen_event_queue")
    assert "ix_offscreen_event_queue_world_importance" in index_names("offscreen_event_queue")
    assert "ix_offscreen_event_queue_worldline_status_due" in index_names(
        "offscreen_event_queue",
    )
    assert "ix_story_hooks_worldline_status" in index_names("story_hooks")
    assert "ix_story_hooks_worldline_type" in index_names("story_hooks")
    assert "ix_plot_threads_worldline_status" in index_names("plot_threads")
    assert "ix_plot_threads_worldline_type" in index_names("plot_threads")
    assert "ix_route_affinities_worldline_agent" in index_names("route_affinities")
    assert "ix_route_affinities_worldline_status" in index_names("route_affinities")
    assert "ix_event_trigger_conditions_world_status" in index_names(
        "event_trigger_conditions",
    )
    assert "ix_scene_beat_drafts_worldline_status" in index_names("scene_beat_drafts")
    assert "ix_scene_beat_drafts_source" in index_names("scene_beat_drafts")
    assert "ix_daily_episode_drafts_worldline_status" in index_names(
        "daily_episode_drafts",
    )
    assert "ix_daily_episode_drafts_source_candidate" in index_names(
        "daily_episode_drafts",
    )
    assert "ix_group_interaction_contexts_worldline_status" in index_names(
        "group_interaction_contexts",
    )
    assert "ix_relationship_event_suggestions_worldline_status" in index_names(
        "relationship_event_suggestions",
    )
    assert "ix_relationship_event_suggestions_relationship" in index_names(
        "relationship_event_suggestions",
    )
    assert "ix_organization_conflict_events_worldline_status" in index_names(
        "organization_conflict_events",
    )
    assert "ix_organization_conflict_events_track" in index_names(
        "organization_conflict_events",
    )
    assert "ix_rumor_records_worldline_status" in index_names("rumor_records")
    assert "ix_rumor_records_worldline_visibility" in index_names("rumor_records")
    assert "ix_rumor_propagations_rumor_status" in index_names("rumor_propagations")
    assert "ix_rumor_propagations_worldline_target" in index_names("rumor_propagations")
    assert "ix_character_knowledge_facts_worldline_agent" in index_names(
        "character_knowledge_facts",
    )
    assert "ix_character_knowledge_facts_worldline_kind" in index_names(
        "character_knowledge_facts",
    )
    assert "ix_secret_records_worldline_status" in index_names("secret_records")
    assert "ix_secret_records_worldline_visibility" in index_names("secret_records")
    assert "ix_character_emotional_states_worldline_agent" in index_names(
        "character_emotional_states",
    )
    assert "ix_relationship_repair_records_worldline_status" in index_names(
        "relationship_repair_records",
    )
    assert "ix_relationship_repair_records_relationship" in index_names(
        "relationship_repair_records",
    )
    assert "ix_player_journal_entries_worldline_user" in index_names(
        "player_journal_entries",
    )
    assert "ix_player_journal_entries_source_event" in index_names(
        "player_journal_entries",
    )
    assert "ix_in_world_notifications_worldline_user" in index_names(
        "in_world_notifications",
    )
    assert "ix_in_world_notifications_source_event" in index_names(
        "in_world_notifications",
    )
    assert "ix_player_intervention_records_worldline_user" in index_names(
        "player_intervention_records",
    )
    assert "ix_player_intervention_records_choice" in index_names(
        "player_intervention_records",
    )
    assert "ix_gm_style_reviews_worldline_status" in index_names("gm_style_reviews")
    assert "ix_gm_style_reviews_source" in index_names("gm_style_reviews")
    assert "ix_narrative_continuity_reviews_worldline_status" in index_names(
        "narrative_continuity_reviews",
    )
    assert "ix_narrative_continuity_reviews_artifact" in index_names(
        "narrative_continuity_reviews",
    )
    assert "ix_conversation_sessions_world_id" in index_names("conversation_sessions")
    assert "ix_conversation_sessions_scene_id" in index_names("conversation_sessions")
    assert "ix_conversation_sessions_world_mode_status" in index_names("conversation_sessions")
    assert "ix_conversation_sessions_worldline_mode_status" in index_names(
        "conversation_sessions",
    )
    assert "ix_conversation_participants_session_id" in index_names("conversation_participants")
    assert "ix_conversation_participants_agent_id" in index_names("conversation_participants")
    assert "ix_conversation_turns_session_id" in index_names("conversation_turns")
    assert "ix_conversation_turns_speaker_agent_id" in index_names("conversation_turns")
    assert "ix_conversation_turns_run_id" in index_names("conversation_turns")
    assert "ix_world_snapshots_world_sequence" in index_names("world_snapshots")
    assert "ix_world_snapshots_worldline_sequence" in index_names("world_snapshots")
    assert "ix_world_snapshots_world_latest_valid" in index_names("world_snapshots")
    assert "ix_agent_calendar_entries_world_agent_starts" in index_names(
        "agent_calendar_entries",
    )
    assert "ix_agent_calendar_entries_world_agent_status" in index_names(
        "agent_calendar_entries",
    )
    assert "ix_world_schedule_rules_world_id" in index_names("world_schedule_rules")
    assert "ix_world_schedule_rules_world_enabled" in index_names("world_schedule_rules")
    assert "ix_agent_memory_items_world_agent" in index_names("agent_memory_items")
    assert "ix_agent_memory_items_world_agent_active" in index_names("agent_memory_items")
    assert "ix_agent_memory_items_source_event_id" in index_names("agent_memory_items")
    assert "ix_agent_memory_items_worldline_agent" in index_names("agent_memory_items")
    assert "ix_agent_memory_items_worldline_agent_active" in index_names(
        "agent_memory_items",
    )
    assert "ix_memory_write_jobs_status_next_attempt_at" in index_names("memory_write_jobs")
    assert "ix_memory_write_jobs_world_agent" in index_names("memory_write_jobs")
    assert "ix_memory_write_jobs_backend_profile_id" in index_names("memory_write_jobs")
    assert "ix_memory_write_jobs_worldline_agent" in index_names("memory_write_jobs")
    assert "ix_memory_write_logs_job_id" in index_names("memory_write_logs")
    assert "ix_memory_write_logs_occurred_at" in index_names("memory_write_logs")
    assert "ix_memory_retrieval_logs_world_agent" in index_names("memory_retrieval_logs")
    assert "ix_memory_retrieval_logs_worldline_agent" in index_names(
        "memory_retrieval_logs",
    )
    assert "ix_memory_retrieval_logs_occurred_at" in index_names("memory_retrieval_logs")
    assert "ix_agent_profile_snapshots_worldline_agent" in index_names(
        "agent_profile_snapshots",
    )
    assert "ix_agent_runtime_runs_world_agent_started_at" in index_names("agent_runtime_runs")
    assert "ix_agent_runtime_runs_worldline_agent_started_at" in index_names(
        "agent_runtime_runs",
    )
    assert "ix_agent_runtime_runs_provider_profile_id" in index_names("agent_runtime_runs")
    assert "ix_narrative_artifacts_world_created_at" in index_names("narrative_artifacts")
    assert "ix_narrative_artifacts_worldline_created_at" in index_names("narrative_artifacts")
    assert "ix_narrative_artifacts_world_agent" in index_names("narrative_artifacts")
    assert "ix_narrative_artifacts_world_conversation_created_at" in index_names(
        "narrative_artifacts",
    )
    assert "ix_narrative_publications_world_status_visible" in index_names(
        "narrative_publications",
    )
    assert "ix_narrative_publications_worldline_status_visible" in index_names(
        "narrative_publications",
    )
    assert "ix_narrative_publications_world_published_at" in index_names(
        "narrative_publications",
    )
    assert "ix_narrative_publications_source_draft" in index_names("narrative_publications")
    assert "ix_runtime_diagnostic_events_occurred_at" in index_names(
        "runtime_diagnostic_events",
    )
    assert "ix_runtime_diagnostic_events_severity_component" in index_names(
        "runtime_diagnostic_events",
    )
    assert "ix_runtime_diagnostic_events_world_occurred_at" in index_names(
        "runtime_diagnostic_events",
    )
    assert "ix_runtime_diagnostic_events_agent_occurred_at" in index_names(
        "runtime_diagnostic_events",
    )


def test_conversation_schema_includes_policy_and_terminal_columns() -> None:
    assert {"policy_config", "writer_config", "memory_config", "terminal_reason"} <= column_names(
        "conversation_sessions",
    )


def test_world_schema_includes_memory_backend_profile_column() -> None:
    assert {"memory_backend_profile_id"} <= column_names("worlds")


def test_narrative_schema_includes_conversation_source_column() -> None:
    assert {"worldline_id", "source_conversation_id"} <= column_names("narrative_artifacts")
    assert Base.metadata.tables["narrative_artifacts"].c.worldline_id.nullable is True


def test_narrative_publication_schema_includes_workflow_columns() -> None:
    assert {
        "worldline_id",
        "artifact_id",
        "source_draft_id",
        "status",
        "reader_visible",
        "metadata",
        "published_at",
        "unpublished_at",
        "published_by_user_id",
    } <= column_names("narrative_publications")
    assert Base.metadata.tables["narrative_publications"].c.worldline_id.nullable is True
