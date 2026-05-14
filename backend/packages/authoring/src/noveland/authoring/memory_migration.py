from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from noveland.authoring.contracts import AuthoringProposalKind

FACT_PATTERN = re.compile(r"^\s*fact\s*:\s*(?P<text>.+?)\s*$", re.IGNORECASE)
EPISODIC_PATTERN = re.compile(
    r"^\s*(?:episode|episodic)\s*:\s*(?P<text>.+?)\s*$",
    re.IGNORECASE,
)
RELATIONSHIP_MEMORY_PATTERN = re.compile(
    r"^\s*relationship\s+memory\s*:\s*(?P<source>.+?)\s*(?:->|=>)\s*"
    r"(?P<target>.+?)\s*:\s*(?P<text>.+?)\s*$",
    re.IGNORECASE,
)
PREFERENCE_PATTERN = re.compile(
    r"^\s*preference\s*:\s*(?P<actor>.+?)\s*=\s*(?P<value>.+?)\s*$",
    re.IGNORECASE,
)
LIKES_PATTERN = re.compile(
    r"^\s*(?P<actor>[A-Za-z][\w .'-]{0,80})\s+"
    r"(?P<polarity>likes|dislikes)\s+(?P<value>.+?)\s*$",
    re.IGNORECASE,
)
STYLE_PATTERN = re.compile(
    r"^\s*style\s*:\s*(?P<actor>.+?)\s*=\s*(?P<value>.+?)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MemoryMigrationCandidate:
    source_fragment_id: uuid.UUID | None
    proposal_kind: AuthoringProposalKind
    target_ref_kind: str
    title: str
    summary: str
    proposed_payload_json: dict[str, Any]
    evidence_json: dict[str, Any]
    confidence: float | None
    priority: int
    memory_kind: str
    dedupe_key: tuple[str, ...]


def migrate_fragment(
    *,
    source_fragment_id: uuid.UUID,
    excerpt_text: str | None,
    migration_mode: str,
) -> list[MemoryMigrationCandidate]:
    if excerpt_text is None:
        return []
    if migration_mode != "deterministic":
        raise ValueError("memory migration mode is not supported")

    candidates: list[MemoryMigrationCandidate] = []
    for line_number, raw_line in enumerate(excerpt_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        fact_match = FACT_PATTERN.match(line)
        if fact_match is not None:
            candidates.append(
                _candidate(
                    source_fragment_id=source_fragment_id,
                    line_number=line_number,
                    memory_kind="fact",
                    title="Fact memory candidate",
                    payload={"memory_text": _normalize_text(fact_match.group("text"))},
                    confidence=0.78,
                    migration_mode=migration_mode,
                )
            )
            continue

        episodic_match = EPISODIC_PATTERN.match(line)
        if episodic_match is not None:
            candidates.append(
                _candidate(
                    source_fragment_id=source_fragment_id,
                    line_number=line_number,
                    memory_kind="episodic",
                    title="Episodic memory candidate",
                    payload={"memory_text": _normalize_text(episodic_match.group("text"))},
                    confidence=0.74,
                    migration_mode=migration_mode,
                )
            )
            continue

        relationship_match = RELATIONSHIP_MEMORY_PATTERN.match(line)
        if relationship_match is not None:
            candidates.append(
                _candidate(
                    source_fragment_id=source_fragment_id,
                    line_number=line_number,
                    memory_kind="relationship",
                    title="Relationship memory candidate",
                    payload={
                        "source_character_label": _normalize_text(
                            relationship_match.group("source")
                        ),
                        "target_character_label": _normalize_text(
                            relationship_match.group("target")
                        ),
                        "memory_text": _normalize_text(relationship_match.group("text")),
                    },
                    confidence=0.76,
                    migration_mode=migration_mode,
                )
            )
            continue

        preference_match = PREFERENCE_PATTERN.match(line)
        if preference_match is not None:
            candidates.append(
                _candidate(
                    source_fragment_id=source_fragment_id,
                    line_number=line_number,
                    memory_kind="preference",
                    title="Preference memory candidate",
                    payload={
                        "actor_label": _normalize_text(preference_match.group("actor")),
                        "preference_value": _normalize_text(preference_match.group("value")),
                    },
                    confidence=0.72,
                    migration_mode=migration_mode,
                )
            )
            continue

        likes_match = LIKES_PATTERN.match(line)
        if likes_match is not None:
            candidates.append(
                _candidate(
                    source_fragment_id=source_fragment_id,
                    line_number=line_number,
                    memory_kind="preference",
                    title="Preference memory candidate",
                    payload={
                        "actor_label": _normalize_text(likes_match.group("actor")),
                        "preference_polarity": _normalize_key(
                            likes_match.group("polarity")
                        ),
                        "preference_value": _normalize_text(likes_match.group("value")),
                    },
                    confidence=0.68,
                    migration_mode=migration_mode,
                )
            )
            continue

        style_match = STYLE_PATTERN.match(line)
        if style_match is not None:
            candidates.append(
                _candidate(
                    source_fragment_id=source_fragment_id,
                    line_number=line_number,
                    memory_kind="style",
                    title="Style memory candidate",
                    payload={
                        "actor_label": _normalize_text(style_match.group("actor")),
                        "style_value": _normalize_text(style_match.group("value")),
                    },
                    confidence=0.7,
                    migration_mode=migration_mode,
                )
            )
    return candidates


def migrate_proposal(
    *,
    source_fragment_id: uuid.UUID | None,
    target_ref_kind: str | None,
    proposed_payload_json: dict[str, Any],
    migration_mode: str,
    priority: int,
) -> MemoryMigrationCandidate | None:
    if migration_mode != "deterministic":
        raise ValueError("memory migration mode is not supported")
    candidate_kind = proposed_payload_json.get("candidate_kind")
    if candidate_kind == "lore" and isinstance(proposed_payload_json.get("lore_text"), str):
        return _proposal_candidate(
            source_fragment_id=source_fragment_id,
            memory_kind="fact",
            title="Fact memory candidate",
            payload={"memory_text": proposed_payload_json["lore_text"]},
            migration_mode=migration_mode,
            priority=priority,
        )
    if candidate_kind == "relationship":
        source = proposed_payload_json.get("source_character_label")
        target = proposed_payload_json.get("target_character_label")
        label = proposed_payload_json.get("relationship_label")
        if isinstance(source, str) and isinstance(target, str):
            return _proposal_candidate(
                source_fragment_id=source_fragment_id,
                memory_kind="relationship",
                title="Relationship memory candidate",
                payload={
                    "source_character_label": source,
                    "target_character_label": target,
                    "memory_text": label if isinstance(label, str) else "related",
                },
                migration_mode=migration_mode,
                priority=priority,
            )
    if target_ref_kind == "dialogue_candidate":
        speaker = proposed_payload_json.get("speaker_label")
        if isinstance(speaker, str) and speaker.strip():
            return _proposal_candidate(
                source_fragment_id=source_fragment_id,
                memory_kind="style",
                title="Style memory candidate",
                payload={
                    "actor_label": speaker,
                    "style_value": "dialogue_speaker_observed",
                },
                migration_mode=migration_mode,
                priority=priority,
            )
    return None


def dedupe_candidates(
    candidates: list[MemoryMigrationCandidate],
) -> list[MemoryMigrationCandidate]:
    seen: set[tuple[str, ...]] = set()
    deduped: list[MemoryMigrationCandidate] = []
    for candidate in candidates:
        if candidate.dedupe_key in seen:
            continue
        seen.add(candidate.dedupe_key)
        deduped.append(candidate)
    return deduped


def _candidate(
    *,
    source_fragment_id: uuid.UUID,
    line_number: int,
    memory_kind: str,
    title: str,
    payload: dict[str, Any],
    confidence: float,
    migration_mode: str,
) -> MemoryMigrationCandidate:
    base_payload = {
        "candidate_kind": "memory",
        "memory_kind": memory_kind,
        "source_fragment_id": str(source_fragment_id),
        "line_number": line_number,
        "migration_mode": migration_mode,
        **payload,
    }
    return _build_candidate(
        source_fragment_id=source_fragment_id,
        memory_kind=memory_kind,
        title=title,
        payload=base_payload,
        evidence={
            "source_fragment_id": str(source_fragment_id),
            "line_number": line_number,
            "memory_kind": memory_kind,
            "migration_mode": migration_mode,
        },
        confidence=confidence,
        priority=line_number,
    )


def _proposal_candidate(
    *,
    source_fragment_id: uuid.UUID | None,
    memory_kind: str,
    title: str,
    payload: dict[str, Any],
    migration_mode: str,
    priority: int,
) -> MemoryMigrationCandidate:
    base_payload = {
        "candidate_kind": "memory",
        "memory_kind": memory_kind,
        "source_kind": "authoring_proposal",
        "migration_mode": migration_mode,
        **payload,
    }
    evidence: dict[str, Any] = {
        "memory_kind": memory_kind,
        "source_kind": "authoring_proposal",
        "migration_mode": migration_mode,
    }
    if source_fragment_id is not None:
        base_payload["source_fragment_id"] = str(source_fragment_id)
        evidence["source_fragment_id"] = str(source_fragment_id)
    return _build_candidate(
        source_fragment_id=source_fragment_id,
        memory_kind=memory_kind,
        title=title,
        payload=base_payload,
        evidence=evidence,
        confidence=0.62,
        priority=priority,
    )


def _build_candidate(
    *,
    source_fragment_id: uuid.UUID | None,
    memory_kind: str,
    title: str,
    payload: dict[str, Any],
    evidence: dict[str, Any],
    confidence: float,
    priority: int,
) -> MemoryMigrationCandidate:
    return MemoryMigrationCandidate(
        source_fragment_id=source_fragment_id,
        proposal_kind=AuthoringProposalKind.MEMORY,
        target_ref_kind="memory_candidate",
        title=title,
        summary=f"{memory_kind.replace('_', ' ')} memory candidate requires review.",
        proposed_payload_json=payload,
        evidence_json=evidence,
        confidence=confidence,
        priority=priority,
        memory_kind=memory_kind,
        dedupe_key=(
            memory_kind,
            _normalize_key("|".join(str(value) for value in payload.values())),
        ),
    )


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", "_", value.strip().lower())
