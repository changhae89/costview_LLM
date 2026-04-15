# Project Agent Guide

This repository uses `AGENTS.md` as the shared source of truth for project-level instructions across coding agents. Tool-specific files such as `.cursorrules` should stay thin and defer to this file when possible.

## Tech Stack

- **Mobile app**: Expo (React Native), React 19, TypeScript/JavaScript with ESM
- **Backend**: Python 3, FastAPI, Uvicorn, SQLAlchemy, PostgreSQL (`DATABASE_URL`)
- **Auth / data (client)**: `@supabase/supabase-js` in the Expo app where Supabase is used
- **Data jobs**: Python scripts under `history_loader/`, `history_naver/`, `prd/`, `proposal/` (HTTP clients, DB writes, optional Supabase helpers in `common/`)
- **Infra**: Backend deploy target includes Render (`backend/render.yaml`); mobile is Expo (dev client / EAS / store builds as configured)
- **Automation**: GitHub Actions under `.github/workflows/` (e.g. `prd.yml`, `proposal.yml`)

## Project Structure

- `frontendapp/costview/`: Expo app (main UI); API wrapper at `src/lib/api.ts`
- `backend/`: FastAPI service (`app/main.py`, routers under `app/api/routes/`, schemas under `app/schemas/`, SQLAlchemy models under `app/models/`)
- `history_loader/`, `history_naver/`: standalone Python loaders (news/history → DB or Supabase-backed flows per script)
- `prd/`, `proposal/`: Python tooling and pipelines related to PRD/proposal workflows; LLM eval fixtures live under **`prd/evals/`**
- `costview_LLM/`: separate Node package (pnpm, Vitest) for LLM-related utilities; not the main mobile app
- `common/`: shared Python modules (e.g. `supabase_client.py`) imported by loaders
- `.github/workflows/`: CI and scheduled or manual automation

There is **no** `supabase/functions/` tree in this repo today; if Edge Functions are added later, document them here.

## Mobile app rules (Expo)

Applies to `frontendapp/costview/`.

- Use functional components and hooks only.
- Use `fetch` for HTTP calls to the FastAPI backend.
- Read the API base URL from `EXPO_PUBLIC_API_URL` (see `src/lib/api.ts`); default local backend port in code is `8020` when unset.
- Keep HTTP/API access logic in `src/lib/api.ts` (extend this module rather than scattering `fetch` URLs).
- Use `react-native-chart-kit` (and related SVG stack) for charts in this app—not `lightweight-charts` (web-only).
- Prefer ESM imports; avoid CommonJS `require()` in app source.
- **Expo** public env vars must use the `EXPO_PUBLIC_` prefix (not `VITE_`).

## Backend rules

Applies to `backend/`.

- Use FastAPI with type hints on endpoints.
- Use Pydantic models for request/response schemas under `app/schemas/` as in existing routes.
- Use **SQLAlchemy** and the existing session/engine pattern (`app/core/database.py`, `get_db`) for PostgreSQL access. Do not introduce ad hoc raw SQL in route handlers unless the user explicitly asks or it matches existing migration/script patterns.
- Load configuration via `app/core/config.py` / environment variables (e.g. `python-dotenv` where already used).
- Keep **CORS** appropriate for real callers (Expo dev, production origins); avoid widening `allow_origins` without cause (`app/main.py`).
- Organize HTTP routers by domain under `app/api/routes/` (e.g. `news.py`, `dashboard.py`).
- Return structured JSON consistently.

## Supabase and database

- **Mobile**: use `@supabase/supabase-js` following existing app patterns for auth/storage when touching Supabase from the client.
- **Python loaders**: when a script already uses `common/supabase_client.py` or Supabase APIs, stay consistent with that file and surrounding modules.
- **Backend API**: uses SQLAlchemy + Postgres; it does not currently use the Supabase Python client—do not assume it unless the project is migrated.
- Prefer **RLS** and Supabase Auth policies on Supabase-managed tables when applicable (product/security requirement).

## Data loader and PRD script rules

Applies to `history_loader/`, `history_naver/`, `prd/`, `proposal/`, and similar Python entrypoints.

- Prefer clear CLI entrypoints and `python-dotenv` / env vars for secrets.
- Use **UTC** for stored/processed timestamps unless a script documents a different convention.
- Keep scripts runnable locally and compatible with how they are invoked from GitHub Actions (if wired).
- Reuse `common/` for shared Supabase or config helpers instead of duplicating connection logic.

## GitHub Actions rules

- Workflows live in `.github/workflows/` (e.g. `ci.yml`, `prd.yml`, `proposal.yml`).
- Never hardcode secrets; use repository or environment secrets.
- When adding jobs, avoid breaking existing workflow names and triggers unless intentionally migrating them.

## Coding constraints (when writing or changing code)

These are **hard expectations** for humans and agents—not optional style tips.

- **Scope**: Change only what the task requires. No unrelated refactors, no drive-by formatting sweeps, no new docs unless asked.
- **Stack fit**: Follow the Mobile / Backend / loader sections above (imports, env var prefixes, API layout, SQLAlchemy patterns).
- **Secrets**: Never commit API keys, tokens, or production connection strings. Use env vars and repository secrets in CI.
- **Size and clarity**: Prefer small, reviewable diffs; keep functions focused; use names like `is_loading`, `has_error`.
- **Comments**: Only for non-obvious logic—do not narrate obvious code.
- **After edits**: Run the relevant local commands under **Verification and agent harnesses → Automated test entrypoints**; for branches opened as PRs, the **PR/push test harness** (`ci.yml`) should be green when secrets are configured.

## General coding rules

- Never hardcode API keys, URLs, or secrets.
- Prefer descriptive names such as `is_loading`, `has_error`, and `is_active`.
- Keep functions focused and reasonably small.
- Handle errors explicitly (`try/catch` in JS/TS, `try/except` in Python).
- Add comments only for non-obvious logic.

## Error handling rules

- When an error appears, identify the root cause first, then fix it.
- After a fix, verify both failure and happy paths.
- If the same error repeats more than twice, stop patching symptoms and fix the underlying cause.
- For import errors, check module paths and package boundaries before broad refactors.
- For FastAPI **422** responses, inspect the Pydantic schema and request body/query shape first.
- For **CORS** issues, verify backend `CORSMiddleware` settings before changing client fetch code.

## Verification and agent harnesses

This section is what makes `AGENTS.md` useful for **harness-style** work: clear, repeatable checks—not only style rules.

### Automated test entrypoints (run after non-trivial changes)

- **Backend** (`backend/`): from `backend/`, run `pytest` (config: `pytest.ini`, tests under `backend/tests/`). Use a valid `DATABASE_URL` or existing test fixtures/conftest patterns when tests touch the DB.
- **Expo app** (`frontendapp/costview/`): run `npm test` (Jest / `jest-expo` as configured in `package.json`).
- **costview_LLM/**: run `pnpm test` or `npm test` per that package’s `package.json` (Vitest).

Agents should **run the relevant commands above** (or explain why they cannot, e.g. missing secrets) before treating a change as complete.

### PR/push test harness (GitHub Actions)

- **Workflow**: `.github/workflows/ci.yml` runs on every **`push`** and **`pull_request`**.
- **Always runs** (no extra secrets): **`expo-app`** — `npm ci`, `npm run lint`, `npm test -- --ci` in `frontendapp/costview/`; **`costview-llm`** — `npm ci`, `npm test` (Vitest) in `costview_LLM/`.
- **Backend** (`backend-tests`): runs **`pytest`** with **`DATABASE_URL`** from **repository secrets**. Configure the `DATABASE_URL` secret in the GitHub repo (same value style as local Postgres/Supabase URI). If the secret is missing, the backend job fails with a clear message.
- **Fork PRs**: the backend job is **skipped** when the PR comes from a fork (`head` repo ≠ base repo), because GitHub does not expose secrets to those workflows. Same-repo PRs and all **`push`** events on this repository still run backend tests when the secret is set.

### CI as operational harnesses

- `.github/workflows/prd.yml` and `proposal.yml` are **scheduled/production harnesses**: they execute `prd/main.py` and `proposal/main.py` with repository secrets. They validate “pipeline still runs in CI,” not unit-test coverage.
- When changing those scripts or their dependencies, keep workflow paths and `requirements.txt` locations in sync and preserve `workflow_dispatch` for manual reruns.

### LLM / LangChain and non-deterministic logic

- Prefer **deterministic unit tests** for parsing, schema validation, and tool I/O boundaries where outputs can be fixed or mocked.
- **Canonical eval harness data**: put golden inputs, expected outputs (when stable), and rubric notes under **`prd/evals/`** (see `prd/evals/README.md`). Co-locate ad hoc fixtures next to the code only when they are tightly coupled to a single module; otherwise prefer `prd/evals/`.
- Do not commit API keys; CI already expects secrets such as `GEMINI_API_KEY`, `DATABASE_URL`, etc.

### Definition of done (agent-facing)

- Happy path **and** failure path considered (see [Error handling rules](#error-handling-rules)).
- Relevant **pytest / Jest / Vitest** suite passes locally; same-repo PRs / pushes should pass **`ci.yml`** (Expo + costview_LLM always; backend when `DATABASE_URL` secret exists).
- No new hardcoded secrets or production URLs.

## Working agreement

- Prefer shared rules in this file over duplicating long instructions in tool-specific configs.
- Keep tool-specific files lightweight and pointed at `AGENTS.md`.
