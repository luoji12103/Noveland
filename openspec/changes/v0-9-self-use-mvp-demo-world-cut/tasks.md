# Tasks — v0.9 Self-use MVP Demo World Cut

Use these tasks when implementation is explicitly requested. Planning tasks may be marked complete during roadmap alignment; implementation tasks must only be marked complete after code, tests, full local gate, fast-forward merge, and harness updates are done.

## 1. Planning / Preflight

- [x] 1.1 Confirm v0.8 archived current specs and no active OpenSpec changes conflict with v0.9.
- [x] 1.2 Write v0.9 feasibility review before implementation begins.
- [x] 1.3 Confirm provider text/image execution, model discovery, and template ownership.
- [x] 1.4 Confirm Visual Generation Control Plane package/router/schema ownership before implementation.
- [ ] 1.5 Confirm galgame source intake legal/technical boundary: already-unpacked user-provided inputs only.
- [x] 1.6 Confirm frontend phases will use `impeccable` before Web implementation.

## 2. Phase 1 — MVP Provider Settings & Model Lab

- [x] 2.1 Write docs-only phase planning checkpoint.
- [x] 2.2 Inventory current provider integrations, adapters, capabilities, smoke tests, and v0.4 provider admin UI.
- [x] 2.3 Implement provider templates, editable settings, model discovery, manual model fallback, image capability metadata, and safe smoke checks.
- [x] 2.4 Add provider settings/model lab UI only after using `impeccable`.
- [x] 2.5 Add provider template, model list, manual fallback, image capability, ACL, and leak tests.
- [x] 2.6 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [x] 2.7 Fast-forward merge to local main and update harness docs.

## 3. Phase 2 — Visual Generation Control Plane

- [x] 3.1 Write docs-only phase planning checkpoint.
- [x] 3.2 Decide visual generation package/router/schema ownership and migration need.
- [ ] 3.3 Implement workflow template registry with validated parameter slots.
- [ ] 3.4 Implement visual model asset inventory for checkpoint, LoRA, VAE, embedding, ControlNet, IP-Adapter, workflow template, and prompt preset metadata.
- [ ] 3.5 Implement character/worldline visual generation profiles.
- [ ] 3.6 Implement provider-neutral visual generation plan DTOs and validation.
- [ ] 3.7 Implement ComfyUI slot mapping validator and raw workflow JSON rejection.
- [ ] 3.8 Implement AI-assisted workflow binding/profile proposals and workflow variant proposals as review/apply only.
- [ ] 3.9 Add UI only after using `impeccable` if Web scope is approved.
- [ ] 3.10 Add template, slot, model inventory, LoRA compatibility, profile, plan, adapter mapping, ACL, worldline, media, ledger, and no-leak tests.
- [ ] 3.11 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 3.12 Fast-forward merge to local main and update harness docs.

## 4. Phase 3 — Provider Worktree Integration Test Harness

- [ ] 4.1 Write docs-only phase planning checkpoint.
- [ ] 4.2 Document provider lab worktree setup and opt-in env variables.
- [ ] 4.3 Add real-provider test markers/profile with default skip behavior.
- [ ] 4.4 Add fake-provider parity tests and opt-in smoke examples, including optional ComfyUI dry-run/mock workflow checks.
- [ ] 4.5 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 4.6 Fast-forward merge to local main and update harness docs.

## 5. Phase 4 — Galgame Source Intake

- [ ] 5.1 Write docs-only phase planning checkpoint.
- [ ] 5.2 Confirm authoring source registry reuse and any migration need.
- [ ] 5.3 Implement already-unpacked source directory intake and preview inventory.
- [ ] 5.4 Support reviewed imported visual assets as future generation reference candidates.
- [ ] 5.5 Add source intake UI only after using `impeccable` if Web scope is approved.
- [ ] 5.6 Add intake, source traceability, media import, generation reference, ACL, and leak tests.
- [ ] 5.7 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 5.8 Fast-forward merge to local main and update harness docs.

## 6. Phase 5 — Script Dialogue Extraction

- [ ] 6.1 Write docs-only phase planning checkpoint.
- [ ] 6.2 Implement deterministic extraction for selected sample formats and manual-label fallback.
- [ ] 6.3 Keep provider extraction optional and ledger-backed if included.
- [ ] 6.4 Add parser, proposal, speaker mapping, uncertainty, ACL, and leak tests.
- [ ] 6.5 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 6.6 Fast-forward merge to local main and update harness docs.

## 7. Phase 6 — Character Memory Distillation Agent

- [ ] 7.1 Write docs-only phase planning checkpoint.
- [ ] 7.2 Implement provider-backed persona card and memory candidate generation through `ProviderExecutionService`.
- [ ] 7.3 Implement optional visual generation profile recommendations as proposals only.
- [ ] 7.4 Implement review/apply to persona and memory only after explicit approval.
- [ ] 7.5 Add invocation ledger, prompt redaction, source traceability, profile proposal, apply, and no-leak tests.
- [ ] 7.6 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 7.7 Fast-forward merge to local main and update harness docs.

## 8. Phase 7 — Visual Asset Mapping

- [ ] 8.1 Write docs-only phase planning checkpoint.
- [ ] 8.2 Implement sprite/background/CG mapping proposals and reviewed apply.
- [ ] 8.3 Reuse visual resolver and reader-safe media delivery.
- [ ] 8.4 Support approved imported assets as visual generation reference assets where appropriate.
- [ ] 8.5 Add visual mapping UI only after using `impeccable` if Web scope is approved.
- [ ] 8.6 Add mapping, fallback, reference-asset, worldline isolation, ACL, and no-leak tests.
- [ ] 8.7 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 8.8 Fast-forward merge to local main and update harness docs.

## 9. Phase 8 — Voice Profile Mapping

- [ ] 9.1 Write docs-only phase planning checkpoint.
- [ ] 9.2 Implement voice reference/provider mapping proposals and reviewed apply.
- [ ] 9.3 Implement MiMo/generic speech provider settings usage without hardcoded endpoints.
- [ ] 9.4 Add voice mapping UI only after using `impeccable` if Web scope is approved.
- [ ] 9.5 Add TTS smoke, binding, style mapping, ACL, and no-secret tests.
- [ ] 9.6 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 9.7 Fast-forward merge to local main and update harness docs.

## 10. Phase 9 — Demo World Assembly

- [ ] 10.1 Write docs-only phase planning checkpoint.
- [ ] 10.2 Implement reviewed demo assembly from applied import/persona/memory/visual generation profile/visual/voice/dialogue proposals.
- [ ] 10.3 Add demo-world setup UI only after using `impeccable` if Web scope is approved.
- [ ] 10.4 Add assembly, source traceability, visual profile, playback, scene, memory, and no-leak tests.
- [ ] 10.5 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 10.6 Fast-forward merge to local main and update harness docs.

## 11. Phase 10 — 30-Minute Self-use MVP Gate

- [ ] 11.1 Write docs-only phase planning checkpoint.
- [ ] 11.2 Implement self-use MVP gate evidence aggregation or checklist.
- [ ] 11.3 Validate 30-minute play evidence, resume behavior, visual generation readiness, provider failure messaging, and admin inspection links.
- [ ] 11.4 Add gate pass/fail, persistence, memory, visual generation, provider/media diagnostics, ACL, and no-leak tests.
- [ ] 11.5 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 11.6 Fast-forward merge to local main and update harness docs.

## 12. Closeout

- [ ] 12.1 Archive the completed OpenSpec change only after all phases are accepted.
- [ ] 12.2 Generate v0.9 release notes.
- [ ] 12.3 Confirm main is clean and report ahead/behind origin.
