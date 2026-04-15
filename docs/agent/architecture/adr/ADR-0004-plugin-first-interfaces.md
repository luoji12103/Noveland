# ADR-0004: Plugin-First Interfaces

## Status
Accepted

## Context
The project must be extensible and open-source friendly, but should avoid a plugin marketplace architecture in v1.

## Decision
Define plugin interfaces from day one, but load them through code registration and configuration only.

## Consequences
This preserves extension seams without turning v1 into a dynamic platform product.
