# Scope and Non-Goals

## Primary scope

Build a stable kernel for persistent multi-agent worlds with narrative output, not a feature-maximal simulation platform.

## Non-goals

- building a social network product
- building a mobile-first experience
- exposing a public developer platform in v1
- supporting unbounded tool execution
- solving generalized multi-tenant SaaS concerns
- optimizing for 100+ agent scale in v1
- inventing a second architecture in parallel

## Anti-scope drift rules

- No new major surface area without updating MVP docs.
- No implementation of real cross-world migration in v1.
- No uncontrolled plugin loading.
- No direct agent access to other agents' private resources.
- No making raw prompts or raw chat logs the canonical state source.
