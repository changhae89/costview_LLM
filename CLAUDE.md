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

## Shared Rules

- Git workflow, response style, stack rules, and test policy are defined in `AGENTS.md`.
- When guidance conflicts, follow `AGENTS.md` as the single project source of truth.

## Behavior Constraints

Claude Code-specific rules (project-wide rules are in `AGENTS.md`):

- **No speculation**: no extra error handling, helpers, or abstractions for hypothetical future use.
- **No backwards-compat hacks**: no `_unused` renames, re-exported types, or `// removed` comments.
- **Responses**: no trailing summary paragraphs after making an edit (response style is in `AGENTS.md`).
- **Git**: only commit when explicitly asked; create new commits (never amend without being asked); never use `--no-verify`; never use interactive flags (`-i`).
- **Destructive actions**: confirm before `reset --hard`, `push --force`, deleting files/branches, or anything hard to reverse.

## Verification (run after non-trivial changes)

- Use the canonical verification entrypoints in `AGENTS.md`.
- If verification cannot run (e.g. missing secrets), explain why.
