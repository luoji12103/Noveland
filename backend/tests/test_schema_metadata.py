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
        "platform_settings",
        "scenes",
        "users",
        "world_memberships",
        "worlds",
    } <= table_names()


def test_core_schema_unique_constraints_are_explicit() -> None:
    assert "uq_users_email" in constraint_names("users", UniqueConstraint)
    assert "uq_worlds_slug" in constraint_names("worlds", UniqueConstraint)
    assert "uq_world_memberships_world_user" in constraint_names(
        "world_memberships",
        UniqueConstraint,
    )
    assert "uq_scenes_world_scene_key" in constraint_names("scenes", UniqueConstraint)
    assert "uq_agents_world_agent_key" in constraint_names("agents", UniqueConstraint)
    assert "uq_platform_settings_key" in constraint_names("platform_settings", UniqueConstraint)


def test_core_schema_check_constraints_capture_initial_enums() -> None:
    assert "ck_world_memberships_role" in constraint_names("world_memberships", CheckConstraint)
    assert "ck_agents_kind" in constraint_names("agents", CheckConstraint)


def test_core_schema_world_scoped_foreign_keys_are_present() -> None:
    assert foreign_key_targets("worlds") == {"users.id"}
    assert foreign_key_targets("world_memberships") == {"users.id", "worlds.id"}
    assert foreign_key_targets("scenes") == {"worlds.id"}
    assert foreign_key_targets("agents") == {"scenes.id", "worlds.id"}


def test_core_schema_indexes_cover_world_boundaries() -> None:
    assert "ix_worlds_owner_user_id" in index_names("worlds")
    assert "ix_world_memberships_world_id" in index_names("world_memberships")
    assert "ix_scenes_world_id" in index_names("scenes")
    assert "ix_agents_world_id" in index_names("agents")
