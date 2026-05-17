from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from noveland.authoring.contracts import AuthoringProposalKind


@dataclass(frozen=True)
class AssetMatchInput:
    source_asset_id: uuid.UUID
    source_fragment_id: uuid.UUID | None
    media_asset_id: uuid.UUID
    source_asset_kind: str
    source_label: str
    source_metadata_json: dict[str, Any]
    fragment_kind: str | None
    fragment_metadata_json: dict[str, Any]
    media_asset_kind: str
    media_asset_role: str
    media_visibility: str
    priority: int


@dataclass(frozen=True)
class AssetMatchCandidate:
    source_fragment_id: uuid.UUID | None
    proposal_kind: AuthoringProposalKind
    target_ref_kind: str
    title: str
    summary: str
    proposed_payload_json: dict[str, Any]
    evidence_json: dict[str, Any]
    confidence: float | None
    priority: int
    match_kind: str
    dedupe_key: tuple[str, ...]


def match_asset(
    match_input: AssetMatchInput,
    *,
    matching_mode: str,
    include_visual_matches: bool,
    include_voice_matches: bool,
    include_cg_matches: bool,
) -> list[AssetMatchCandidate]:
    if matching_mode != "deterministic":
        raise ValueError("asset matching mode is not supported")

    hints = _merged_hints(
        match_input.source_metadata_json,
        match_input.fragment_metadata_json,
    )
    candidates: list[AssetMatchCandidate] = []
    if match_input.media_asset_kind == "image" and include_visual_matches:
        if _has_any(hints, ("character_label", "expression_key", "pose_key", "outfit_key")):
            candidates.append(
                _candidate(
                    match_input,
                    matching_mode=matching_mode,
                    match_kind="sprite",
                    target_ref_kind="sprite_asset_match",
                    title="Sprite asset match candidate",
                    confidence=0.78,
                    payload=_sprite_payload(hints),
                )
            )
        if _is_background_match(match_input.media_asset_role, hints):
            candidates.append(
                _candidate(
                    match_input,
                    matching_mode=matching_mode,
                    match_kind="background",
                    target_ref_kind="background_asset_match",
                    title="Background asset match candidate",
                    confidence=0.76,
                    payload=_background_payload(hints),
                )
            )
        if include_cg_matches and _is_cg_match(match_input.media_asset_role, hints):
            candidates.append(
                _candidate(
                    match_input,
                    matching_mode=matching_mode,
                    match_kind="cg",
                    target_ref_kind="cg_asset_match",
                    title="CG asset match candidate",
                    confidence=0.68,
                    payload=_cg_payload(match_input.source_label, hints),
                )
            )
    if match_input.media_asset_kind == "audio" and include_voice_matches:
        candidates.append(
            _candidate(
                match_input,
                matching_mode=matching_mode,
                match_kind="voice",
                target_ref_kind="voice_asset_match",
                title="Voice asset match candidate",
                confidence=0.72,
                payload=_voice_payload(match_input.source_label, hints),
            )
        )
    return candidates


def dedupe_candidates(candidates: list[AssetMatchCandidate]) -> list[AssetMatchCandidate]:
    seen: set[tuple[str, ...]] = set()
    deduped: list[AssetMatchCandidate] = []
    for candidate in candidates:
        if candidate.dedupe_key in seen:
            continue
        seen.add(candidate.dedupe_key)
        deduped.append(candidate)
    return deduped


def _candidate(
    match_input: AssetMatchInput,
    *,
    matching_mode: str,
    match_kind: str,
    target_ref_kind: str,
    title: str,
    confidence: float,
    payload: dict[str, Any],
) -> AssetMatchCandidate:
    base_payload = {
        "candidate_kind": "asset_match",
        "match_kind": match_kind,
        "source_asset_id": str(match_input.source_asset_id),
        "media_asset_id": str(match_input.media_asset_id),
        "matching_mode": matching_mode,
        **payload,
    }
    evidence = {
        "source_asset_id": str(match_input.source_asset_id),
        "media_asset_id": str(match_input.media_asset_id),
        "source_asset_kind": match_input.source_asset_kind,
        "media_asset_kind": match_input.media_asset_kind,
        "media_asset_role": match_input.media_asset_role,
        "matching_mode": matching_mode,
    }
    if match_input.source_fragment_id is not None:
        base_payload["source_fragment_id"] = str(match_input.source_fragment_id)
        evidence["source_fragment_id"] = str(match_input.source_fragment_id)
    return AssetMatchCandidate(
        source_fragment_id=match_input.source_fragment_id,
        proposal_kind=AuthoringProposalKind.ASSET_MATCH,
        target_ref_kind=target_ref_kind,
        title=title,
        summary=f"{match_kind} asset match requires review.",
        proposed_payload_json=base_payload,
        evidence_json=evidence,
        confidence=confidence,
        priority=match_input.priority,
        match_kind=match_kind,
        dedupe_key=(
            str(match_input.media_asset_id),
            str(match_input.source_asset_id),
            match_kind,
            _target_hint_key(base_payload),
        ),
    )


def _merged_hints(
    source_metadata_json: dict[str, Any],
    fragment_metadata_json: dict[str, Any],
) -> dict[str, str | list[str]]:
    merged: dict[str, str | list[str]] = {}
    for key in (
        "character_label",
        "expression_key",
        "pose_key",
        "outfit_key",
        "scene_id",
        "location_key",
        "time_of_day",
        "weather_key",
        "speaker_label",
        "voice_label",
        "emotion_key",
        "style_key",
        "cg_key",
        "route_key",
        "provider_id",
        "provider_voice_id",
        "voice_id",
        "language",
    ):
        value = fragment_metadata_json.get(key, source_metadata_json.get(key))
        if isinstance(value, str) and value.strip():
            merged[key] = _normalize_text(value)
    for list_key in ("mood_tags", "supported_languages"):
        value = fragment_metadata_json.get(list_key, source_metadata_json.get(list_key))
        if isinstance(value, list):
            tags = [
                _normalize_key(item) for item in value if isinstance(item, str) and item.strip()
            ]
            if tags:
                merged[list_key] = tags
    return merged


def _sprite_payload(hints: dict[str, str | list[str]]) -> dict[str, Any]:
    return _select_hints(
        hints,
        (
            "character_label",
            "expression_key",
            "pose_key",
            "outfit_key",
            "mood_tags",
        ),
    )


def _background_payload(hints: dict[str, str | list[str]]) -> dict[str, Any]:
    return _select_hints(
        hints,
        (
            "scene_id",
            "location_key",
            "time_of_day",
            "weather_key",
        ),
    )


def _cg_payload(source_label: str, hints: dict[str, str | list[str]]) -> dict[str, Any]:
    payload = _select_hints(hints, ("scene_id", "cg_key", "route_key"))
    if "cg_key" not in payload:
        payload["cg_key"] = _normalize_key(source_label)
    return payload


def _voice_payload(source_label: str, hints: dict[str, str | list[str]]) -> dict[str, Any]:
    payload = _select_hints(
        hints,
        (
            "speaker_label",
            "voice_label",
            "emotion_key",
            "style_key",
            "provider_id",
            "provider_voice_id",
            "voice_id",
            "language",
            "supported_languages",
        ),
    )
    if "voice_label" not in payload:
        payload["voice_label"] = _normalize_text(source_label)
    return payload


def _select_hints(
    hints: dict[str, str | list[str]],
    keys: tuple[str, ...],
) -> dict[str, Any]:
    return {key: hints[key] for key in keys if key in hints}


def _has_any(hints: dict[str, str | list[str]], keys: tuple[str, ...]) -> bool:
    return any(key in hints for key in keys)


def _is_background_match(
    media_asset_role: str,
    hints: dict[str, str | list[str]],
) -> bool:
    return media_asset_role == "scene_background" or _has_any(
        hints,
        ("scene_id", "location_key", "time_of_day", "weather_key"),
    )


def _is_cg_match(media_asset_role: str, hints: dict[str, str | list[str]]) -> bool:
    return media_asset_role == "event_cg" or _has_any(hints, ("cg_key", "route_key"))


def _target_hint_key(payload: dict[str, Any]) -> str:
    parts = []
    for key in (
        "character_label",
        "expression_key",
        "pose_key",
        "outfit_key",
        "scene_id",
        "location_key",
        "time_of_day",
        "weather_key",
        "speaker_label",
        "voice_label",
        "emotion_key",
        "style_key",
        "cg_key",
        "route_key",
        "provider_id",
        "provider_voice_id",
        "voice_id",
        "language",
        "supported_languages",
    ):
        value = payload.get(key)
        if isinstance(value, str):
            parts.append(f"{key}:{_normalize_key(value)}")
        elif isinstance(value, list):
            parts.append(f"{key}:{','.join(_normalize_key(item) for item in value)}")
    return "|".join(parts)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9_.-]+", "-", value.strip().lower()).strip("-")
