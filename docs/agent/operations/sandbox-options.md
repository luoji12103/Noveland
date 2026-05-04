# Sandbox Options Design

## Purpose

This document records the sandbox decision boundary for future runtime/tool work. It is design-only; no sandbox is implemented in this bundle.

## Current Position

- Runtime executes trusted first-party Python code.
- Built-in plugins run in-process.
- External tool policy is not yet implemented.
- No user-authored code execution is supported.

## Candidate Options

- In-process validation only: lowest complexity, insufficient for untrusted code.
- Subprocess sandbox: useful for local tool execution with explicit timeouts and environment control.
- Container sandbox: stronger isolation, higher operational complexity for local/single-host deployments.
- Remote worker sandbox: best isolation boundary, but introduces queue, network, and secrets-management complexity.

## Selection Criteria

- Prevent secret exposure.
- Preserve world/user/runtime actor attribution.
- Support deterministic audit logs.
- Keep local development usable.
- Avoid introducing a distributed queue before the queue-readiness phase is complete.

## Non-Goals

- No marketplace execution.
- No hot reload of untrusted plugins.
- No hard sandbox in v1.

Future implementation should start with an external tool policy and a narrow subprocess/container proof before changing core runtime behavior.
