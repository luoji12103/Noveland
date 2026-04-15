# Regression Policy

Every bug fix affecting stable behavior must add or update a regression test.

## Minimum regression rule

If a bug can be reproduced in an automated way, it must be captured in tests before or with the fix.

## Core regression areas

- world isolation
- auth/access
- replay/snapshot
- agent private memory/calendar isolation
- plugin registration and config
