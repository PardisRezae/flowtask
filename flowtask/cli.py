from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from .config import default_db_path
from . import db
from .graph import would_create_cycle
from .models import Task


def _parse_date(d: Optional[str]) -> Optional[date]:
    if not d:
        return None
    try:
        return date.fromisoformat(d)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid date '{d}'. Use YYYY-MM-DD.") from e


def _db_path_from_args(ns: argparse.Namespace) -> Path:
    if getattr(ns, "db", None):
        return Path(ns.db).expanduser().resolve()
    return default_db_path()


def _print_tasks(tasks: list[Task]) -> None:
    if not tasks:
        print("No tasks found.")
        return
    print(f"{'ID':>3}  {'ST':<4} {'P':>2}  {'DUE':<10}  TITLE")
    print("-" * 60)
    for t in tasks:
        due = t.due.isoformat() if t.due else ""
        st = "DONE" if t.status == "done" else "TODO"
        print(f"{t.id:>3}  {st:<4} {t.priority:>2}  {due:<10}  {t.title}")


def cmd_init(ns: argparse.Namespace) -> int:
    path = _db_path_from_args(ns)
    db.init_db(path)
    print(f"Initialized database at: {path}")
    return 0


def cmd_add(ns: argparse.Namespace) -> int:
    path = _db_path_from_args(ns)
    db.init_db(path)
    task_id = db.add_task(
        path,
        title=ns.title,
        description=ns.description or "",
        priority=int(ns.priority),
        due=ns.due,
        tags=ns.tags or "",
    )
    print(f"Added task #{task_id}: {ns.title}")
    return 0


def cmd_list(ns: argparse.Namespace) -> int:
    path = _db_path_from_args(ns)
    db.init_db(path)
    status = None
    if ns.todo:
        status = "todo"
    elif ns.done:
        status = "done"
    tasks = db.list_tasks(path, status=status)
    _print_tasks(tasks)
    return 0


def cmd_done(ns: argparse.Namespace) -> int:
    path = _db_path_from_args(ns)
    db.init_db(path)
    ok = db.mark_done(path, int(ns.task_id))
    if not ok:
        print(f"Task #{ns.task_id} not found.", file=sys.stderr)
        return 1
    print(f"Marked task #{ns.task_id} as done.")
    return 0


def cmd_depend(ns: argparse.Namespace) -> int:
    path = _db_path_from_args(ns)
    db.init_db(path)
    task_id = int(ns.task_id)
    prereq_id = int(ns.prereq_id)

    if not db.get_task(path, task_id):
        print(f"Task #{task_id} not found.", file=sys.stderr)
        return 1
    if not db.get_task(path, prereq_id):
        print(f"Prerequisite task #{prereq_id} not found.", file=sys.stderr)
        return 1

    edges = db.get_dependencies(path)
    if would_create_cycle(edges, task_id=task_id, prereq_id=prereq_id):
        print(
            f"Cannot add dependency: {task_id} depends on {prereq_id} would create a cycle.",
            file=sys.stderr,
        )
        return 1

    db.add_dependency(path, task_id, prereq_id)
    print(f"Added dependency: task #{task_id} depends on #{prereq_id}")
    return 0


def cmd_next(ns: argparse.Namespace) -> int:
    path = _db_path_from_args(ns)
    db.init_db(path)
    tasks = db.ready_tasks(path)
    print("Next tasks you can work on (all prerequisites done):")
    _print_tasks(tasks)
    return 0


def cmd_export(ns: argparse.Namespace) -> int:
    path = _db_path_from_args(ns)
    db.init_db(path)
    data = db.export_json(path)
    out = Path(ns.out).expanduser().resolve()
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Exported to: {out}")
    return 0


def cmd_import(ns: argparse.Namespace) -> int:
    path = _db_path_from_args(ns)
    data_path = Path(ns.file).expanduser().resolve()
    data = json.loads(data_path.read_text(encoding="utf-8"))
    db.import_json(path, data)
    print(f"Imported from: {data_path} into {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="flowtask",
        description="FlowTask: a dependency-aware task manager (Python + SQLite).",
    )
    p.add_argument(
        "--db",
        help="Path to SQLite DB (default: ~/.flowtask/flowtask.db or FLOWTASK_DB env var)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="Initialize the database.")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("add", help="Add a new task.")
    s.add_argument("title", help="Short task title.")
    s.add_argument("-d", "--description", help="Longer description.")
    s.add_argument("-p", "--priority", type=int, default=0, help="Priority (higher = more important).")
    s.add_argument("--due", type=_parse_date, help="Due date in YYYY-MM-DD.")
    s.add_argument("--tags", help="Comma-separated tags (e.g., school,cs).")
    s.set_defaults(func=cmd_add)

    s = sub.add_parser("list", help="List tasks.")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--todo", action="store_true", help="Only todo tasks.")
    g.add_argument("--done", action="store_true", help="Only done tasks.")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("done", help="Mark a task as done.")
    s.add_argument("task_id", help="Task ID.")
    s.set_defaults(func=cmd_done)

    s = sub.add_parser("depend", help="Add a dependency: TASK depends on PREREQ.")
    s.add_argument("task_id", help="Task ID.")
    s.add_argument("prereq_id", help="Prerequisite task ID.")
    s.set_defaults(func=cmd_depend)

    s = sub.add_parser("next", help="Show tasks that are ready to work on.")
    s.set_defaults(func=cmd_next)

    s = sub.add_parser("export", help="Export tasks/deps to JSON.")
    s.add_argument("--out", required=True, help="Output JSON file path.")
    s.set_defaults(func=cmd_export)

    s = sub.add_parser("import", help="Import tasks/deps from JSON.")
    s.add_argument("file", help="JSON file previously exported by flowtask export.")
    s.set_defaults(func=cmd_import)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    return int(ns.func(ns))