# Project Agent Guide

This repository uses `AGENTS.md` as the shared source of truth for project-level instructions across coding agents. Tool-specific files such as `.cursorrules` should stay thin and defer to this file when possible.

## Tech Stack

- **Mobile app**: Expo (React Native), React, JavaScript/ESM — `front_app/`
- **Web app**: Vite + React, TypeScript — `front_web/`
- **Backend**: Python 3, FastAPI, Uvicorn, psycopg (raw), PostgreSQL (`DATABASE_URL`) — `backend/`
- **Auth / data (client)**: `@supabase/supabase-js` in `front_app/src/lib/supabase.js`
- **Data jobs**: Python scripts under `prd/` (LLM pipelines, DB writes)
- **Root package**: Vitest-based LLM utilities at the repo root (`vitest.config.ts`, `package.json`)
- **Automation**: GitHub Actions under `.github/workflows/` (`deploy.yml`, `data-sync-all.yml`)

## Project Structure

- `front_app/`: Expo (React Native) app; API/Supabase helpers at `src/lib/`
- `front_web/`: Vite web app (`src/main.tsx`, routers under `src/pages/`, components under `src/components/`)
- `backend/`: FastAPI service (`main.py`, routers under `api/routes/`, schemas under `schemas/`, DB at `db.py`, config at `config.py`)
- `prd/`: Python LLM pipeline (`main.py`); tests under `prd/tests/`; DB backtest validation under `prd/validation/` (run `cd prd && python -m validation.main`)
- `data_collector/`: data mining and reasoning scripts (`src/data_mining/`, `src/reasoning/`); own backend entry at `data_collector/backend/main.py`
- `infra/`: infrastructure configuration
- `.github/workflows/`: CI and scheduled automation (`deploy.yml`, `data-sync-all.yml`)

## Mobile app rules (Expo)

Applies to `front_app/`.

- Use functional components and hooks only.
- Use `fetch` for HTTP calls to the FastAPI backend.
- Keep API/Supabase access logic in `src/lib/` (extend existing modules rather than scattering fetch calls).
- Use `react-native-chart-kit` (and related SVG stack) for charts—not `lightweight-charts` (web-only).
- Prefer ESM imports; avoid CommonJS `require()` in app source.
- **Expo** public env vars must use the `EXPO_PUBLIC_` prefix (not `VITE_`).

## Web app rules

Applies to `front_web/`.

- Use functional components and hooks only.
- Use `VITE_` prefix for public env vars.
- Keep API logic centralized under `src/lib/` or `src/app/`.

## Backend rules

Applies to `backend/`.

- Use FastAPI with type hints on endpoints.
- Use Pydantic models for request/response schemas under `schemas/`.
- Use **psycopg** via `db.py` (`get_conn()`) for PostgreSQL access. Do not introduce raw SQL outside of existing patterns.
- Auth is handled via Supabase JWT validation (`auth.py`); do not bypass it.
- Load configuration via `config.py` / environment variables.
- Keep **CORS** appropriate for real callers (Expo dev, production origins); avoid widening `allow_origins` without cause (`main.py`).
- Organize HTTP routers by domain under `api/routes/` (e.g. `category.py`, `consumer_item.py`).
- Return structured JSON consistently.

## Supabase and database

- **Mobile**: use `@supabase/supabase-js` following existing patterns in `front_app/src/lib/supabase.js`.
- **Backend API**: uses psycopg + Postgres directly for data; uses Supabase for auth JWT validation (`auth.py`).
- Prefer **RLS** and Supabase Auth policies on Supabase-managed tables when applicable.

## PRD script rules

Applies to `prd/`.

- Prefer clear CLI entrypoints and `python-dotenv` / env vars for secrets.
- Use **UTC** for stored/processed timestamps unless a script documents a different convention.
- Keep scripts runnable locally and compatible with how they are invoked from GitHub Actions.
- **LangChain 프롬프트 중괄호**: 프롬프트 문자열 내 JSON 예시·리터럴 중괄호는 반드시 `{{`, `}}`로 이스케이프한다. 단일 `{...}`는 템플릿 변수로 해석되어 `ChatPromptTemplate` 생성 시 ValueError 발생.
- **DB 스키마 선확인**: 쿼리에 컬럼을 추가하기 전 실제 테이블 스키마를 확인한다 (Supabase 대시보드 또는 `\d tablename`). 없는 컬럼 조회는 APIError `42703`을 유발한다.
- **신규 테이블 선생성**: 코드 작성 전 마이그레이션 SQL을 먼저 실행한다. 테이블이 없는 상태로 코드를 배포하면 저장 단계에서 실패한다.

## GitHub Actions rules

- Workflows live in `.github/workflows/` (`deploy.yml`, `data-sync-all.yml`).
- Never hardcode secrets; use repository or environment secrets.
- When adding jobs, avoid breaking existing workflow names and triggers unless intentionally migrating them.

## Coding constraints

These are **hard expectations** for humans and agents—not optional style tips.

- **Scope**: Change only what the task requires. No unrelated refactors, no drive-by formatting sweeps, no new docs unless asked.
- **Stack fit**: Follow the Mobile / Web / Backend sections above (imports, env var prefixes, API layout, psycopg patterns).
- **Secrets**: Never commit API keys, tokens, or production connection strings. Use env vars and repository secrets in CI.
- **Size and clarity**: Prefer small, reviewable diffs; keep functions focused; use names like `is_loading`, `has_error`.
- **Error handling**: Handle errors explicitly (`try/catch` in JS/TS, `try/except` in Python).
- **Comments**: Only for non-obvious logic—do not narrate obvious code.
- **After edits**: Run the relevant local commands under **Verification and agent harnesses → Automated test entrypoints**.

## Error handling rules

- When an error appears, identify the root cause first, then fix it.
- After a fix, verify both failure and happy paths.
- If the same error repeats more than twice, stop patching symptoms and fix the underlying cause.
- For import errors, check module paths and package boundaries before broad refactors.
- For FastAPI **422** responses, inspect the Pydantic schema and request body/query shape first.
- For **CORS** issues, verify backend `CORSMiddleware` settings before changing client fetch code.

## Verification and agent harnesses

### 수정 → 테스트 → 반복 원칙

모든 변경은 아래 사이클을 완료해야 done으로 간주한다:

1. **수정**: 코드 작성
2. **테스트**: 아래 테스트 항목을 순서대로 실행
3. **미통과 시 재수정**: 통과할 때까지 1~2 반복 후 커밋

### Automated test entrypoints (run after non-trivial changes)

- **Backend** (`backend/`): no dedicated test suite; verify endpoints manually or with an HTTP client.
- **LLM pipeline** (`prd/`): from `prd/`, run `pytest tests/`. Use a valid `DATABASE_URL` when tests touch the DB.
- **Expo app** (`front_app/`): no test script; run `npm run lint` to check for lint errors.
- **Web app** (`front_web/`): no test script; run `npm run build` to verify compilation.
- **Root LLM utilities**: run `npm test` (Vitest) at the repo root.
- **data_collector**: run `python test.py` from `data_collector/`; no formal test suite.

Agents should **run the relevant commands above** (or explain why they cannot, e.g. missing secrets) before treating a change as complete.

### PR/push test harness (GitHub Actions)

- **Workflows**: `.github/workflows/deploy.yml`, `data-sync-all.yml`.
- Never hardcode secrets; all credentials must come from repository or environment secrets (e.g. `DATABASE_URL`, `GEMINI_API_KEY`).

### LLM / non-deterministic logic

- Prefer **deterministic unit tests** for parsing, schema validation, and tool I/O boundaries where outputs can be fixed or mocked.
- Tests live under `prd/tests/`.
- Do not commit API keys; CI expects secrets such as `GEMINI_API_KEY`, `DATABASE_URL`, etc.

### Definition of done (agent-facing)

- Happy path **and** failure path considered (see [Error handling rules](#error-handling-rules)).
- Relevant test suite passes locally.
- No new hardcoded secrets or production URLs.
- 신규 DB 테이블을 사용하는 경우, 마이그레이션을 코드 커밋 **전** 적용하고 실제 저장 쿼리 성공을 확인한다.
- LLM 파이프라인(`prd/`)은 빌드·유닛 테스트뿐 아니라 **end-to-end 실행**(DB 저장까지) 성공을 확인해야 done으로 간주한다.

### LLM 파이프라인 체크리스트 (prd/ 신규 기능 추가 시)

| 순서 | 항목 | 확인 방법 |
|------|------|-----------|
| 1 | 프롬프트 중괄호 이스케이프 | `ChatPromptTemplate.from_messages(...)` import 시 오류 없음 |
| 2 | 쿼리 컬럼이 실제 테이블에 존재 | Supabase 대시보드 또는 `\d tablename` 로 스키마 확인 |
| 3 | 신규 테이블 마이그레이션 선실행 | SQL 실행 후 테이블 존재 확인 |
| 4 | 헬퍼 함수 단위 테스트 | `python -c "from prd.llm... import ..."` |
| 5 | `pytest prd/tests/` 전체 통과 | 기존 테스트 회귀 없음 확인 |
| 6 | **수정한 프로그램 직접 실행** | `python -m prd.<entrypoint>` 실행 후 오류 없이 완료 확인 |
| 7 | **DB 저장 확인** | `SELECT ... FROM <table> ORDER BY created_at DESC LIMIT 3` 으로 실제 저장된 행 조회 |

## Git Workflow

변경 작업은 아래 순서로 진행한다:

1. **이슈 등록** — `gh issue create` (제목 + 작업 내용)
2. **브랜치 생성** — `feature/<issue번호>-<설명>`
3. **커밋** — `feat/fix: 설명 (#이슈번호)`
4. **PR → origin/main 머지** — `gh pr create --base main` → `gh pr merge`
5. **이슈 코멘트** — 변경 내용 정리 후 `gh issue comment`
6. **이슈 close** — `gh issue close`

권장 형식:

- 브랜치: `feature/<issue-number>-<short-description>` 또는 `fix/<issue-number>-<short-description>`
- 커밋: `feat: short summary (#<issue-number>)` 또는 `fix: short summary (#<issue-number>)`
- 이슈 코멘트: 변경 내용 요약, 검증 결과, 관련 PR/커밋 링크를 함께 남긴다.

## Response Style

- **Length**: 텍스트 설명은 300자 이내로 간결하게 작성한다. 표·도형·다이어그램은 글자 수 제한 없이 적극 활용한다.
- **Format**: 수치 비교는 표, 흐름 설명은 도형/다이어그램 등 시각 요소를 우선한다.

## Working agreement

- Prefer shared rules in this file over duplicating long instructions in tool-specific configs.
- Keep tool-specific files lightweight and pointed at `AGENTS.md`.
- Keep `CLAUDE.md` focused on Claude-only tool/behavior deltas; avoid restating project workflow here.
