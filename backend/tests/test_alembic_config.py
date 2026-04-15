from pathlib import Path

from alembic.config import Config


def test_alembic_config_loads_script_location() -> None:
    config = Config(Path("alembic.ini"))

    assert config.get_main_option("script_location") == "migrations"
