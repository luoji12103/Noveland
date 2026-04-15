# Plugin Contract Policy

Each plugin category must define contract tests.

## Categories

- model provider
- memory backend
- world rules / schedule rules
- persona / behavior policy
- narrative writer / summarizer

## Contract expectations

A plugin implementation must prove:
- it can be registered
- config validates
- capability declaration is correct
- failure modes are surfaced
- required interface methods behave as documented

No plugin implementation merges without passing its category contract tests.
