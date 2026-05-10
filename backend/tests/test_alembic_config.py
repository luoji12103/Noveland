import importlib.util
from pathlib import Path
from types import ModuleType

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
    assert revisions[-1] == "20260510_0030"


def test_every_migration_exposes_upgrade_and_downgrade() -> None:
    for migration_file in _migration_files():
        module = _load_migration_module(migration_file)
        assert callable(module.upgrade)
        assert callable(module.downgrade)


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
