---
name: agent-state
description: Manage the project's DuckDB state ledger (.agent/state.duckdb) - features, validation contract, sprint steps and the append-only execution log. Use when bootstrapping a session, logging an action (init gen eval fix sync done err), updating a feature status or sprint step, marking contract criteria passed, or searching the project history. Replaces the legacy 4-file markdown ledger and migrates it automatically on first bootstrap.
---

# agent-state - one DuckDB ledger per project

Work state lives in a single DuckDB database, `.agent/state.duckdb`, managed only
through this CLI: features, validation contract, sprint objective and milestones,
append-only execution log. It replaces the legacy 4-file markdown/JSON ledger
(`feature_list*.json`, `contract.md`, `progress.md`, `log.md` + `docs/journal/`
archives), which `bootstrap` migrates automatically (with backup) when detected.

## Invocation

```bash
uv run --no-project .agents/skills/agent-state/scripts/state_agents.py [--repo PATH] <command>
```

- The dependency (`duckdb>=1.1.0`) is declared in the script's PEP 723 header:
  uv builds and caches an isolated environment on first use (~1-2 s afterwards).
  No global install, no virtualenv to manage, works on fresh clones and CI.
- Plain `python <script>` also works wherever duckdb is already importable.
- In the agents-kit repository itself the canonical copy is
  `scripts/state_agents.py`; the copy shipped here is byte-identical
  (test-enforced mirror).

## Commands

| Command | Effect |
|---|---|
| `bootstrap` | Bounded state: active features (`!= completed`), sprint, contract + test command, **last 20 log entries**. Auto-runs `migrate --backup` when the database is absent and a legacy ledger is detected. |
| `migrate [--backup]` | Import the legacy 4-file ledger + `docs/journal/log_*.md` in ONE transaction. `--backup` moves the sources to `.agent/legacy_markdown_backup/` and adds `.agent/*.duckdb.wal` to `.gitignore`. Archived ids colliding with reused active ids are re-keyed `AA-<id>` — never dropped. |
| `log <type> "<message>"` | Append an entry; type ∈ `init gen eval fix sync done err`; budget ~200 chars (warned, kept). |
| `feature add <id> <name> <desc> [--deps F-01,F-02]` | Create a feature (`pending`). |
| `feature status <id> <pending\|in_progress\|completed>` | Change a feature status. |
| `step add <objective\|milestone> "<description>"` | Add a sprint step. |
| `step done <id>` | Mark a sprint step done. |
| `step reset` | Clear the sprint table (start a new sprint). |
| `contract add "<criterion>"` | Append a validation criterion (frozen once coding starts). |
| `contract pass <id>` | Mark a criterion passed (evidence first: command run, exit code). |
| `contract cmd "<command>"` | Record the test command in `contract_meta`. |
| `search-log "<query>" [--limit N]` | Case-insensitive search through the whole log (replaces grepping archives). |
| `export-md` | Regenerate `.agent/DASHBOARD.md`, a read-only summary for humans. |

## Workflow (the 4 operational directives)

1. **Bootstrap** - on every session start, crash or restart, run `bootstrap`.
   It guarantees a bounded context; never query the full history unfiltered -
   use `search-log` for targeted lookups instead.
2. **Action** - log at the start and at the end of each action:
   `log init|gen|eval|fix|sync|done|err "<one line>"`.
3. **Sync** - immediately after each write or test, update the matching state:
   `feature status`, `step done`, `contract pass`.
4. **Errors** - on exception or interruption, run `bootstrap` again: the last
   committed transaction is the valid state.

## Hard rules

- `.agent/state.duckdb` is the single source of truth: commit it to git
  (binary; single-writer fleet). Only `.agent/*.duckdb.wal` is git-ignored.
- The execution log is append-only; never rewrite or delete entries.
- The contract is frozen before the first line of code; a scope change means a
  new contract approved by the user, not silent edits.
- Connections are ephemeral (opened and closed per command): never hold one
  open, never two writers at once.
- Output is ASCII and concise on purpose (token budget); details go in commits.
