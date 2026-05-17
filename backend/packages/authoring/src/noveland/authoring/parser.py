from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from noveland.authoring.contracts import AuthoringProposalKind

SCENE_PATTERNS = (
    re.compile(r"^\s*\[\s*scene\s*:\s*(?P<key>[^\]]+)\]\s*$", re.IGNORECASE),
    re.compile(r"^\s*#\s*scene\s+(?P<key>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*@\s*scene\s+(?P<key>.+?)\s*$", re.IGNORECASE),
)
CHOICE_PATTERNS = (
    re.compile(r"^\s*choice\s*:\s*(?P<label>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*->\s*(?P<label>.+?)\s*$"),
)
ROUTE_PATTERNS = (
    re.compile(r"^\s*\[\s*route\s*:\s*(?P<key>[^\]]+)\]\s*$", re.IGNORECASE),
    re.compile(r"^\s*@\s*route\s+(?P<key>.+?)\s*$", re.IGNORECASE),
)
EVENT_PATTERNS = (
    re.compile(r"^\s*\[\s*event\s*:\s*(?P<key>[^\]]+)\]\s*$", re.IGNORECASE),
    re.compile(r"^\s*@\s*event\s+(?P<key>.+?)\s*$", re.IGNORECASE),
)
EMOTION_PATTERNS = (
    re.compile(r"^\s*\[\s*emotion\s*:\s*(?P<value>[^\]]+)\]\s*$", re.IGNORECASE),
    re.compile(r"^\s*@\s*emotion\s+(?P<value>.+?)\s*$", re.IGNORECASE),
)
RELATIONSHIP_HINT_PATTERNS = (
    re.compile(
        r"^\s*\[\s*relationship\s*:\s*(?P<value>[^\]]+)\]\s*$",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*@\s*relationship\s+(?P<value>.+?)\s*$", re.IGNORECASE),
)
SPEAKER_PATTERN = re.compile(r"^\s*(?P<speaker>[^:：\[]+?)\s*[:：]\s*(?P<text>.+?)\s*$")
QUOTED_PATTERN = re.compile(r'^\s*(?:"(?P<dq>.+)"|「(?P<jp>.+)」|“(?P<ldq>.+)”)\s*$')


@dataclass(frozen=True)
class ParsedScriptCandidate:
    source_fragment_id: uuid.UUID
    proposal_kind: AuthoringProposalKind
    target_ref_kind: str
    title: str
    summary: str
    proposed_payload_json: dict[str, Any]
    evidence_json: dict[str, Any]
    confidence: float | None
    priority: int
    unresolved_speaker: bool = False
    candidate_kind: str = "other"


def parse_fragment(
    *,
    source_fragment_id: uuid.UUID,
    excerpt_text: str | None,
    parser_mode: str,
) -> list[ParsedScriptCandidate]:
    if excerpt_text is None:
        return []
    if parser_mode != "deterministic":
        raise ValueError("parser mode is not supported")

    candidates: list[ParsedScriptCandidate] = []
    for line_number, raw_line in enumerate(excerpt_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        scene_key = _match_value(SCENE_PATTERNS, line)
        if scene_key is not None:
            normalized = _normalize_key(scene_key)
            candidates.append(
                ParsedScriptCandidate(
                    source_fragment_id=source_fragment_id,
                    proposal_kind=AuthoringProposalKind.OTHER,
                    target_ref_kind="scene_candidate",
                    title=f"Scene candidate: {normalized}",
                    summary=f"Scene candidate extracted from line {line_number}.",
                    proposed_payload_json={
                        "candidate_kind": "scene",
                        "scene_key": normalized,
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "parser_mode": parser_mode,
                    },
                    evidence_json={
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "candidate_kind": "scene",
                        "parser_mode": parser_mode,
                    },
                    confidence=0.84,
                    priority=line_number,
                    candidate_kind="scene",
                )
            )
            continue

        choice_label = _match_value(CHOICE_PATTERNS, line)
        if choice_label is not None:
            normalized = _normalize_key(choice_label)
            candidates.append(
                ParsedScriptCandidate(
                    source_fragment_id=source_fragment_id,
                    proposal_kind=AuthoringProposalKind.OTHER,
                    target_ref_kind="choice_candidate",
                    title=f"Choice candidate: {normalized}",
                    summary=f"Choice candidate extracted from line {line_number}.",
                    proposed_payload_json={
                        "candidate_kind": "choice",
                        "choice_label": normalized,
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "parser_mode": parser_mode,
                    },
                    evidence_json={
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "candidate_kind": "choice",
                        "parser_mode": parser_mode,
                    },
                    confidence=0.8,
                    priority=line_number,
                    candidate_kind="choice",
                )
            )
            continue

        route_key = _match_value(ROUTE_PATTERNS, line)
        if route_key is not None:
            normalized = _normalize_key(route_key)
            candidates.append(
                ParsedScriptCandidate(
                    source_fragment_id=source_fragment_id,
                    proposal_kind=AuthoringProposalKind.OTHER,
                    target_ref_kind="route_candidate",
                    title=f"Route candidate: {normalized}",
                    summary=f"Route candidate extracted from line {line_number}.",
                    proposed_payload_json={
                        "candidate_kind": "route",
                        "route_key": normalized,
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "parser_mode": parser_mode,
                    },
                    evidence_json={
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "candidate_kind": "route",
                        "parser_mode": parser_mode,
                    },
                    confidence=0.77,
                    priority=line_number,
                    candidate_kind="route",
                )
            )
            continue

        event_key = _match_value(EVENT_PATTERNS, line)
        if event_key is not None:
            normalized = _normalize_key(event_key)
            candidates.append(
                ParsedScriptCandidate(
                    source_fragment_id=source_fragment_id,
                    proposal_kind=AuthoringProposalKind.OTHER,
                    target_ref_kind="event_candidate",
                    title=f"Event candidate: {normalized}",
                    summary=f"Event candidate extracted from line {line_number}.",
                    proposed_payload_json={
                        "candidate_kind": "event",
                        "event_key": normalized,
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "parser_mode": parser_mode,
                    },
                    evidence_json={
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "candidate_kind": "event",
                        "parser_mode": parser_mode,
                    },
                    confidence=0.76,
                    priority=line_number,
                    candidate_kind="event",
                )
            )
            continue

        emotion_value = _match_value(EMOTION_PATTERNS, line)
        if emotion_value is not None:
            normalized = _normalize_key(emotion_value)
            candidates.append(
                ParsedScriptCandidate(
                    source_fragment_id=source_fragment_id,
                    proposal_kind=AuthoringProposalKind.OTHER,
                    target_ref_kind="emotion_hint_candidate",
                    title=f"Emotion hint: {normalized}",
                    summary=f"Emotion hint extracted from line {line_number}.",
                    proposed_payload_json={
                        "candidate_kind": "emotion_hint",
                        "emotion_key": normalized,
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "parser_mode": parser_mode,
                    },
                    evidence_json={
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "candidate_kind": "emotion_hint",
                        "parser_mode": parser_mode,
                    },
                    confidence=0.72,
                    priority=line_number,
                    candidate_kind="emotion_hint",
                )
            )
            continue

        relationship_value = _match_value(RELATIONSHIP_HINT_PATTERNS, line)
        if relationship_value is not None:
            normalized = _normalize_label(relationship_value)
            candidates.append(
                ParsedScriptCandidate(
                    source_fragment_id=source_fragment_id,
                    proposal_kind=AuthoringProposalKind.RELATIONSHIP,
                    target_ref_kind="relationship_hint_candidate",
                    title=f"Relationship hint: {normalized}",
                    summary=f"Relationship hint extracted from line {line_number}.",
                    proposed_payload_json={
                        "candidate_kind": "relationship_hint",
                        "relationship_hint": normalized,
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "parser_mode": parser_mode,
                    },
                    evidence_json={
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "candidate_kind": "relationship_hint",
                        "parser_mode": parser_mode,
                    },
                    confidence=0.68,
                    priority=line_number,
                    candidate_kind="relationship_hint",
                )
            )
            continue

        speaker_match = SPEAKER_PATTERN.match(line)
        if speaker_match is not None:
            speaker = _normalize_key(speaker_match.group("speaker"))
            dialogue_text = speaker_match.group("text").strip()
            candidates.append(
                ParsedScriptCandidate(
                    source_fragment_id=source_fragment_id,
                    proposal_kind=AuthoringProposalKind.DIALOGUE,
                    target_ref_kind="dialogue_candidate",
                    title=f"Dialogue candidate: {speaker}",
                    summary=f"Dialogue candidate extracted from line {line_number}.",
                    proposed_payload_json={
                        "candidate_kind": "dialogue",
                        "speaker_label": speaker,
                        "line_text": dialogue_text,
                        "speaker_resolution": {"status": "resolved"},
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "parser_mode": parser_mode,
                    },
                    evidence_json={
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "candidate_kind": "dialogue",
                        "line_excerpt": _excerpt(dialogue_text),
                        "speaker_resolution": {"status": "resolved"},
                        "parser_mode": parser_mode,
                    },
                    confidence=0.93,
                    priority=line_number,
                    candidate_kind="dialogue",
                )
            )
            continue

        quoted_match = QUOTED_PATTERN.match(line)
        if quoted_match is not None:
            dialogue_text = _quoted_text(quoted_match)
            candidates.append(
                ParsedScriptCandidate(
                    source_fragment_id=source_fragment_id,
                    proposal_kind=AuthoringProposalKind.DIALOGUE,
                    target_ref_kind="dialogue_candidate",
                    title="Dialogue candidate: unresolved speaker",
                    summary=f"Unresolved speaker dialogue candidate from line {line_number}.",
                    proposed_payload_json={
                        "candidate_kind": "dialogue",
                        "line_text": dialogue_text,
                        "speaker_resolution": {
                            "status": "unresolved",
                            "reason": "missing_speaker",
                        },
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "parser_mode": parser_mode,
                    },
                    evidence_json={
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "candidate_kind": "dialogue",
                        "line_excerpt": _excerpt(dialogue_text),
                        "speaker_resolution": {
                            "status": "unresolved",
                            "reason": "missing_speaker",
                        },
                        "parser_mode": parser_mode,
                    },
                    confidence=0.55,
                    priority=line_number,
                    unresolved_speaker=True,
                    candidate_kind="dialogue",
                )
            )
            continue

        if _should_create_manual_label_candidate(line):
            candidates.append(
                ParsedScriptCandidate(
                    source_fragment_id=source_fragment_id,
                    proposal_kind=AuthoringProposalKind.OTHER,
                    target_ref_kind="manual_label_candidate",
                    title="Manual label required",
                    summary=f"Unrecognized script line from line {line_number}.",
                    proposed_payload_json={
                        "candidate_kind": "manual_label",
                        "label_status": "needs_review",
                        "reason": "unrecognized_script_line",
                        "line_excerpt": _excerpt(line),
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "parser_mode": parser_mode,
                    },
                    evidence_json={
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "candidate_kind": "manual_label",
                        "reason": "unrecognized_script_line",
                        "parser_mode": parser_mode,
                    },
                    confidence=0.25,
                    priority=line_number,
                    unresolved_speaker=True,
                    candidate_kind="manual_label",
                )
            )
    return candidates


def _match_value(patterns: tuple[re.Pattern[str], ...], line: str) -> str | None:
    for pattern in patterns:
        match = pattern.match(line)
        if match is not None:
            for value in match.groupdict().values():
                if value is not None:
                    return value
    return None


def _normalize_key(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"\s+", "_", normalized)
    return normalized


def _normalize_label(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip())
    return normalized


def _quoted_text(match: re.Match[str]) -> str:
    for value in match.groupdict().values():
        if value is not None:
            return value.strip()
    return ""


def _excerpt(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip())
    return normalized[:240]


def _should_create_manual_label_candidate(line: str) -> bool:
    if len(line) < 3:
        return False
    if line.startswith(("//", ";")):
        return False
    return True
