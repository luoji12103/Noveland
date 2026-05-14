from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from noveland.authoring.contracts import AuthoringProposalKind

LORE_PATTERN = re.compile(
    r"^\s*(?P<classification>lore|canon|inferred|uncertain)\s*:\s*(?P<text>.+?)\s*$",
    re.IGNORECASE,
)
LOCATION_PATTERN = re.compile(
    r"^\s*(?:location|place)\s*:\s*(?P<label>.+?)\s*$",
    re.IGNORECASE,
)
ORGANIZATION_PATTERN = re.compile(
    r"^\s*(?:organization|org)\s*:\s*(?P<label>.+?)\s*$",
    re.IGNORECASE,
)
WORLD_RULE_PATTERN = re.compile(
    r"^\s*(?:world\s+rule|rule)\s*:\s*(?P<text>.+?)\s*$",
    re.IGNORECASE,
)
SECRET_PATTERN = re.compile(
    r"^\s*(?:secret|spoiler)\s*:\s*(?P<text>.+?)\s*$",
    re.IGNORECASE,
)
KNOWLEDGE_BOUNDARY_PATTERN = re.compile(
    r"^\s*(?P<kind>knowledge|knows|hidden\s+from)\s*:\s*"
    r"(?P<actor>.+?)\s*(?:->|=>)\s*(?P<fact>.+?)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExtractedLoreCandidate:
    source_fragment_id: uuid.UUID
    proposal_kind: AuthoringProposalKind
    target_ref_kind: str
    title: str
    summary: str
    proposed_payload_json: dict[str, Any]
    evidence_json: dict[str, Any]
    confidence: float | None
    priority: int
    candidate_kind: str
    classification: str | None
    dedupe_key: tuple[str, ...]


def extract_fragment(
    *,
    source_fragment_id: uuid.UUID,
    excerpt_text: str | None,
    extractor_mode: str,
) -> list[ExtractedLoreCandidate]:
    if excerpt_text is None:
        return []
    if extractor_mode != "deterministic":
        raise ValueError("lore extractor mode is not supported")

    candidates: list[ExtractedLoreCandidate] = []
    for line_number, raw_line in enumerate(excerpt_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        lore_match = LORE_PATTERN.match(line)
        if lore_match is not None:
            classification = _normalize_key(lore_match.group("classification"))
            text = _normalize_text(lore_match.group("text"))
            candidates.append(
                _candidate(
                    source_fragment_id=source_fragment_id,
                    line_number=line_number,
                    candidate_kind="lore",
                    classification=classification,
                    target_ref_kind="lore_candidate",
                    title=f"Lore candidate: {classification}",
                    payload={"lore_text": text, "classification": classification},
                    confidence=_classification_confidence(classification),
                    extractor_mode=extractor_mode,
                )
            )
            continue

        location_match = LOCATION_PATTERN.match(line)
        if location_match is not None:
            label = _normalize_text(location_match.group("label"))
            candidates.append(
                _candidate(
                    source_fragment_id=source_fragment_id,
                    line_number=line_number,
                    candidate_kind="location",
                    classification="canon",
                    target_ref_kind="location_candidate",
                    title=f"Location candidate: {label}",
                    payload={"location_label": label, "location_key": _normalize_key(label)},
                    confidence=0.78,
                    extractor_mode=extractor_mode,
                )
            )
            continue

        organization_match = ORGANIZATION_PATTERN.match(line)
        if organization_match is not None:
            label = _normalize_text(organization_match.group("label"))
            candidates.append(
                _candidate(
                    source_fragment_id=source_fragment_id,
                    line_number=line_number,
                    candidate_kind="organization",
                    classification="canon",
                    target_ref_kind="organization_candidate",
                    title=f"Organization candidate: {label}",
                    payload={
                        "organization_label": label,
                        "organization_key": _normalize_key(label),
                    },
                    confidence=0.76,
                    extractor_mode=extractor_mode,
                )
            )
            continue

        world_rule_match = WORLD_RULE_PATTERN.match(line)
        if world_rule_match is not None:
            text = _normalize_text(world_rule_match.group("text"))
            candidates.append(
                _candidate(
                    source_fragment_id=source_fragment_id,
                    line_number=line_number,
                    candidate_kind="world_rule",
                    classification="canon",
                    target_ref_kind="world_rule_candidate",
                    title="World rule candidate",
                    payload={"world_rule_text": text, "classification": "canon"},
                    confidence=0.74,
                    extractor_mode=extractor_mode,
                )
            )
            continue

        secret_match = SECRET_PATTERN.match(line)
        if secret_match is not None:
            text = _normalize_text(secret_match.group("text"))
            candidates.append(
                _candidate(
                    source_fragment_id=source_fragment_id,
                    line_number=line_number,
                    candidate_kind="secret",
                    classification="secret",
                    target_ref_kind="secret_candidate",
                    title="Secret lore candidate",
                    payload={"secret_text": text, "classification": "secret"},
                    confidence=0.72,
                    extractor_mode=extractor_mode,
                )
            )
            continue

        knowledge_match = KNOWLEDGE_BOUNDARY_PATTERN.match(line)
        if knowledge_match is not None:
            kind = _normalize_key(knowledge_match.group("kind"))
            actor = _normalize_text(knowledge_match.group("actor"))
            fact = _normalize_text(knowledge_match.group("fact"))
            candidates.append(
                _candidate(
                    source_fragment_id=source_fragment_id,
                    line_number=line_number,
                    candidate_kind="knowledge_boundary",
                    classification="secret" if kind == "hidden_from" else "canon",
                    target_ref_kind="knowledge_boundary_candidate",
                    title=f"Knowledge boundary candidate: {actor}",
                    payload={
                        "boundary_kind": kind,
                        "actor_label": actor,
                        "fact_text": fact,
                    },
                    confidence=0.7,
                    extractor_mode=extractor_mode,
                )
            )
    return candidates


def dedupe_candidates(
    candidates: list[ExtractedLoreCandidate],
) -> list[ExtractedLoreCandidate]:
    seen: set[tuple[str, ...]] = set()
    deduped: list[ExtractedLoreCandidate] = []
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
    candidate_kind: str,
    classification: str,
    target_ref_kind: str,
    title: str,
    payload: dict[str, Any],
    confidence: float,
    extractor_mode: str,
) -> ExtractedLoreCandidate:
    base_payload = {
        "candidate_kind": candidate_kind,
        "source_fragment_id": str(source_fragment_id),
        "line_number": line_number,
        "extractor_mode": extractor_mode,
        **payload,
    }
    evidence = {
        "source_fragment_id": str(source_fragment_id),
        "line_number": line_number,
        "candidate_kind": candidate_kind,
        "classification": classification,
        "extractor_mode": extractor_mode,
    }
    return ExtractedLoreCandidate(
        source_fragment_id=source_fragment_id,
        proposal_kind=AuthoringProposalKind.LORE,
        target_ref_kind=target_ref_kind,
        title=title,
        summary=f"{title} extracted from line {line_number}.",
        proposed_payload_json=base_payload,
        evidence_json=evidence,
        confidence=confidence,
        priority=line_number,
        candidate_kind=candidate_kind,
        classification=classification,
        dedupe_key=(
            candidate_kind,
            classification,
            _normalize_key("|".join(str(value) for value in payload.values())),
        ),
    )


def _classification_confidence(classification: str) -> float:
    if classification == "canon":
        return 0.84
    if classification == "inferred":
        return 0.66
    if classification == "uncertain":
        return 0.45
    return 0.78


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _normalize_key(value: str) -> str:
    normalized = re.sub(r"\s+", "_", value.strip().lower())
    return re.sub(r"[^a-z0-9_.-]+", "_", normalized)
