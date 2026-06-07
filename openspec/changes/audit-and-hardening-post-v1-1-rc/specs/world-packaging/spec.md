## MODIFIED Requirements

### Requirement: World import uses preview before apply
The system SHALL validate imports in a preview step before mutating world state.

#### Scenario: Import preview detects incompatibility
- **Given** a package references an unsupported capability
- **When** import preview runs
- **Then** it SHALL report a blocker
- **And** it SHALL NOT create world, media, or provider records.

#### Scenario: Import apply requires CSRF
- **Given** an authenticated world admin browser session applies a package import
- **When** the import apply request would create or link world, media, or provider records
- **Then** the API SHALL require a matching CSRF cookie and X-CSRF-Token header before applying the package.
