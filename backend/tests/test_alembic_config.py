import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any, cast

from alembic.config import Config


def test_alembic_config_loads_script_location() -> None:
    config = Config(Path("alembic.ini"))

    assert config.get_main_option("script_location") == "migrations"


def test_migration_versions_are_linear_and_ordered() -> None:
    migration_files = _migration_files()
    revisions = [_module_value(path, "revision") for path in migration_files]
    down_revisions = [_module_value(path, "down_revision") for path in migration_files]

    assert len(revisions) == len(set(revisions))
    revision_matches_filename = [
        path.stem.startswith(str(revision))
        for path, revision in zip(migration_files, revisions, strict=True)
    ]
    assert revision_matches_filename == [True] * len(migration_files)
    assert down_revisions[0] is None
    assert down_revisions[1:] == revisions[:-1]
    assert revisions[-1] == "20260520_0048"


def test_every_migration_exposes_upgrade_and_downgrade() -> None:
    for migration_file in _migration_files():
        module = _load_migration_module(migration_file)
        assert callable(module.upgrade)
        assert callable(module.downgrade)


def test_conversation_policy_json_default_does_not_compile_numeric_values_as_bindparams() -> None:
    module = _load_migration_module(
        Path("migrations/versions/20260421_0012_conversation_policies_stop_conditions.py")
    )

    server_default = module.policy_config_server_default()
    compiled_default = str(server_default.compile(compile_kwargs={"literal_binds": True}))

    assert not server_default._bindparams
    assert '"max_consecutive_failed_turns":2' in compiled_default
    assert "NULL" not in compiled_default


def test_conversation_writer_json_default_does_not_compile_json_literals_as_bindparams() -> None:
    module = _load_migration_module(
        Path("migrations/versions/20260421_0013_narrative_writer_summarizer.py")
    )

    server_default = module.writer_config_server_default()
    compiled_default = str(server_default.compile(compile_kwargs={"literal_binds": True}))

    assert not server_default._bindparams
    assert '"provider_profile_id":null' in compiled_default
    assert '"auto_generate_on_complete":false' in compiled_default
    assert "NULL" not in compiled_default


def test_narrative_writer_migration_identifiers_fit_postgresql_limit() -> None:
    module = _load_migration_module(
        Path("migrations/versions/20260421_0013_narrative_writer_summarizer.py")
    )

    assert len(module.SOURCE_CONVERSATION_FK_NAME) <= 63


def test_media_kernel_replace_check_uses_preformatted_constraint_names() -> None:
    module = cast(
        Any,
        _load_migration_module(Path("migrations/versions/20260512_0033_media_kernel.py")),
    )
    fake_op = _FakeMigrationOp()
    original_op = module.op
    module.op = fake_op
    try:
        module._replace_check(
            "media_assets",
            "ck_media_assets_asset_kind",
            "asset_kind IN ('image')",
        )
    finally:
        module.op = original_op

    assert fake_op.calls == [
        (
            "drop_constraint",
            "formatted:ck_media_assets_asset_kind",
            "media_assets",
            "check",
        ),
        (
            "create_check_constraint",
            "formatted:ck_media_assets_asset_kind",
            "media_assets",
            "asset_kind IN ('image')",
        ),
    ]


def _migration_files() -> list[Path]:
    return sorted(
        path for path in Path("migrations/versions").glob("*.py") if not path.name.startswith("__")
    )


def _module_value(path: Path, name: str) -> object:
    return getattr(_load_migration_module(path), name)


def _load_migration_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeMigrationOp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, str]] = []

    def f(self, name: str) -> str:
        return f"formatted:{name}"

    def drop_constraint(self, name: str, table_name: str, *, type_: str) -> None:
        self.calls.append(("drop_constraint", name, table_name, type_))

    def create_check_constraint(self, name: str, table_name: str, condition: str) -> None:
        self.calls.append(("create_check_constraint", name, table_name, condition))
