from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOYMENT_PROFILE = REPO_ROOT / "docs/agent/operations/deployment-profile.md"


def _deployment_profile_text() -> str:
    return DEPLOYMENT_PROFILE.read_text(encoding="utf-8")


def test_deployment_profile_doc_covers_local_validation_commands() -> None:
    text = _deployment_profile_text()

    for expected in [
        "docker compose -f infra/compose.yaml config",
        "docker compose -f infra/compose.yaml up -d",
        "uv run alembic upgrade head",
        "uv run alembic current",
        "uv run noveland-backup-verify",
        "uv run noveland-runtime --once",
        "GET /health",
        "GET /runtime/supervision",
        "GET /runtime/status",
        "GET /provider-profiles/health",
        "GET /metrics",
    ]:
        assert expected in text


def test_deployment_profile_doc_covers_configuration_and_non_goals() -> None:
    text = _deployment_profile_text()

    for expected in [
        "NOVELAND_DATABASE_URL",
        "NOVELAND_NATS_URL",
        "NOVELAND_OBJECT_STORAGE_ROOT",
        "NOVELAND_API_BASE_URL",
        "NOVELAND_PROVIDER_API_KEYS_JSON",
        "NOVELAND_MEMORY_BACKEND_SECRETS_JSON",
        "No managed-cloud platform lock-in.",
        "No Kubernetes orchestration.",
        "No autoscaling.",
        "No new runtime or deployment endpoint",
    ]:
        assert expected in text


def test_deployment_profile_doc_covers_migration_and_rollback_prerequisites() -> None:
    text = _deployment_profile_text()

    for expected in [
        "## Migration Procedure",
        "## Rollback Prerequisites",
        "docs/agent/operations/backup-restore.md",
        "verified database dump",
        "matching object-storage archive",
        "the runtime daemon stopped",
    ]:
        assert expected in text
