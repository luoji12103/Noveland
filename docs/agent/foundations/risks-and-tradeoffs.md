# Risks and Tradeoffs

## Major risks

### 1. Over-engineering too early
Mitigation: keep one modular backend and one web app.

### 2. Plugin abstraction without implementation discipline
Mitigation: interfaces first, code-registered implementations only, no hot marketplace.

### 3. World rules drifting into prompts
Mitigation: all world timing and rule logic must live in kernel code/config.

### 4. Snapshot/replay becoming fake
Mitigation: keep event log append-only and snapshots explicit from the beginning.

### 5. Directory and utility sprawl
Mitigation: strict file creation rules and file inventory.

### 6. Session handoff failure
Mitigation: active handoff, task board, change/debug journals.

## Tradeoffs accepted

- dual-language stack (TS + Python)
- slightly heavier upfront governance
- lower short-term speed in exchange for lower long-term refactor risk
