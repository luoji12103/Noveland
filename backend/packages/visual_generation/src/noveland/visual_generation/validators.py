from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from noveland.providers.contracts import ProviderAdapterKind, ProviderKind
from noveland.providers.routing import ProviderRoutingError, validate_provider_adapter_compatibility
from noveland.providers.secrets import ProviderSecretValidationError, reject_sensitive_config
from noveland.visual_generation.contracts import (
    ValidationIssue,
    ValidationSeverity,
    VisualGenerationPlanValidationResult,
)

FORBIDDEN_KEY_PATTERN = re.compile(
    r"("
    r"storage_uri|storageurl|storage_url|filesystem|filepath|file_path|object_storage|"
    r"s3_url|gcs_url|signed_url|bytes|base64|b64|raw_prompt|raw_output|"
    r"prompt_snapshot|resolved_secret|api_key|secret|authorization|bearer|password|token"
    r")",
    re.IGNORECASE,
)
PATH_LIKE_PATTERN = re.compile(r"(^/|^[A-Za-z]:\\|\\|s3://|gs://|file://)")
RAW_WORKFLOW_KEYS = {
    "raw_workflow_json",
    "workflow_json",
    "comfyui_workflow_json",
    "prompt_graph",
    "nodes",
}


def safe_json_or_raise(value: object, *, field_name: str) -> None:
    try:
        reject_sensitive_config(value, field_name=field_name)
    except ProviderSecretValidationError as exc:
        raise ValueError(str(exc)) from exc
    issues = leak_issues(value, field_name=field_name)
    if issues:
        first = issues[0]
        raise ValueError(first.message)


def leak_issues(value: object, *, field_name: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    _collect_leak_issues(value, path=field_name, issues=issues)
    return issues


def reject_raw_workflow_payload(value: object, *, field_name: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    _collect_raw_workflow_issues(value, path=field_name, issues=issues)
    return issues


def validate_provider_adapter(
    provider_kind: ProviderKind,
    adapter_kind: ProviderAdapterKind,
) -> list[ValidationIssue]:
    try:
        validate_provider_adapter_compatibility(provider_kind, adapter_kind)
    except ProviderRoutingError as exc:
        return [_issue("provider_adapter_mismatch", str(exc), field="provider")]
    if provider_kind not in {
        ProviderKind.IMAGE_GENERATION,
        ProviderKind.IMAGE_EDITING,
        ProviderKind.IMAGE_ANALYSIS,
        ProviderKind.IMAGE_COMPOSITION,
        ProviderKind.WORKFLOW_ENGINE,
        ProviderKind.OTHER,
    }:
        return [
            _issue(
                "provider_kind_not_visual",
                "provider kind is not valid for visual generation",
                field="provider_kind",
            )
        ]
    return []


def validate_slots(
    parameter_schema: Mapping[str, Any],
    provided_slots: Mapping[str, Any],
) -> VisualGenerationPlanValidationResult:
    allowed = _schema_string_set(parameter_schema.get("slots"))
    required = _schema_string_set(parameter_schema.get("required"))
    if not allowed and isinstance(parameter_schema.get("properties"), dict):
        allowed = set(parameter_schema["properties"].keys())
    issues: list[ValidationIssue] = []
    if not allowed and provided_slots:
        issues.append(
            _issue(
                "template_has_no_slots",
                "workflow template version does not expose parameter slots",
                field="workflow_template_version.parameter_schema_json",
            )
        )
    for slot in sorted(provided_slots):
        if slot not in allowed:
            issues.append(
                _issue(
                    "slot_not_allowed",
                    f"slot '{slot}' is not allowed by workflow template",
                    field=f"slots.{slot}",
                )
            )
    for slot in sorted(required):
        if slot not in provided_slots or provided_slots.get(slot) in (None, "", [], {}):
            issues.append(
                _issue(
                    "slot_required",
                    f"slot '{slot}' is required by workflow template",
                    field=f"slots.{slot}",
                )
            )
    for issue in leak_issues(dict(provided_slots), field_name="slots"):
        issues.append(issue)
    for issue in reject_raw_workflow_payload(dict(provided_slots), field_name="slots"):
        issues.append(issue)
    return VisualGenerationPlanValidationResult(
        passed=not any(issue.severity == ValidationSeverity.ERROR for issue in issues),
        issues=tuple(issues),
        normalized_slot_values_json={key: provided_slots[key] for key in sorted(provided_slots)},
    )


def sanitize_validation_metadata(value: object) -> dict[str, Any]:
    issues = leak_issues(value, field_name="validation_error")
    if issues:
        return {
            "sanitized": True,
            "issue_codes": [issue.code for issue in issues],
            "message": "validation metadata contained sensitive fields and was redacted",
        }
    if isinstance(value, dict):
        return dict(value)
    return {"message": str(value)[:500]}


def _collect_leak_issues(value: object, *, path: str, issues: list[ValidationIssue]) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            nested_path = f"{path}.{key_text}"
            if FORBIDDEN_KEY_PATTERN.search(key_text):
                issues.append(
                    _issue(
                        "forbidden_key",
                        f"forbidden field '{key_text}' is not allowed in visual generation data",
                        field=nested_path,
                    )
                )
            _collect_leak_issues(nested, path=nested_path, issues=issues)
        return
    if isinstance(value, list | tuple):
        for index, nested in enumerate(value):
            _collect_leak_issues(nested, path=f"{path}[{index}]", issues=issues)
        return
    if isinstance(value, bytes | bytearray):
        issues.append(
            _issue("forbidden_binary", "binary data is not allowed", field=path),
        )
        return
    if isinstance(value, str) and PATH_LIKE_PATTERN.search(value.strip()):
        issues.append(
            _issue(
                "forbidden_path_value",
                "path-like values are not allowed in safe visual generation data",
                field=path,
            )
        )


def _collect_raw_workflow_issues(
    value: object,
    *,
    path: str,
    issues: list[ValidationIssue],
) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            nested_path = f"{path}.{key_text}"
            if key_text in RAW_WORKFLOW_KEYS:
                issues.append(
                    _issue(
                        "raw_workflow_payload_rejected",
                        "raw workflow payloads may not be supplied by runtime plan requests",
                        field=nested_path,
                    )
                )
            _collect_raw_workflow_issues(nested, path=nested_path, issues=issues)
        return
    if isinstance(value, list | tuple):
        for index, nested in enumerate(value):
            _collect_raw_workflow_issues(nested, path=f"{path}[{index}]", issues=issues)


def _schema_string_set(value: object) -> set[str]:
    if isinstance(value, Iterable) and not isinstance(value, str | bytes | dict):
        return {str(item).strip() for item in value if str(item).strip()}
    return set()


def _issue(
    code: str,
    message: str,
    *,
    field: str | None = None,
    severity: ValidationSeverity = ValidationSeverity.ERROR,
) -> ValidationIssue:
    return ValidationIssue(code=code, message=message, field=field, severity=severity)
