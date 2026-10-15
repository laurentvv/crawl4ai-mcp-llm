#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.1.0"]
# ///
"""agent-state - one DuckDB ledger per project (features, contract, sprint, log).

Usage:
    uv run --no-project .agents/skills/agent-state/scripts/state_agents.py [--repo PATH] <command>

The dependency (duckdb) is declared in the PEP 723 header above: uv builds and
caches an isolated environment, no global install is needed. The database is
.agent/state.duckdb; connections are ephemeral (opened and closed per command)
so nothing holds a lock on the file. All output is ASCII.

Commands:
    bootstrap                           bounded state: active features, sprint, contract,
                                        last 20 log entries; auto-migrates a legacy 4-file
                                        ledger (with backup) when the database is absent
    migrate [--backup]                  import legacy feature_list*.json, contract.md,
                                        progress.md, log.md and docs/journal/log_*.md in
                                        ONE transaction; --backup archives the sources into
                                        .agent/legacy_markdown_backup/ and adds the WAL
                                        line to .gitignore
    log <type> "<message>"              append an entry (type: init gen eval fix sync done err)
    feature add <id> <name> <desc> [--deps F-01,F-02]
    feature status <id> <status>        pending | in_progress | completed
    step add <objective|milestone> "<description>"
    step done <id>                      mark a sprint step done
    step reset                          clear the sprint table (new sprint)
    contract add "<criterion>"          append a validation criterion
    contract pass <id>                  mark a criterion passed
    contract cmd "<command>"            record the test command
    search-log "<query>" [--limit N]    case-insensitive search through the log
    export-md                           regenerate .agent/DASHBOARD.md (read-only summary)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

try:
    import duckdb
except ImportError:  # pragma: no cover - hint only, uv handles the install
    print("duckdb is required: run this script through 'uv run --no-project <script>'"
          " (the PEP 723 header declares the dependency).")
    raise

# Legacy ledger detection mirrors sync_agents.py LEDGER_LOCATIONS.
DB_REL = Path(".agent") / "state.duckdb"
BACKUP_REL = Path(".agent") / "legacy_markdown_backup"
DASHBOARD_REL = Path(".agent") / "DASHBOARD.md"
WAL_LINE = ".agent/*.duckdb.wal"
LEGACY_LOCATIONS = (".", ".agents", "memory-bank")
LEGACY_FILES = ("feature_list.json", "feature_list_archive.json", "contract.md", "progress.md", "log.md")
JOURNAL_DIR = Path("docs") / "journal"

FEATURE_STATUSES = ("pending", "in_progress", "completed")
LOG_TYPES = ("init", "gen", "eval", "fix", "sync", "done", "err")
STEP_CATEGORIES = ("objective", "milestone")
ENTRY_BUDGET = 200
BOOTSTRAP_LOG_LINES = 20

LOG_ENTRY_RE = re.compile(r"^##\s*\[(\d{4}-\d{2}-\d{2})\]\s*(" + "|".join(LOG_TYPES) + r")\s*\|\s*(.+)$")
CHECKBOX_RE = re.compile(r"^[-*]\s+\[([ xX])\]\s*(.+)$")
TEST_CMD_EN_RE = re.compile(r"^\*\s*Test command:\s*`([^`]+)`")

# Legacy French headings (kit v1.x wrote French ledgers). Built from code points
# so that this source file holds no accented character and no French word.
_E9 = chr(0xE9)
FR_TEST_CMD_PREFIX = "* Commande d'ex" + _E9 + "cution d" + "es tests"
FR_TEST_CMD_RE = re.compile(re.escape(FR_TEST_CMD_PREFIX) + r"\s*:\s*`([^`]+)`")
FR_GOAL = "Objectif Actuel"
FR_MILESTONES = "Jalons de l'It" + _E9 + "ration"
GOAL_ALIASES = ("Current Goal", FR_GOAL)
MILESTONE_ALIASES = ("Iteration Milestones", FR_MILESTONES)


class InputError(Exception):
    """Unusable input: message printed as-is, exit code 2."""


# ------------------------------------------------------------------ helpers

def read_text(p: Path) -> str:
    """UTF-8 text (BOM tolerated), line endings normalized to LF."""
    return p.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def write_text(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8", newline="\n")


def local_today() -> date:
    """Today's date in the machine's time zone (the one writing the log)."""
    return datetime.now().astimezone().date()


def db_path(repo: Path) -> Path:
    return repo / DB_REL


def normalize_title(line: str) -> str:
    """Heading title, casefolded, typographic apostrophes folded to ASCII."""
    title = line.lstrip("#").strip()
    return title.replace(chr(8217), "'").casefold()


def init_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("CREATE SEQUENCE IF NOT EXISTS seq_contract_criteria")
    con.execute("CREATE SEQUENCE IF NOT EXISTS seq_sprint_progress")
    con.execute("CREATE SEQUENCE IF NOT EXISTS seq_execution_log")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS features (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            description VARCHAR,
            status VARCHAR CHECK (status IN ('pending', 'in_progress', 'completed')),
            dependencies VARCHAR[],
            updated_at TIMESTAMP DEFAULT current_timestamp)
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS contract_meta (
            key VARCHAR PRIMARY KEY,
            value VARCHAR)
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS contract_criteria (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_contract_criteria'),
            criterion VARCHAR NOT NULL,
            passed BOOLEAN DEFAULT FALSE,
            locked BOOLEAN DEFAULT TRUE)
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS sprint_progress (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_sprint_progress'),
            category VARCHAR CHECK (category IN ('objective', 'milestone')),
            description VARCHAR NOT NULL,
            done BOOLEAN DEFAULT FALSE)
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS execution_log (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_execution_log'),
            log_date VARCHAR NOT NULL,
            action VARCHAR CHECK (action IN
                ('init', 'gen', 'eval', 'fix', 'sync', 'done', 'err')),
            message VARCHAR NOT NULL,
            created_at TIMESTAMP DEFAULT current_timestamp)
        """
    )


def open_db(repo: Path) -> duckdb.DuckDBPyConnection:
    """Ephemeral connection: caller keeps it inside a with-block only."""
    db = db_path(repo)
    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    init_schema(con)
    return con


def find_legacy(repo: Path) -> list[Path]:
    """Existing legacy ledger files, in the three historical locations."""
    found: list[Path] = []
    for loc in LEGACY_LOCATIONS:
        base = repo / loc
        for name in LEGACY_FILES:
            if (base / name).is_file():
                found.append(base / name)
    return found


def journal_log_files(repo: Path) -> list[Path]:
    """docs/journal/log_*.md sorted by name (name sort is chronological)."""
    journal = repo / JOURNAL_DIR
    if not journal.is_dir():
        return []
    return sorted(journal.glob("log_*.md"), key=lambda p: p.name)


# ------------------------------------------------------- legacy parsers

def parse_features(path: Path) -> list[dict]:
    """Feature dicts from {"features": [...]} or a bare list (archive tolerance)."""
    data = json.loads(read_text(path))
    if isinstance(data, dict):
        data = data.get("features", [])
    if not isinstance(data, list):
        raise InputError(f"{path.name}: expected an object with a features list, or a bare list")
    return [f for f in data if isinstance(f, dict)]


def parse_contract(path: Path) -> tuple[list[tuple[bool, str]], str | None]:
    """(criteria as (passed, text), test command or None) from a contract.md."""
    criteria: list[tuple[bool, str]] = []
    command = None
    for line in read_text(path).split("\n"):
        m = CHECKBOX_RE.match(line)
        if m:
            criteria.append((m.group(1) in "xX", m.group(2).strip()))
            continue
        if command is None:
            men = TEST_CMD_EN_RE.match(line)
            if men:
                command = men.group(1)
                continue
            mfr = FR_TEST_CMD_RE.match(line)
            if mfr:
                command = mfr.group(1)
    return criteria, command


def parse_progress(path: Path) -> list[tuple[str, bool, str]]:
    """Sprint rows as (category, done, description) from a progress.md."""
    rows: list[tuple[str, bool, str]] = []
    category: str | None = None
    for line in read_text(path).split("\n"):
        if line.startswith("#"):
            title = normalize_title(line)
            if any(title == alias.casefold() for alias in GOAL_ALIASES):
                category = "objective"
            elif any(title == alias.casefold() for alias in MILESTONE_ALIASES):
                category = "milestone"
            else:
                category = None
            continue
        if category is None:
            continue
        m = CHECKBOX_RE.match(line)
        if m:
            rows.append((category, m.group(1) in "xX", m.group(2).strip()))
    return rows


def parse_log_file(path: Path) -> tuple[list[tuple[str, str, str]], int]:
    """((date, type, message) rows, count of skipped '## ' heading lines)."""
    rows: list[tuple[str, str, str]] = []
    skipped = 0
    for line in read_text(path).split("\n"):
        if not line.startswith("## "):
            continue
        m = LOG_ENTRY_RE.match(line)
        if m:
            rows.append((m.group(1), m.group(2), m.group(3).strip()))
        else:
            skipped += 1
    return rows, skipped


# ---------------------------------------------------------------- commands

def cmd_bootstrap(repo: Path) -> int:
    if not repo.is_dir():
        print(f"FOLDER NOT FOUND: {repo}")
        return 2
    db = db_path(repo)
    if not db.exists():
        legacy = find_legacy(repo) + journal_log_files(repo)
        if legacy:
            print("LEGACY LEDGER DETECTED: migrating first (backup kept)...")
            rc = cmd_migrate(repo, backup=True)
            if rc:
                return rc
    with open_db(repo) as con:
        legacy_left = find_legacy(repo) + journal_log_files(repo)
        if legacy_left:
            print(f"NOTE: legacy files still present ({len(legacy_left)}) -"
                  " 'migrate --backup' archives them.")
        print(format_state(con))
    return 0


def format_state(con: duckdb.DuckDBPyConnection) -> str:
    out: list[str] = []

    features = con.execute(
        "SELECT id, name, status, dependencies FROM features"
        " WHERE status != 'completed' ORDER BY id").fetchall()
    total = con.execute("SELECT count(*) FROM features").fetchone()[0]
    out.append(f"FEATURES {len(features)} active / {total}")
    for fid, name, status, deps in features:
        dep_txt = f" deps:{','.join(deps)}" if deps else ""
        out.append(f" [{status}] {fid} {name}{dep_txt}")

    sprint = con.execute(
        "SELECT id, category, done, description FROM sprint_progress"
        " ORDER BY category DESC, id").fetchall()
    done_n = sum(1 for _, _, d, _ in sprint if d)
    out.append(f"SPRINT {done_n}/{len(sprint)} done")
    for sid, category, done, desc in sprint:
        tag = "OBJ" if category == "objective" else "MILE"
        out.append(f" [{'x' if done else ' '}] {sid} {tag} {desc}")

    command = con.execute(
        "SELECT value FROM contract_meta WHERE key = 'test_command'").fetchone()
    criteria = con.execute(
        "SELECT id, passed, criterion FROM contract_criteria ORDER BY id").fetchall()
    passed_n = sum(1 for _, p, _ in criteria if p)
    cmd_txt = f" cmd:{command[0]}" if command else ""
    out.append(f"CONTRACT {passed_n}/{len(criteria)} passed{cmd_txt}")
    for cid, passed, criterion in criteria:
        if not passed:
            out.append(f" [ ] {cid} {criterion}")

    total_log = con.execute("SELECT count(*) FROM execution_log").fetchone()[0]
    logs = con.execute(
        "SELECT log_date, action, message FROM execution_log"
        f" ORDER BY id DESC LIMIT {BOOTSTRAP_LOG_LINES}").fetchall()
    out.append(f"LOG last {len(logs)} of {total_log}")
    for log_date, action, message in reversed(logs):
        out.append(f" {log_date} {action} | {message}")
    return "\n".join(out)


def cmd_migrate(repo: Path, backup: bool) -> int:
    if not repo.is_dir():
        print(f"FOLDER NOT FOUND: {repo}")
        return 2
    ledger_files = find_legacy(repo)
    logs_files = journal_log_files(repo)
    current_log = [p for p in ledger_files if p.name == "log.md"]
    sources = ledger_files + logs_files
    if not sources:
        print("NOTHING TO MIGRATE: no legacy ledger file found"
              f" (looked in {', '.join(LEGACY_LOCATIONS)} and {JOURNAL_DIR.as_posix()}).")
        return 0 if db_path(repo).exists() else 2

    db = db_path(repo)
    db_existed = db.exists()
    warnings: list[str] = []
    counts = {"features": 0, "criteria": 0, "steps": 0, "log": 0}
    skipped_headings = 0
    try:
        with open_db(repo) as con:
            if con.execute("SELECT count(*) FROM execution_log").fetchone()[0]:
                warnings.append(
                    "execution_log already holds rows: re-running without --backup duplicates them")
            con.execute("BEGIN TRANSACTION")
            try:
                # 1. features. Active ids are collected first: a repository may reuse
                #    an id across sprints, and a single primary-key table cannot hold
                #    both rows - colliding archived rows are re-keyed "AA-<id>"
                #    (the kit archive prefix), never silently dropped. The archive is
                #    inserted before the active file so active data wins same-id
                #    duplicates inside the active set.
                active_ids: set[str] = set()
                active_rows: list[tuple[Path, dict]] = []
                for path in [p for p in ledger_files if p.name == "feature_list.json"]:
                    for feature in parse_features(path):
                        active_ids.add(str(feature.get("id", "")))
                        active_rows.append((path, feature))
                for name in ("feature_list_archive.json", "feature_list.json"):
                    rows = (active_rows if name == "feature_list.json"
                            else [(path, f) for path in ledger_files if path.name == name
                                  for f in parse_features(path)])
                    for path, feature in rows:
                        fid = str(feature.get("id", ""))
                        insert_id = fid
                        if name == "feature_list_archive.json" and fid in active_ids:
                            insert_id = "AA-" + fid
                            suffix = 2
                            while insert_id in active_ids:
                                insert_id = f"AA-{fid}-{suffix}"
                                suffix += 1
                            warnings.append(
                                f"{path.name} {fid}: id reused across sprints,"
                                f" archived row re-keyed {insert_id}")
                        status = feature.get("status")
                        if status not in FEATURE_STATUSES:
                            warnings.append(
                                f"{path.name} {fid}: status '{status}' coerced to 'pending'")
                            status = "pending"
                        deps = feature.get("dependencies", [])
                        if not isinstance(deps, list):
                            deps = []
                        con.execute(
                            "INSERT OR REPLACE INTO features"
                            " (id, name, description, status, dependencies) VALUES (?, ?, ?, ?, ?)",
                            [insert_id, str(feature.get("name", "")),
                             str(feature.get("description", "")), status,
                             [str(d) for d in deps]],
                        )
                        counts["features"] += 1
                        active_ids.add(insert_id)
                # 2. contract.
                for path in [p for p in ledger_files if p.name == "contract.md"]:
                    criteria, command = parse_contract(path)
                    for passed, criterion in criteria:
                        con.execute(
                            "INSERT INTO contract_criteria (criterion, passed) VALUES (?, ?)",
                            [criterion, passed])
                        counts["criteria"] += 1
                    if command:
                        con.execute(
                            "INSERT OR REPLACE INTO contract_meta (key, value)"
                            " VALUES ('test_command', ?)", [command])
                # 3. sprint progress.
                for path in [p for p in ledger_files if p.name == "progress.md"]:
                    for category, done, desc in parse_progress(path):
                        con.execute(
                            "INSERT INTO sprint_progress (category, description, done)"
                            " VALUES (?, ?, ?)", [category, desc, done])
                        counts["steps"] += 1
                # 4. logs: journal archives in name order, then the live log.md.
                for path in logs_files + current_log:
                    rows, skipped = parse_log_file(path)
                    skipped_headings += skipped
                    for log_date, action, message in rows:
                        con.execute(
                            "INSERT INTO execution_log (log_date, action, message)"
                            " VALUES (?, ?, ?)", [log_date, action, message])
                        counts["log"] += 1
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise
    except (InputError, json.JSONDecodeError, OSError, duckdb.Error) as e:
        # A failed migration leaves no half-state: data rolled back; a database we
        # just created is removed so the repository sits exactly where it started.
        for suffix in ("", ".wal"):
            wal = Path(str(db) + suffix)
            if not db_existed and wal.exists():
                wal.unlink()
        print(f"MIGRATION FAILED (rolled back, sources untouched): {e}")
        return 1

    print(f"MIGRATED into {DB_REL.as_posix()}: {counts['features']} features,"
          f" {counts['criteria']} criteria, {counts['steps']} steps, {counts['log']} log entries.")
    if skipped_headings:
        warnings.append(f"{skipped_headings} '## ' heading line(s) skipped (non-standard format)")
    for w in warnings:
        print(f"WARNING: {w}")
    if not backup:
        print("Sources kept in place (re-run without --backup duplicates log entries).")
        return 0
    return backup_legacy(repo, ledger_files)


def backup_legacy(repo: Path, ledger_files: list[Path]) -> int:
    moved: list[str] = []
    failures: list[str] = []
    targets: list[Path] = list(dict.fromkeys(ledger_files))
    journal = repo / JOURNAL_DIR
    if journal.is_dir():
        targets.append(journal)
    for src in targets:
        dest = repo / BACKUP_REL / src.relative_to(repo)
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                failures.append(f"{src.relative_to(repo)} -> backup target already exists")
                continue
            shutil.move(str(src), str(dest))
            moved.append(src.relative_to(repo).as_posix())
        except OSError as e:
            failures.append(f"{src.relative_to(repo)}: {e}")
    for rel in moved:
        print(f"BACKED UP: {rel} -> {BACKUP_REL.as_posix()}/")
    rc = add_wal_ignore_line(repo)
    if failures:
        for f in failures:
            print(f"WARNING: not moved: {f}")
        return 1
    return rc


def add_wal_ignore_line(repo: Path) -> int:
    gi = repo / ".gitignore"
    try:
        lines = read_text(gi).split("\n") if gi.is_file() else []
    except UnicodeDecodeError:
        print(f"WARNING: {gi} is not UTF-8 - add '{WAL_LINE}' by hand")
        return 1
    if WAL_LINE in lines:
        return 0
    text = "\n".join(lines)
    if lines and lines[-1].strip():
        text += "\n"
    text += WAL_LINE + "\n"
    write_text(gi, text)
    print(f"GITIGNORE: added '{WAL_LINE}'")
    return 0


def cmd_log(repo: Path, type_: str, message: str) -> int:
    if type_ not in LOG_TYPES:
        print(f"INVALID TYPE: {type_} (expected one of: {' '.join(LOG_TYPES)})")
        return 1
    if len(message) > ENTRY_BUDGET:
        print(f"WARNING: {len(message)}-character entry (budget ~{ENTRY_BUDGET},"
              " details go in the commit)")
    with open_db(repo) as con:
        con.execute("INSERT INTO execution_log (log_date, action, message) VALUES (?, ?, ?)",
                    [local_today().isoformat(), type_, message])
        total = con.execute("SELECT count(*) FROM execution_log").fetchone()[0]
    print(f"LOGGED ({total} entries)")
    return 0


def cmd_feature_add(repo: Path, fid: str, name: str, description: str, deps: str) -> int:
    dep_list = [d.strip() for d in deps.split(",") if d.strip()] if deps else []
    with open_db(repo) as con:
        if con.execute("SELECT 1 FROM features WHERE id = ?", [fid]).fetchone():
            print(f"DUPLICATE ID: {fid} already exists")
            return 1
        con.execute(
            "INSERT INTO features (id, name, description, status, dependencies)"
            " VALUES (?, ?, ?, 'pending', ?)", [fid, name, description, dep_list])
    print(f"ADDED {fid} (pending)")
    return 0


def cmd_feature_status(repo: Path, fid: str, status: str) -> int:
    if status not in FEATURE_STATUSES:
        print(f"INVALID STATUS: {status} (expected one of: {' '.join(FEATURE_STATUSES)})")
        return 1
    with open_db(repo) as con:
        cur = con.execute("UPDATE features SET status = ?, updated_at = current_timestamp"
                          " WHERE id = ?", [status, fid])
        if cur.fetchone()[0] == 0 and con.execute(
                "SELECT 1 FROM features WHERE id = ?", [fid]).fetchone() is None:
            print(f"UNKNOWN ID: {fid}")
            return 1
    print(f"{fid} -> {status}")
    return 0


def cmd_step_add(repo: Path, category: str, description: str) -> int:
    if category not in STEP_CATEGORIES:
        print(f"INVALID CATEGORY: {category} (expected one of: {' '.join(STEP_CATEGORIES)})")
        return 1
    with open_db(repo) as con:
        con.execute("INSERT INTO sprint_progress (category, description) VALUES (?, ?)",
                    [category, description])
        sid = con.execute("SELECT max(id) FROM sprint_progress").fetchone()[0]
    print(f"STEP {sid} added ({category})")
    return 0


def cmd_step_done(repo: Path, sid: int) -> int:
    with open_db(repo) as con:
        changed = con.execute("UPDATE sprint_progress SET done = TRUE WHERE id = ?",
                              [sid]).fetchone()[0]
        if not changed:
            print(f"UNKNOWN ID: {sid}")
            return 1
    print(f"STEP {sid} done")
    return 0


def cmd_step_reset(repo: Path) -> int:
    with open_db(repo) as con:
        removed = con.execute("DELETE FROM sprint_progress").fetchone()[0]
    print(f"SPRINT CLEARED ({removed} step(s) removed)")
    return 0


def cmd_contract_add(repo: Path, criterion: str) -> int:
    with open_db(repo) as con:
        con.execute("INSERT INTO contract_criteria (criterion) VALUES (?)", [criterion])
        cid = con.execute("SELECT max(id) FROM contract_criteria").fetchone()[0]
    print(f"CRITERION {cid} added")
    return 0


def cmd_contract_pass(repo: Path, cid: int) -> int:
    with open_db(repo) as con:
        changed = con.execute("UPDATE contract_criteria SET passed = TRUE WHERE id = ?",
                              [cid]).fetchone()[0]
        if not changed:
            print(f"UNKNOWN ID: {cid}")
            return 1
    print(f"CRITERION {cid} passed")
    return 0


def cmd_contract_cmd(repo: Path, command: str) -> int:
    with open_db(repo) as con:
        con.execute("INSERT OR REPLACE INTO contract_meta (key, value)"
                    " VALUES ('test_command', ?)", [command])
    print(f"TEST COMMAND: {command}")
    return 0


def cmd_search_log(repo: Path, query: str, limit: int) -> int:
    with open_db(repo) as con:
        rows = con.execute(
            "SELECT id, log_date, action, message FROM execution_log"
            " WHERE message ILIKE ? ORDER BY id DESC LIMIT ?", [f"%{query}%", limit]).fetchall()
        total = con.execute("SELECT count(*) FROM execution_log WHERE message ILIKE ?",
                            [f"%{query}%"]).fetchone()[0]
    for cid, log_date, action, message in reversed(rows):
        print(f" {cid} {log_date} {action} | {message}")
    print(f"MATCHES {len(rows)} shown of {total}")
    return 0


def cmd_export_md(repo: Path) -> int:
    with open_db(repo) as con:
        content = format_state(con)
    lines = [
        "# Agent State Dashboard",
        "",
        (
            f"Generated by agent-state on {local_today().isoformat()} - read-only summary,"
            " regenerate with `export-md`."
        ),
        "",
    ]
    section = ""
    for line in content.split("\n"):
        if line.startswith(("FEATURES", "SPRINT", "CONTRACT", "LOG ")):
            section = line.split()[0].title() if not line.startswith("LOG") else "Execution Log"
            lines += ["## " + section, ""]
        lines.append(line)
    write_text(repo / DASHBOARD_REL, "\n".join(lines) + "\n")
    print(f"WROTE {DASHBOARD_REL.as_posix()}")
    return 0


# --------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="agent-state - DuckDB project ledger")
    ap.add_argument("--repo", default=".", help="target repository (default: current folder)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("bootstrap", help="bounded state + legacy auto-migration")
    m = sub.add_parser("migrate", help="import a legacy 4-file ledger (one transaction)")
    m.add_argument("--backup", action="store_true",
                   help="archive the sources into .agent/legacy_markdown_backup/ and pin the WAL ignore line")

    lg = sub.add_parser("log", help="append an execution_log entry")
    lg.add_argument("type", choices=LOG_TYPES, help="entry type")
    lg.add_argument("message", help="one line, ~200 characters max")

    fa = sub.add_parser("feature", help="features")
    fsub = fa.add_subparsers(dest="feature_cmd", required=True)
    fa1 = fsub.add_parser("add", help="create a feature (status: pending)")
    fa1.add_argument("id")
    fa1.add_argument("name")
    fa1.add_argument("description")
    fa1.add_argument("--deps", default="", help="comma-separated feature ids")
    fs = fsub.add_parser("status", help="change a feature status")
    fs.add_argument("id")
    fs.add_argument("status", choices=FEATURE_STATUSES)

    st = sub.add_parser("step", help="sprint objective and milestones")
    ssub = st.add_subparsers(dest="step_cmd", required=True)
    sa = ssub.add_parser("add", help="add a sprint step")
    sa.add_argument("category", choices=STEP_CATEGORIES)
    sa.add_argument("description")
    sd = ssub.add_parser("done", help="mark a step done")
    sd.add_argument("id", type=int)
    ssub.add_parser("reset", help="clear the sprint table (new sprint)")

    ct = sub.add_parser("contract", help="validation contract")
    csub = ct.add_subparsers(dest="contract_cmd", required=True)
    ca = csub.add_parser("add", help="append a criterion")
    ca.add_argument("criterion")
    cp = csub.add_parser("pass", help="mark a criterion passed")
    cp.add_argument("id", type=int)
    cc = csub.add_parser("cmd", help="record the test command")
    cc.add_argument("command")

    sl = sub.add_parser("search-log", help="case-insensitive search in the log")
    sl.add_argument("query")
    sl.add_argument("--limit", type=int, default=20)

    sub.add_parser("export-md", help="regenerate .agent/DASHBOARD.md")

    args = ap.parse_args(argv)
    repo = Path(args.repo).resolve()
    try:
        if args.cmd == "bootstrap":
            return cmd_bootstrap(repo)
        if args.cmd == "migrate":
            return cmd_migrate(repo, args.backup)
        if args.cmd == "log":
            return cmd_log(repo, args.type, args.message)
        if args.cmd == "feature":
            if args.feature_cmd == "add":
                return cmd_feature_add(repo, args.id, args.name, args.description, args.deps)
            return cmd_feature_status(repo, args.id, args.status)
        if args.cmd == "step":
            if args.step_cmd == "add":
                return cmd_step_add(repo, args.category, args.description)
            if args.step_cmd == "done":
                return cmd_step_done(repo, args.id)
            return cmd_step_reset(repo)
        if args.cmd == "contract":
            if args.contract_cmd == "add":
                return cmd_contract_add(repo, args.criterion)
            if args.contract_cmd == "pass":
                return cmd_contract_pass(repo, args.id)
            return cmd_contract_cmd(repo, args.command)
        if args.cmd == "search-log":
            return cmd_search_log(repo, args.query, args.limit)
        return cmd_export_md(repo)
    except InputError as e:
        print(e)
        return 2


if __name__ == "__main__":
    # Windows console / Git Bash pipe: an unrepresentable character must never crash the script.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    sys.exit(main())
