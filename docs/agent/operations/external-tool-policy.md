# External Tool Policy

External tool policy is policy-only in v1. Noveland does not execute external
tools, subprocesses, filesystem commands, network actions, or sandboxed code
through agent runtime paths.

## Operator Surface

- `GET /runtime/tool-policy` reports the current policy mode.
- The response is platform-admin only.
- `execution_enabled=false` means there is no runtime execution path.
- Policy responses may include secret refs in future work, but never secret values.

## Policy Inputs

Future allow/deny decisions must include:

- world id
- agent id when applicable
- actor ref, such as `system:runtime`
- tool identifier
- permission mode
- correlation id

## Deny Reasons

The v1 deny vocabulary includes:

- `external_tool_execution_disabled`
- `tool_not_allowlisted`
- `missing_world_or_actor_context`
- `secret_exposure_risk`
- `network_or_process_sandbox_unavailable`

## Boundaries

- No uncontrolled plugin loading.
- No remote marketplace or hot reload.
- No subprocess proof-of-concept in this phase.
- No memory writes or world events may be created from external tool output until
  attribution, redaction, and review rules are defined.
