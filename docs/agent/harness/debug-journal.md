# Debug Journal

## Entry format

- Date:
- Branch:
- Issue:
- Reproduction:
- Root cause:
- Fix:
- Regression test:
- Remaining risk:

## Initial state

No debug entries yet.

## 2026-04-15 backend namespace package import failure

- Date: 2026-04-15
- Branch: feat/bootstrap-runnable-skeleton
- Issue: `uv run pytest` and `uv run mypy .` could not import `noveland.*` workspace packages.
- Reproduction: Run `uv run pytest` from `backend/` after initial workspace setup.
- Root cause: Hatch member configs packaged `src/noveland/<domain>`, which caused editable installs to add nested namespace paths instead of each member's `src` root.
- Fix: Set each member's Hatch wheel package root to `src/noveland` and add all member `src` roots to `mypy_path`.
- Regression test: `uv run pytest` imports every workspace package; `uv run mypy .` now resolves namespace imports.
- Remaining risk: Future package members must keep the same namespace packaging pattern.

## 2026-04-15 Playwright port collision

- Date: 2026-04-15
- Branch: feat/bootstrap-runnable-skeleton
- Issue: Playwright loaded an unrelated Photogiraffe login page instead of the Noveland app.
- Reproduction: Run `npm run test:e2e` while another service owns `127.0.0.1:3000`.
- Root cause: Playwright reused an existing server on the default Next.js port.
- Fix: Move Playwright web server and base URL to `127.0.0.1:3107`.
- Regression test: `npm run test:e2e` now launches the Noveland app and verifies the dashboard shell.
- Remaining risk: Port `3107` could still collide in rare local environments; choose another unused port if that happens.
