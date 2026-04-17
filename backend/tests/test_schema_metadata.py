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
        "agent_runtime_runs",
        "agent_calendar_entries",
        "agent_memory_items",
        "auth_sessions",
        "platform_settings",
        "platform_role_assignments",
        "provider_profiles",
        "runtime_control_states",
        "narrative_artifacts",
        "scenes",
        "user_credentials",
        "users",
        "world_events",
        "world_clock_states",
        "world_clock_transitions",
        "world_memberships",
        "world_schedule_rules",
        "world_snapshots",
        "worlds",
    } <= table_names()


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
    assert "uq_world_memberships_world_user" in constraint_names(
        "world_memberships",
        UniqueConstraint,
    )
    assert "uq_scenes_world_scene_key" in constraint_names("scenes", UniqueConstraint)
    assert "uq_agents_world_agent_key" in constraint_names("agents", UniqueConstraint)
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
    assert "uq_world_events_world_sequence" in constraint_names(
        "world_events",
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
    assert "ck_agent_memory_items_visibility" in constraint_names(
        "agent_memory_items",
        CheckConstraint,
    )
    assert "ck_provider_profiles_provider_type" in constraint_names(
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


def test_core_schema_world_scoped_foreign_keys_are_present() -> None:
    assert foreign_key_targets("user_credentials") == {"users.id"}
    assert foreign_key_targets("auth_sessions") == {"users.id"}
    assert foreign_key_targets("platform_role_assignments") == {"users.id"}
    assert foreign_key_targets("worlds") == {"users.id"}
    assert foreign_key_targets("world_memberships") == {"users.id", "worlds.id"}
    assert foreign_key_targets("scenes") == {"worlds.id"}
    assert foreign_key_targets("agents") == {"scenes.id", "worlds.id"}
    assert foreign_key_targets("world_clock_states") == {"worlds.id"}
    assert foreign_key_targets("world_clock_transitions") == {"worlds.id"}
    assert foreign_key_targets("world_events") == {"worlds.id", "world_events.id"}
    assert foreign_key_targets("world_snapshots") == {"worlds.id", "world_events.id"}
    assert foreign_key_targets("agent_calendar_entries") == {"agents.id", "worlds.id"}
    assert foreign_key_targets("world_schedule_rules") == {"worlds.id"}
    assert foreign_key_targets("agent_memory_items") == {
        "agents.id",
        "world_events.id",
        "worlds.id",
    }
    assert foreign_key_targets("provider_profiles") == set()
    assert foreign_key_targets("runtime_control_states") == set()
    assert foreign_key_targets("agent_runtime_runs") == {
        "agent_calendar_entries.id",
        "agents.id",
        "provider_profiles.id",
        "world_events.id",
        "world_schedule_rules.id",
        "worlds.id",
    }
    assert foreign_key_targets("narrative_artifacts") == {
        "agent_runtime_runs.id",
        "agents.id",
        "worlds.id",
    }


def test_core_schema_indexes_cover_world_boundaries() -> None:
    assert "ix_user_credentials_user_id" in index_names("user_credentials")
    assert "ix_auth_sessions_user_id" in index_names("auth_sessions")
    assert "ix_auth_sessions_user_status_expires" in index_names("auth_sessions")
    assert "ix_platform_role_assignments_user_id" in index_names("platform_role_assignments")
    assert "ix_worlds_owner_user_id" in index_names("worlds")
    assert "ix_world_memberships_world_id" in index_names("world_memberships")
    assert "ix_scenes_world_id" in index_names("scenes")
    assert "ix_agents_world_id" in index_names("agents")
    assert "ix_world_clock_states_world_id" in index_names("world_clock_states")
    assert "ix_world_clock_transitions_world_id" in index_names("world_clock_transitions")
    assert "ix_world_clock_transitions_world_wall_time" in index_names(
        "world_clock_transitions",
    )
    assert "ix_world_events_world_sequence" in index_names("world_events")
    assert "ix_world_events_world_event_name" in index_names("world_events")
    assert "ix_world_events_world_wall_time" in index_names("world_events")
    assert "ix_world_snapshots_world_sequence" in index_names("world_snapshots")
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
    assert "ix_agent_runtime_runs_world_agent_started_at" in index_names("agent_runtime_runs")
    assert "ix_agent_runtime_runs_provider_profile_id" in index_names("agent_runtime_runs")
    assert "ix_narrative_artifacts_world_created_at" in index_names("narrative_artifacts")
    assert "ix_narrative_artifacts_world_agent" in index_names("narrative_artifacts")
