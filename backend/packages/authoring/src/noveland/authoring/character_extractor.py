from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from noveland.authoring.contracts import AuthoringProposalKind

CHARACTER_PATTERNS = (
    re.compile(r"^\s*character\s*:\s*(?P<name>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*name\s*:\s*(?P<name>.+?)\s*$", re.IGNORECASE),
)
ALIAS_PATTERN = re.compile(
    r"^\s*alias\s*:\s*(?P<name>.+?)\s*(?:->|=>|=)\s*(?P<alias>.+?)\s*$",
    re.IGNORECASE,
)
RELATIONSHIP_PATTERNS = (
    re.compile(
        r"^\s*relationship\s*:\s*(?P<source>.+?)\s*(?:->|=>)\s*"
        r"(?P<target>.+?)(?:\s*:\s*(?P<label>.+?))?\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?P<source>[A-Za-z][\w .'-]{0,80})\s*(?:->|=>)\s*"
        r"(?P<target>[A-Za-z][\w .'-]{0,80})\s*:\s*(?P<label>.+?)\s*$",
    ),
    re.compile(
        r"^\s*(?P<source>[A-Za-z][\w .'-]{0,80})\s+"
        r"(?P<label>loves|trusts|hates|fears|protects)\s+"
        r"(?P<target>[A-Za-z][\w .'-]{0,80})\s*$",
        re.IGNORECASE,
    ),
)
FACTION_PATTERN = re.compile(r"^\s*faction\s*:\s*(?P<name>.+?)\s*$", re.IGNORECASE)
IDENTITY_PATTERN = re.compile(
    r"^\s*(?:identity|role)\s*:\s*(?P<name>.+?)\s*=\s*(?P<value>.+?)\s*$",
    re.IGNORECASE,
)
EMOTIONAL_BASELINE_PATTERN = re.compile(
    r"^\s*(?:emotion|baseline)\s*:\s*(?P<name>.+?)\s*=\s*(?P<value>.+?)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExtractedCharacterCandidate:
    source_fragment_id: uuid.UUID | None
    proposal_kind: AuthoringProposalKind
    target_ref_kind: str
    title: str
    summary: str
    proposed_payload_json: dict[str, Any]
    evidence_json: dict[str, Any]
    confidence: float | None
    priority: int
    candidate_kind: str
    dedupe_key: tuple[str, ...]


def extract_fragment(
    *,
    source_fragment_id: uuid.UUID,
    excerpt_text: str | None,
    extractor_mode: str,
) -> list[ExtractedCharacterCandidate]:
    if excerpt_text is None:
        return []
    if extractor_mode != "deterministic":
        raise ValueError("character extractor mode is not supported")

    candidates: list[ExtractedCharacterCandidate] = []
    for line_number, raw_line in enumerate(excerpt_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        character_name = _match_value(CHARACTER_PATTERNS, line)
        if character_name is not None:
            candidates.append(
                _character_candidate(
                    source_fragment_id=source_fragment_id,
                    line_number=line_number,
                    name=character_name,
                    source_kind="fragment",
                    confidence=0.86,
                    priority=line_number,
                    extractor_mode=extractor_mode,
                )
            )
            continue

        alias_match = ALIAS_PATTERN.match(line)
        if alias_match is not None:
            name = _normalize_label(alias_match.group("name"))
            alias = _normalize_label(alias_match.group("alias"))
            candidates.append(
                ExtractedCharacterCandidate(
                    source_fragment_id=source_fragment_id,
                    proposal_kind=AuthoringProposalKind.CHARACTER,
                    target_ref_kind="character_alias_candidate",
                    title=f"Alias candidate: {name} -> {alias}",
                    summary=f"Alias candidate extracted from line {line_number}.",
                    proposed_payload_json={
                        "candidate_kind": "alias",
                        "character_label": name,
                        "alias_label": alias,
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "extractor_mode": extractor_mode,
                    },
                    evidence_json={
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "candidate_kind": "alias",
                        "extractor_mode": extractor_mode,
                    },
                    confidence=0.82,
                    priority=line_number,
                    candidate_kind="alias",
                    dedupe_key=("alias", _normalize_key(name), _normalize_key(alias)),
                )
            )
            continue

        relationship = _match_relationship(line)
        if relationship is not None:
            source, target, label = relationship
            candidates.append(
                ExtractedCharacterCandidate(
                    source_fragment_id=source_fragment_id,
                    proposal_kind=AuthoringProposalKind.RELATIONSHIP,
                    target_ref_kind="relationship_candidate",
                    title=f"Relationship candidate: {source} -> {target}",
                    summary=f"Relationship candidate extracted from line {line_number}.",
                    proposed_payload_json={
                        "candidate_kind": "relationship",
                        "source_character_label": source,
                        "target_character_label": target,
                        "relationship_label": label,
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "extractor_mode": extractor_mode,
                    },
                    evidence_json={
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "candidate_kind": "relationship",
                        "extractor_mode": extractor_mode,
                    },
                    confidence=0.78,
                    priority=line_number,
                    candidate_kind="relationship",
                    dedupe_key=(
                        "relationship",
                        _normalize_key(source),
                        _normalize_key(target),
                        _normalize_key(label),
                    ),
                )
            )
            continue

        faction_name = _match_value((FACTION_PATTERN,), line)
        if faction_name is not None:
            normalized = _normalize_label(faction_name)
            candidates.append(
                ExtractedCharacterCandidate(
                    source_fragment_id=source_fragment_id,
                    proposal_kind=AuthoringProposalKind.CHARACTER,
                    target_ref_kind="faction_candidate",
                    title=f"Faction candidate: {normalized}",
                    summary=f"Faction candidate extracted from line {line_number}.",
                    proposed_payload_json={
                        "candidate_kind": "faction",
                        "faction_label": normalized,
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "extractor_mode": extractor_mode,
                    },
                    evidence_json={
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "candidate_kind": "faction",
                        "extractor_mode": extractor_mode,
                    },
                    confidence=0.76,
                    priority=line_number,
                    candidate_kind="faction",
                    dedupe_key=("faction", _normalize_key(normalized)),
                )
            )
            continue

        identity_match = IDENTITY_PATTERN.match(line)
        if identity_match is not None:
            name = _normalize_label(identity_match.group("name"))
            value = _normalize_label(identity_match.group("value"))
            candidates.append(
                ExtractedCharacterCandidate(
                    source_fragment_id=source_fragment_id,
                    proposal_kind=AuthoringProposalKind.CHARACTER,
                    target_ref_kind="identity_candidate",
                    title=f"Identity candidate: {name}",
                    summary=f"Identity candidate extracted from line {line_number}.",
                    proposed_payload_json={
                        "candidate_kind": "identity",
                        "character_label": name,
                        "identity_value": value,
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "extractor_mode": extractor_mode,
                    },
                    evidence_json={
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "candidate_kind": "identity",
                        "extractor_mode": extractor_mode,
                    },
                    confidence=0.74,
                    priority=line_number,
                    candidate_kind="identity",
                    dedupe_key=("identity", _normalize_key(name), _normalize_key(value)),
                )
            )
            continue

        baseline_match = EMOTIONAL_BASELINE_PATTERN.match(line)
        if baseline_match is not None:
            name = _normalize_label(baseline_match.group("name"))
            value = _normalize_label(baseline_match.group("value"))
            candidates.append(
                ExtractedCharacterCandidate(
                    source_fragment_id=source_fragment_id,
                    proposal_kind=AuthoringProposalKind.CHARACTER,
                    target_ref_kind="emotional_baseline_candidate",
                    title=f"Emotional baseline candidate: {name}",
                    summary=f"Emotional baseline candidate extracted from line {line_number}.",
                    proposed_payload_json={
                        "candidate_kind": "emotional_baseline",
                        "character_label": name,
                        "emotional_baseline": value,
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "extractor_mode": extractor_mode,
                    },
                    evidence_json={
                        "source_fragment_id": str(source_fragment_id),
                        "line_number": line_number,
                        "candidate_kind": "emotional_baseline",
                        "extractor_mode": extractor_mode,
                    },
                    confidence=0.72,
                    priority=line_number,
                    candidate_kind="emotional_baseline",
                    dedupe_key=(
                        "emotional_baseline",
                        _normalize_key(name),
                        _normalize_key(value),
                    ),
                )
            )
    return candidates


def extract_dialogue_speaker_candidate(
    *,
    source_fragment_id: uuid.UUID | None,
    speaker_label: str,
    extractor_mode: str,
    priority: int,
) -> ExtractedCharacterCandidate:
    if extractor_mode != "deterministic":
        raise ValueError("character extractor mode is not supported")
    return _character_candidate(
        source_fragment_id=source_fragment_id,
        line_number=None,
        name=speaker_label,
        source_kind="dialogue_proposal",
        confidence=0.7,
        priority=priority,
        extractor_mode=extractor_mode,
    )


def dedupe_candidates(
    candidates: list[ExtractedCharacterCandidate],
) -> list[ExtractedCharacterCandidate]:
    seen: set[tuple[str, ...]] = set()
    deduped: list[ExtractedCharacterCandidate] = []
    for candidate in candidates:
        if candidate.dedupe_key in seen:
            continue
        seen.add(candidate.dedupe_key)
        deduped.append(candidate)
    return deduped


def _character_candidate(
    *,
    source_fragment_id: uuid.UUID | None,
    line_number: int | None,
    name: str,
    source_kind: str,
    confidence: float,
    priority: int,
    extractor_mode: str,
) -> ExtractedCharacterCandidate:
    normalized = _normalize_label(name)
    payload: dict[str, Any] = {
        "candidate_kind": "character",
        "character_label": normalized,
        "source_kind": source_kind,
        "extractor_mode": extractor_mode,
    }
    evidence: dict[str, Any] = {
        "candidate_kind": "character",
        "source_kind": source_kind,
        "extractor_mode": extractor_mode,
    }
    if source_fragment_id is not None:
        payload["source_fragment_id"] = str(source_fragment_id)
        evidence["source_fragment_id"] = str(source_fragment_id)
    if line_number is not None:
        payload["line_number"] = line_number
        evidence["line_number"] = line_number
    return ExtractedCharacterCandidate(
        source_fragment_id=source_fragment_id,
        proposal_kind=AuthoringProposalKind.CHARACTER,
        target_ref_kind="character_candidate",
        title=f"Character candidate: {normalized}",
        summary="Character candidate extracted from authoring source.",
        proposed_payload_json=payload,
        evidence_json=evidence,
        confidence=confidence,
        priority=priority,
        candidate_kind="character",
        dedupe_key=("character", _normalize_key(normalized)),
    )


def _match_value(patterns: tuple[re.Pattern[str], ...], line: str) -> str | None:
    for pattern in patterns:
        match = pattern.match(line)
        if match is not None:
            for value in match.groupdict().values():
                if value is not None:
                    return value
    return None


def _match_relationship(line: str) -> tuple[str, str, str] | None:
    for pattern in RELATIONSHIP_PATTERNS:
        match = pattern.match(line)
        if match is None:
            continue
        source = _normalize_label(match.group("source"))
        target = _normalize_label(match.group("target"))
        label = _normalize_label(match.groupdict().get("label") or "related")
        return source, target, label
    return None


def _normalize_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", "_", value.strip().lower())
