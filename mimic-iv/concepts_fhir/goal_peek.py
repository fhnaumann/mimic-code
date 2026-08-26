#!/usr/bin/env python3
"""Look inside the sessions a `mimic_utils goal-run` pool is driving.

A pool worker runs `opencode run --format json ...`, which prints nothing until
the turn returns, so while a concept is mid-turn there is no terminal to watch
and the pool's own `sessions/<concept>.jsonl` transcript does not exist yet.
The session is still fully observable, though: opencode persists every message
part as it arrives.  This reads that store, plus the pool ledger beside it, and
prints where each concept has got to -- including which subagent is currently
holding the turn, which is usually the thing you actually want to know.

Read-only by construction.  The database is opened `mode=ro`, nothing is
written, and no opencode command is run.  Safe against a live pool.

    ./goal_peek.py                     # one snapshot of the newest pool
    ./goal_peek.py --follow            # refresh every 20s
    ./goal_peek.py -n 25 milrinone     # deeper tail, one concept
    ./goal_peek.py --run-dir replay/1.goalrun

This reads opencode's own SQLite store, which is internal and may change shape
between versions.  If it does, `opencode export <session-id>` is the supported
equivalent and `opencode session list` still gives you the ids.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
REPLAY_DIR = HERE / "replay"

SKIP_PART_TYPES = frozenset({"step-start", "step-finish", "snapshot", "patch"})
TOOL_MARK = {"completed": " ok", "error": "ERR", "running": " ..", "pending": " ..."}


def _db_path() -> Path:
    base = os.environ.get("XDG_DATA_HOME")
    root = Path(base) if base else Path.home() / ".local" / "share"
    return root / "opencode" / "opencode.db"


def _connect(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        sys.exit(f"No opencode store at {path}")
    # mode=ro, not immutable: there is a live writer, and immutable would let us
    # read a stale snapshot of the WAL and silently miss the newest parts.
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def _rows(conn: sqlite3.Connection, sql: str, args: Sequence[Any] = ()) -> List[sqlite3.Row]:
    try:
        return list(conn.execute(sql, args))
    except sqlite3.Error as err:
        sys.exit(
            f"Could not read the opencode store ({err}).\n"
            "Its schema is internal and may have changed; use "
            "`opencode session list` and `opencode export <id>` instead."
        )


def _json(raw: Any) -> Dict[str, Any]:
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


# --------------------------------------------------------------------------- #
# ledger
# --------------------------------------------------------------------------- #


def _read_ledger(path: Path) -> Optional[Dict[str, Any]]:
    """The pool ledger, which is replaced atomically so it cannot tear."""
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _pick_run_dir(explicit: Optional[str]) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            path = Path.cwd() / path
        return path.resolve()
    candidates = sorted(
        (p for p in REPLAY_DIR.glob("*.goalrun") if (p / "ledger.json").is_file()),
        key=lambda p: (p / "ledger.json").stat().st_mtime,
    )
    if not candidates:
        sys.exit(f"No pool ledger under {REPLAY_DIR} -- pass --run-dir")
    return candidates[-1]


# --------------------------------------------------------------------------- #
# sessions
# --------------------------------------------------------------------------- #


def _find_session(conn: sqlite3.Connection, concept: str, scan: int) -> Optional[str]:
    """The session a pool worker opened for *concept*, found by its first part.

    The ledger only learns a session id once a turn returns, so a concept still
    in its first turn has none recorded.  Match on the opening message instead:
    the pool sends the bare concept stem and nothing else, which is exactly what
    `/goal <concept>` expands to.  That is an exact match on text the pool
    controls, unlike the model-generated session title.
    """
    rows = _rows(
        conn,
        """
        SELECT id FROM session
         WHERE directory = ? AND parent_id IS NULL
         ORDER BY time_updated DESC LIMIT ?
        """,
        (str(REPO_ROOT), scan),
    )
    for row in rows:
        first = _rows(
            conn,
            "SELECT data FROM part WHERE session_id = ? ORDER BY time_created LIMIT 1",
            (row["id"],),
        )
        if not first:
            continue
        part = _json(first[0]["data"])
        if part.get("type") == "text" and (part.get("text") or "").strip() == concept:
            return row["id"]
    return None


def _session_info(conn: sqlite3.Connection, session_id: str) -> Optional[sqlite3.Row]:
    rows = _rows(
        conn,
        """
        SELECT id, title, agent, model, cost, tokens_input, tokens_output,
               time_updated
          FROM session WHERE id = ?
        """,
        (session_id,),
    )
    return rows[0] if rows else None


def _parts(conn: sqlite3.Connection, session_id: str, limit: int) -> List[Dict[str, Any]]:
    """The newest *limit* interesting parts of a session, oldest first."""
    rows = _rows(
        conn,
        """
        SELECT data, time_updated FROM part
         WHERE session_id = ? ORDER BY time_created DESC LIMIT ?
        """,
        # Over-fetch: the bookkeeping types we drop are roughly half of them.
        (session_id, limit * 4),
    )
    kept: List[Dict[str, Any]] = []
    for row in rows:
        part = _json(row["data"])
        if part.get("type") in SKIP_PART_TYPES or not part:
            continue
        part["_at"] = row["time_updated"]
        kept.append(part)
        if len(kept) >= limit:
            break
    return list(reversed(kept))


def _child_session(part: Dict[str, Any]) -> Optional[str]:
    """The subagent session a `task` tool part spawned, if it has one."""
    if part.get("type") != "tool" or part.get("tool") != "task":
        return None
    meta = (part.get("state") or {}).get("metadata") or {}
    child = meta.get("sessionId")
    return child if isinstance(child, str) else None


# --------------------------------------------------------------------------- #
# formatting
# --------------------------------------------------------------------------- #


def _oneline(text: str, width: int) -> str:
    flat = " ".join(str(text).split())
    return flat if len(flat) <= width else flat[: width - 1] + "…"


def _hms(seconds: float) -> str:
    seconds = int(max(seconds, 0))
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m{seconds % 60:02d}s"
    return f"{seconds // 3600}h{(seconds % 3600) // 60:02d}m"


def _ago_ms(epoch_ms: Optional[int]) -> str:
    if not epoch_ms:
        return "-"
    return _hms(time.time() - epoch_ms / 1000.0) + " ago"


def _ago_iso(stamp: Optional[str]) -> str:
    if not stamp:
        return "-"
    try:
        when = datetime.fromisoformat(stamp)
    except ValueError:
        return stamp
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return _hms((datetime.now(timezone.utc) - when).total_seconds()) + " ago"


def _clock(epoch_ms: Optional[int]) -> str:
    if not epoch_ms:
        return "  --:--:--"
    return datetime.fromtimestamp(epoch_ms / 1000.0).strftime("%H:%M:%S")


def _tool_detail(part: Dict[str, Any]) -> str:
    state = part.get("state") or {}
    args = state.get("input") or {}
    if isinstance(state.get("title"), str) and state["title"].strip():
        return state["title"]
    for key in ("command", "filePath", "pattern", "description", "prompt", "path"):
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _part_line(part: Dict[str, Any], width: int) -> str:
    when = _clock(part.get("_at"))
    kind = part.get("type")
    if kind == "text":
        return f"{when}  say   {_oneline(part.get('text') or '', width)}"
    if kind == "reasoning":
        return f"{when}  think {_oneline(part.get('text') or '', width - 40)}"
    if kind == "tool":
        state = part.get("state") or {}
        mark = TOOL_MARK.get(state.get("status", ""), state.get("status", "?"))
        name = part.get("tool") or "?"
        return (
            f"{when}  {mark} {name:<10} {_oneline(_tool_detail(part), width - 20)}"
        )
    return f"{when}  {str(kind):<5} {_oneline(json.dumps(part)[:200], width - 20)}"


def _workers() -> Dict[str, Tuple[str, str]]:
    """Live `opencode run` workers, keyed by their trailing argv token.

    On turn 0 that token is the concept stem; on later turns the pool passes a
    continuation prompt and carries --session, so both keys are looked up.
    """
    try:
        out = subprocess.run(
            ["ps", "-ax", "-o", "pid=,etime=,command="],
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return {}
    live: Dict[str, Tuple[str, str]] = {}
    for line in out.splitlines():
        if "opencode run" not in line:
            continue
        fields = line.split()
        if len(fields) < 3:
            continue
        argv = fields[2:]
        live[argv[-1]] = (fields[0], fields[1])
        if "--session" in argv:
            index = argv.index("--session")
            if index + 1 < len(argv):
                live[argv[index + 1]] = (fields[0], fields[1])
    return live


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #


def _print_session(
    conn: sqlite3.Connection,
    session_id: str,
    tail: int,
    width: int,
    indent: str,
    show_children: bool,
) -> None:
    info = _session_info(conn, session_id)
    if info is None:
        print(f"{indent}(session {session_id} is not in the store)")
        return

    meta = [session_id, f"agent {info['agent'] or '?'}"]
    if info["tokens_input"] or info["tokens_output"]:
        meta.append(f"tok in {info['tokens_input']} out {info['tokens_output']}")
    if info["cost"]:
        meta.append(f"${info['cost']:.2f}")
    meta.append(f"last part {_ago_ms(info['time_updated'])}")
    print(f"{indent}{'  '.join(meta)}")

    parts = _parts(conn, session_id, tail)
    if not parts:
        print(f"{indent}(no parts yet)")
        return

    for part in parts:
        print(f"{indent}{_part_line(part, width)}")

    if not show_children:
        return

    # The last task tool is where the turn actually is: the orchestrator spends
    # most of a port waiting on a subagent, so its own tail goes quiet while the
    # child is the only thing moving.
    for part in reversed(parts):
        child = _child_session(part)
        if not child:
            continue
        state = (part.get("state") or {}).get("status")
        label = "running" if state in ("running", "pending") else str(state)
        print(f"{indent}  └─ {part.get('tool')} [{label}] -> subagent:")
        _print_session(conn, child, max(tail // 2, 4), width - 4, indent + "     ", False)
        break


def report(
    conn: sqlite3.Connection,
    run_dir: Path,
    only: Iterable[str],
    tail: int,
    scan: int,
    width: int,
    cache: Dict[str, str],
) -> None:
    ledger = _read_ledger(run_dir / "ledger.json")
    if ledger is None:
        print(f"ledger not readable: {run_dir / 'ledger.json'}")
        return

    wanted = set(only)
    runs = [r for r in ledger.get("runs", []) if not wanted or r.get("concept") in wanted]
    live = _workers()

    print(
        f"== pool '{ledger.get('wave', '?')}'  {run_dir}\n"
        f"   {datetime.now().strftime('%H:%M:%S')}, ledger updated "
        f"{_ago_iso(ledger.get('updated_at'))}, {len(runs)} concept(s)"
    )
    print()

    for run in runs:
        concept = run.get("concept", "?")
        phase = run.get("phase", "?")
        session_id = run.get("session_id") or cache.get(concept)

        bits = [f"turn {run.get('turns', 0)}"]
        for key, label in (("outcome", "outcome"), ("status", "state")):
            if run.get(key):
                bits.append(f"{label} {run[key]}")
        if run.get("seconds"):
            bits.append(f"took {_hms(run['seconds'])}")
        worker = live.get(concept) or (live.get(session_id) if session_id else None)
        if worker:
            bits.append(f"pid {worker[0]} up {worker[1]}")
        if run.get("error"):
            bits.append(f"error {_oneline(run['error'], 60)}")
        print(f"-- {concept:<24} {phase:<9} {', '.join(bits)}")

        # A finished concept is summarised by its ledger line; naming it on the
        # command line is the way to ask for the transcript anyway.
        if phase in ("terminal", "skipped", "queued") and not wanted:
            continue

        if not session_id:
            session_id = _find_session(conn, concept, scan)
            if session_id:
                cache[concept] = session_id
        if not session_id:
            print("     (no session yet -- the worker has not sent its opening "
                  "message)")
            continue

        _print_session(conn, session_id, tail, width, "     ", True)
        print()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="goal_peek.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Attaching a TUI instead of reading:\n"
            "  `opencode run` only serves an HTTP API when it is given --port, and\n"
            "  goal-run does not pass one, so `opencode attach` cannot reach a\n"
            "  worker that is already running.  An attached TUI can also send input\n"
            "  and cancel the turn, so it is not what you want while the pool is\n"
            "  depending on that turn finishing.\n"
        ),
    )
    parser.add_argument("concepts", nargs="*", help="only these (default: all)")
    parser.add_argument("--run-dir", help="pool dir (default: newest under replay/)")
    parser.add_argument(
        "-n", "--tail", type=int, default=12, help="parts per session (default 12)"
    )
    parser.add_argument(
        "--follow", action="store_true", help="keep refreshing until interrupted"
    )
    parser.add_argument(
        "--interval", type=float, default=20.0, help="--follow seconds (default 20)"
    )
    parser.add_argument(
        "--scan",
        type=int,
        default=20,
        help="recent sessions searched when matching a concept (default 20)",
    )
    parser.add_argument(
        "--width", type=int, default=110, help="text truncation width (default 110)"
    )
    args = parser.parse_args(argv)

    run_dir = _pick_run_dir(args.run_dir)
    db = _db_path()
    cache: Dict[str, str] = {}

    if not args.follow:
        conn = _connect(db)
        try:
            report(conn, run_dir, args.concepts, args.tail, args.scan, args.width, cache)
        finally:
            conn.close()
        return 0

    try:
        while True:
            # Reconnect each pass: a connection held open across a WAL
            # checkpoint can keep serving the snapshot it started on.
            conn = _connect(db)
            try:
                os.system("clear")
                report(
                    conn, run_dir, args.concepts, args.tail, args.scan, args.width, cache
                )
                print("(--follow; ctrl-c to stop)")
            finally:
                conn.close()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
