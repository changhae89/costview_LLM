# Claude Code Project Guide

> Full project rules live in [AGENTS.md](./AGENTS.md). This file adds Claude Code-specific behavior on top of those shared rules.

## Tool Usage

Use dedicated tools instead of shell equivalents:

| Task | Use | Not |
|------|-----|-----|
| Read a file | `Read` | `cat`, `head`, `tail` via Bash |
| Edit a file | `Edit` / `Write` | `sed`, `awk`, `echo >` via Bash |
| Find files | `Glob` | `find`, `ls` via Bash |
| Search content | `Grep` | `grep`, `rg` via Bash |
| Run commands / tests | `Bash` | — |

## Git Workflow

변경 작업 완료 시 반드시 아래 순서로 진행한다:

1. **이슈 등록** — `gh issue create` (제목 + 작업 내용)
2. **브랜치 생성** — `feature/<issue번호>-<설명>`
3. **커밋** — `feat/fix: 설명 (#이슈번호)`
4. **PR → dev 머지** — `gh pr create --base dev` → `gh pr merge`
5. **PR → main 머지** — `gh pr create --base main --head dev` → `gh pr merge`
6. **이슈 코멘트** — 변경 내용 정리 후 `gh issue comment`
7. **이슈 close** — `gh issue close`

## Response Style

- **Length**: 300자 이내로 간결하게 답변한다.
- **Format**: 수치 비교는 표, 흐름 설명은 도형/다이어그램, 시각 요소를 적극 활용한다.

## Behavior Constraints

- **Scope**: change only what the task requires — no unrelated refactors, no drive-by formatting, no new docs unless asked.
- **No speculation**: no extra error handling, helpers, or abstractions for hypothetical future use.
- **No backwards-compat hacks**: no `_unused` renames, re-exported types, or `// removed` comments.
- **Responses**: concise — no trailing summary paragraphs after making an edit.
- **Git**: only commit when explicitly asked; create new commits (never amend without being asked); never use `--no-verify`; never use interactive flags (`-i`).
- **Destructive actions**: confirm before `reset --hard`, `push --force`, deleting files/branches, or anything hard to reverse.
- **Security**: never introduce command injection, XSS, SQL injection, or OWASP top-10 vulnerabilities; never hardcode secrets.

## Verification (run after non-trivial changes)

- **Backend**: `cd backend && pytest`
- **Expo app**: `cd frontendapp/costview && npm test`
- **costview_LLM**: `cd costview_LLM && pnpm test`

Explain why you cannot run them (e.g. missing secrets) if that is the case.
