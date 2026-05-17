from __future__ import annotations

from typing import Any

from noveland.visual_generation.contracts import ValidationIssue


def issues_json(issues: tuple[ValidationIssue, ...]) -> dict[str, Any]:
    return {
        "passed": not issues,
        "issues": [issue.model_dump(mode="json") for issue in issues],
    }
