# multiworld-multiuser-stress Specification

## Purpose
This spec captures the current v1.1 normal-use stress capability on `main`. It covers deterministic fake-provider stress evidence for multiple worlds, worldlines, players, provider profiles, and long-session equivalents while enforcing isolation, quota coverage, safe reporting, and no default real-provider spend.
## Requirements
### Requirement: Stress tests cover multiple worlds and players
The system SHALL provide controlled stress fixtures or evals for multiple worlds, multiple players, multiple provider profiles, and long sessions. The first normal-use baseline SHALL cover at least 3 worlds, 2 worldlines per world, 2 player sessions per world, 2 fake provider profiles, and a deterministic 120-turn or equivalent long-session run.

#### Scenario: Multi-world stress run
- **Given** a stress fixture creates multiple worlds and players
- **When** the stress run executes
- **Then** each world and player SHALL remain isolated
- **And** cross-world or cross-worldline data leakage SHALL be reported as a failure.

### Requirement: Stress tests use fake providers by default
The system SHALL use fake or mocked providers in default stress tests and SHALL require opt-in for real provider stress.

#### Scenario: Default stress test
- **Given** the default local gate runs
- **When** stress tests execute
- **Then** no real provider quota SHALL be consumed.

### Requirement: Stress reports are safe
The system SHALL produce stress reports with aggregate metrics and safe evidence references.

#### Scenario: Stress report generated
- **Given** a long-session stress run completes
- **When** the report is returned
- **Then** it SHALL include latency, cost, failure, quota, worldline, and session summaries
- **And** it SHALL NOT expose raw prompts, raw outputs, storage paths, or secrets.
