## ADDED Requirements

### Requirement: Audit changes are OpenSpec-governed
The project SHALL track post-v1.1 release-candidate audit findings, remediation tasks, tests, and closeout evidence under an active OpenSpec change before implementation changes are made.

#### Scenario: Findings precede remediation
- **WHEN** an audit identifies a security, product, or spec-compliance issue that requires implementation changes
- **THEN** the issue is recorded as an OpenSpec task or finding with severity, affected boundary, evidence, intended remediation, and targeted verification before the fix is completed

#### Scenario: Existing capability behavior changes
- **WHEN** a remediation changes the behavior promised by an existing OpenSpec capability
- **THEN** the change includes the appropriate capability spec delta before the implementation is completed

### Requirement: Security boundary regressions are prioritized
The project SHALL prioritize fixes that protect authentication, authorization, worldline isolation, provider spend, provider secrets, prompt/output privacy, storage/media references, and admin/player/reader/member API boundaries.

#### Scenario: Forbidden response data is found
- **WHEN** an audit finds resolved secrets, disallowed auth refs, storage URIs, filesystem/object paths, local model paths, raw prompts, raw outputs, prompt snapshot internals, invite tokens, bytes, or base64 in a non-admin-safe response or event payload
- **THEN** the remediation removes or redacts the forbidden data and adds targeted regression coverage for that exposure path

#### Scenario: Cross-scope access is found
- **WHEN** an audit finds cross-world, cross-worldline, cross-player, cross-role, or cross-member access that violates existing authorization contracts
- **THEN** the remediation enforces the correct scope and adds tests for allowed access and denied cross-scope access

### Requirement: Provider execution remains controlled
The project SHALL keep provider-backed work behind `ProviderExecutionService`, quota checks, explicit audit evidence, and fake/mocked default tests.

#### Scenario: Provider spend path is audited
- **WHEN** an audit reviews code that can trigger provider, media, image, speech, runtime, or fallback execution
- **THEN** it verifies that the path is quota-guarded before adapter execution and does not resolve secrets or call providers in default tests

#### Scenario: Real-provider test remains opt-in
- **WHEN** the audit or remediation runs tests by default
- **THEN** it does not set `NOVELAND_RUN_REAL_PROVIDER_TESTS=1` and does not require external provider quota

### Requirement: Harness handoff stays current
The project SHALL update harness records after each meaningful audit or remediation batch so repository state, findings, tests, and remaining risk are recoverable.

#### Scenario: Batch closeout
- **WHEN** an audit or remediation batch is ready to stop or commit
- **THEN** the branch, OpenSpec task state, changed files, tests run, test gaps, findings, and residual risks are recorded in the necessary harness documents

#### Scenario: Final closeout
- **WHEN** the audit change is ready for completion
- **THEN** git status is clean, OpenSpec validation passes, relevant targeted tests are recorded, no push has occurred unless explicitly requested, and remaining risks are documented
