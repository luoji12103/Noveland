# Experimental Work Policy

## Allowed locations

- `backend/experimental/`
- `web/experimental/`

## Rules

- production code must not depend on experimental code
- experiments still require logging
- experiments must have an exit:
  - promote
  - archive
  - delete

## Prohibited

- silently letting experimental code become production-critical
- using experimental folders as a permanent overflow area
