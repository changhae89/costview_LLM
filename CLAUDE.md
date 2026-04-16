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
