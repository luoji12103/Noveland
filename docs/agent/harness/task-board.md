# Task Board

## Open
- None

## In Progress
- None

## Blocked
- None

## Done
- Pre-build architecture and governance package drafted
- Scaffold repository structure
- Establish backend service skeletons
- Establish web app shell
- Establish local infrastructure skeleton
- Define core database schema
- Define plugin registry skeleton
- Define world clock state model
- Define event log + snapshot baseline
- Define auth/session baseline
- Add HTTP auth surface
- Add web auth integration
- Add authorization dependencies
- Add world management API
- Add world dashboard data
- Add runtime clock service
- Runtime Event Emission + NATS Baseline
- Replay + Snapshot Restore Baseline
- Calendar + Schedule Rules Baseline
- Memory Backend + Local pgvector Baseline
- Agent Loop + Narrative Baseline
- Runtime Observability + Diagnostics
- Provider Reliability Hardening
- Agent Observation + Persona Policy Baseline
- Conversation Workspace Baseline
- Conversation Policies + Stop Conditions
- Narrative Writer / Summarizer Pipeline
- Dedicated Narrative Reader Surface
- Realtime Updates
- Agent Composition Presets
- Plugin Runtime Wiring
- Memory Mem0 OSS Foundation
- Memory Context Integration
- Agent Profile Snapshots + Forget / Eval / Ops
- Runtime/Memory Ops
- Runtime/Provider/Memory Ops Hardening
- Provider Secrets Validation
- Runtime Recovery Playbook
- Event/Replay/Clock Ops
- Calendar/Agent Diagnostics Ops
- Conversation/Narrative Quality Ops
- Narrative Reader + Composition Ops
- Plugin/Preset Evolution Ops
- Storage/Backup/Auth Runtime Ops
- Access/Diagnostics/Scale Readiness Ops
- Tool Policy / Scale / v2 Readiness
- Living World Character Foundation
- Living World Autonomous Systems
- Living World GM / Choices / Worldlines
- Living World Plot / Route / Rumor Flow
- Living World Knowledge / Player / Guardrails
- Living World Beta Release Readiness
- V2 Runtime Worldline + Memory Isolation Remediation
- V2 Prompt Boundary + Publish Guardrails Remediation
- V2 Runtime GM + Narrative Execution Depth Remediation
- V2 Beta Acceptance Gating Hardening Remediation
- V2 Acceptance Contract Hardening
- V2 Release Evidence Worldline Gate Hardening
- V2 Beta GM Loop Evidence Hardening
- V2 Web Mock Evidence Parity
- V2 Mem0 Worldline Isolation Contracts
- V2 Release Evidence E2E Stabilization
- Media Kernel Foundation v0.3.1.1
- Media Asset Catalog v0.3.1.2
- Model Invocation Ledger v0.3.1.3
- v0.4 Operator/Admin UX planning baseline
- v0.4 Operator/Admin UX Phase 1: Admin UX Foundation
- v0.4 Operator/Admin UX Phase 2: Provider Admin Console
- v0.4 Operator/Admin UX Phase 3: Media Asset Admin Console implementation
- v0.4 Operator/Admin UX Phase 3: Media Asset Admin Console fast-forward merge
- v0.4 Operator/Admin UX Phase 4: Visual Asset Admin Console planning checkpoint
- v0.4 Operator/Admin UX Phase 4: Visual Asset Admin Console implementation
- v0.4 Operator/Admin UX Phase 4: Visual Asset Admin Console full local gate
- v0.4 Operator/Admin UX Phase 4: Visual Asset Admin Console fast-forward merge
- v0.4 Operator/Admin UX Phase 5: Speech Admin Console planning checkpoint
- v0.4 Operator/Admin UX Phase 5: Speech Admin Console implementation
- v0.4 Operator/Admin UX Phase 5: Speech Admin Console full local gate
- v0.4 Operator/Admin UX Phase 5: Speech Admin Console fast-forward merge
- v0.4 Operator/Admin UX Phase 6: Invocation Ledger Browser planning checkpoint
- v0.4 Operator/Admin UX Phase 6: Invocation Ledger Browser implementation
- v0.4 Operator/Admin UX Phase 6: Invocation Ledger Browser full local gate
- v0.4 Operator/Admin UX Phase 6: Invocation Ledger Browser fast-forward merge
- v0.4 Operator/Admin UX Phase 7: Multimodal Diagnostics Dashboard planning checkpoint
- v0.4 Operator/Admin UX Phase 7: Multimodal Diagnostics Dashboard implementation
- v0.4 Operator/Admin UX Phase 7: Multimodal Diagnostics Dashboard targeted tests
- v0.4 Operator/Admin UX Phase 7: Multimodal Diagnostics Dashboard full local gate
- v0.4 Operator/Admin UX Phase 7: Multimodal Diagnostics Dashboard fast-forward merge

## Upcoming Mainline
- V2 phases 1-50, the four recorded remediation bundles, acceptance contract
  hardening, and the follow-up release/beta/Web/Mem0 evidence hardening work are
  implemented locally.
- Remaining work should come from fresh acceptance reports, beta evidence, operator
  feedback, and targeted hardening rather than a new phase-number branch.
- Use `docs/agent/harness/debug-journal.md` as the source of record. The
  2026-05-10 closure entry supersedes the 2026-05-09 remaining-risk bullets for
  release evidence gates, beta GM loop evidence, Web mock evidence parity, and
  Mem0 worldline isolation contracts.
- Media Kernel Phases 1-3 are backend-only. Later media/invocation work should add
  performance annotations, provider integrations,
  upload/download policy, asset embeddings/similarity search, and Web surfaces
  in separate feature-named branches.
