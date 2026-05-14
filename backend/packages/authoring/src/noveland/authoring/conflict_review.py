from __future__ import annotations

import hashlib
import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from noveland.authoring.contracts import AuthoringProposalKind


@dataclass(frozen=True)
class ConflictReviewProposal:
    id: uuid.UUID
    source_fragment_id: uuid.UUID | None
    target_ref_kind: str | None
    proposed_payload_json: dict[str, Any]
    evidence_json: dict[str, Any]


@dataclass(frozen=True)
class ConflictReportCandidate:
    source_fragment_id: uuid.UUID | None
    proposal_kind: AuthoringProposalKind
    target_ref_kind: str
    title: str
    summary: str
    proposed_payload_json: dict[str, Any]
    evidence_json: dict[str, Any]
    confidence: float | None
    priority: int
    conflict_kind: str
    dedupe_key: tuple[str, ...]


def review_proposals(
    proposals: list[ConflictReviewProposal],
    *,
    review_mode: str,
) -> list[ConflictReportCandidate]:
    if review_mode != "deterministic":
        raise ValueError("conflict review mode is not supported")

    candidates: list[ConflictReportCandidate] = []
    candidates.extend(_duplicate_reports(proposals, review_mode=review_mode))
    candidates.extend(_relationship_contradictions(proposals, review_mode=review_mode))
    candidates.extend(_value_contradictions(proposals, review_mode=review_mode))
    candidates.extend(_risk_reports(proposals, review_mode=review_mode))
    return _dedupe_reports(candidates)


def _duplicate_reports(
    proposals: list[ConflictReviewProposal],
    *,
    review_mode: str,
) -> list[ConflictReportCandidate]:
    groups: dict[tuple[str, str], list[ConflictReviewProposal]] = defaultdict(list)
    for proposal in proposals:
        payload = proposal.proposed_payload_json
        candidate_kind = payload.get("candidate_kind")
        key: str | None = None
        if candidate_kind == "character":
            key = _normalize_key(payload.get("character_label"))
        elif candidate_kind == "location":
            key = _normalize_key(payload.get("location_key") or payload.get("location_label"))
        elif candidate_kind == "organization":
            key = _normalize_key(
                payload.get("organization_key") or payload.get("organization_label")
            )
        elif candidate_kind == "lore":
            key = _fingerprint(
                f"{payload.get('classification', '')}|{payload.get('lore_text', '')}"
            )
        if key:
            groups[(str(candidate_kind), key)].append(proposal)

    reports: list[ConflictReportCandidate] = []
    for (candidate_kind, key), group in groups.items():
        if len(group) < 2:
            continue
        reports.append(
            _report(
                conflict_kind="duplicate",
                conflict_key=f"{candidate_kind}:{key}",
                title=f"Duplicate {candidate_kind} candidate",
                summary=f"Duplicate {candidate_kind} candidates require review.",
                involved=group,
                review_mode=review_mode,
                extra_payload={"candidate_kind": candidate_kind, "fingerprint": key},
                confidence=0.82,
                priority=20,
            )
        )
    return reports


def _relationship_contradictions(
    proposals: list[ConflictReviewProposal],
    *,
    review_mode: str,
) -> list[ConflictReportCandidate]:
    groups: dict[tuple[str, str], list[ConflictReviewProposal]] = defaultdict(list)
    for proposal in proposals:
        payload = proposal.proposed_payload_json
        if payload.get("candidate_kind") != "relationship":
            continue
        source = _normalize_key(payload.get("source_character_label"))
        target = _normalize_key(payload.get("target_character_label"))
        if source and target:
            groups[(source, target)].append(proposal)

    reports: list[ConflictReportCandidate] = []
    for (source, target), group in groups.items():
        labels = {
            _normalize_key(proposal.proposed_payload_json.get("relationship_label"))
            for proposal in group
        }
        labels.discard("")
        if len(labels) < 2:
            continue
        reports.append(
            _report(
                conflict_kind="contradiction",
                conflict_key=f"relationship:{source}:{target}",
                title="Relationship contradiction",
                summary="Relationship candidates disagree on the relationship label.",
                involved=group,
                review_mode=review_mode,
                extra_payload={
                    "candidate_kind": "relationship",
                    "source_character_key": source,
                    "target_character_key": target,
                    "relationship_label_keys": sorted(labels),
                },
                confidence=0.78,
                priority=30,
            )
        )
    return reports


def _value_contradictions(
    proposals: list[ConflictReviewProposal],
    *,
    review_mode: str,
) -> list[ConflictReportCandidate]:
    groups: dict[tuple[str, str], list[ConflictReviewProposal]] = defaultdict(list)
    for proposal in proposals:
        payload = proposal.proposed_payload_json
        candidate_kind = payload.get("candidate_kind")
        if candidate_kind == "identity":
            character = _normalize_key(payload.get("character_label"))
            if character:
                groups[("identity", character)].append(proposal)
        elif candidate_kind == "emotional_baseline":
            character = _normalize_key(payload.get("character_label"))
            if character:
                groups[("emotional_baseline", character)].append(proposal)

    reports: list[ConflictReportCandidate] = []
    for (candidate_kind, character), group in groups.items():
        value_field = "identity_value"
        if candidate_kind == "emotional_baseline":
            value_field = "emotional_baseline"
        values = {
            _normalize_key(proposal.proposed_payload_json.get(value_field))
            for proposal in group
        }
        values.discard("")
        if len(values) < 2:
            continue
        reports.append(
            _report(
                conflict_kind="contradiction",
                conflict_key=f"{candidate_kind}:{character}",
                title=f"{candidate_kind.replace('_', ' ').title()} contradiction",
                summary=f"{candidate_kind.replace('_', ' ')} candidates disagree.",
                involved=group,
                review_mode=review_mode,
                extra_payload={
                    "candidate_kind": candidate_kind,
                    "character_key": character,
                    "value_keys": sorted(values),
                },
                confidence=0.74,
                priority=35,
            )
        )
    return reports


def _risk_reports(
    proposals: list[ConflictReviewProposal],
    *,
    review_mode: str,
) -> list[ConflictReportCandidate]:
    reports: list[ConflictReportCandidate] = []
    for proposal in proposals:
        payload = proposal.proposed_payload_json
        evidence = proposal.evidence_json
        payload_uncertain = payload.get("classification") == "uncertain"
        evidence_uncertain = evidence.get("classification") == "uncertain"
        if payload_uncertain or evidence_uncertain:
            reports.append(
                _report(
                    conflict_kind="uncertain",
                    conflict_key=f"uncertain:{proposal.id}",
                    title="Uncertain canon candidate",
                    summary="Uncertain candidate requires admin review before apply.",
                    involved=[proposal],
                    review_mode=review_mode,
                    extra_payload={"candidate_kind": payload.get("candidate_kind", "unknown")},
                    confidence=0.62,
                    priority=50,
                )
            )
        if payload.get("ooc_risk") is True or evidence.get("ooc_risk") is True:
            reports.append(
                _report(
                    conflict_kind="ooc_risk",
                    conflict_key=f"ooc:{proposal.id}",
                    title="OOC risk candidate",
                    summary="Candidate has OOC risk evidence and requires review.",
                    involved=[proposal],
                    review_mode=review_mode,
                    extra_payload={"candidate_kind": payload.get("candidate_kind", "unknown")},
                    confidence=0.58,
                    priority=55,
                )
            )
    return reports


def _report(
    *,
    conflict_kind: str,
    conflict_key: str,
    title: str,
    summary: str,
    involved: list[ConflictReviewProposal],
    review_mode: str,
    extra_payload: dict[str, Any],
    confidence: float,
    priority: int,
) -> ConflictReportCandidate:
    proposal_ids = [str(proposal.id) for proposal in involved]
    source_fragment_id = next(
        (
            proposal.source_fragment_id
            for proposal in involved
            if proposal.source_fragment_id is not None
        ),
        None,
    )
    payload = {
        "candidate_kind": "canon_conflict",
        "conflict_kind": conflict_kind,
        "conflict_key": _fingerprint(conflict_key),
        "involved_proposal_ids": proposal_ids,
        "involved_proposal_count": len(proposal_ids),
        "review_mode": review_mode,
        **extra_payload,
    }
    evidence = {
        "conflict_kind": conflict_kind,
        "involved_proposal_ids": proposal_ids,
        "review_mode": review_mode,
    }
    if source_fragment_id is not None:
        payload["source_fragment_id"] = str(source_fragment_id)
        evidence["source_fragment_id"] = str(source_fragment_id)
    return ConflictReportCandidate(
        source_fragment_id=source_fragment_id,
        proposal_kind=AuthoringProposalKind.OTHER,
        target_ref_kind="canon_conflict_report",
        title=title,
        summary=summary,
        proposed_payload_json=payload,
        evidence_json=evidence,
        confidence=confidence,
        priority=priority,
        conflict_kind=conflict_kind,
        dedupe_key=(conflict_kind, str(payload["conflict_key"])),
    )


def _dedupe_reports(
    candidates: list[ConflictReportCandidate],
) -> list[ConflictReportCandidate]:
    seen: set[tuple[str, ...]] = set()
    deduped: list[ConflictReportCandidate] = []
    for candidate in candidates:
        if candidate.dedupe_key in seen:
            continue
        seen.add(candidate.dedupe_key)
        deduped.append(candidate)
    return deduped


def _normalize_key(value: object) -> str:
    if not isinstance(value, str):
        return ""
    normalized = "_".join(value.strip().lower().split())
    return "".join(
        character if character.isalnum() or character in "_.-" else "_"
        for character in normalized
    )


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
