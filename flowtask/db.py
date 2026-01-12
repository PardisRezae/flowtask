from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Optional

from .models import Task

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    priority    INTEGER NOT NULL DEFAULT 0,
    due         TEXT, -- ISO date: YYYY-MM-DD (nullable)
    status      TEXT NOT NULL DEFAULT 'todo',
    tags        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS deps (
    task_id        INTEGER NOT NULL,
    depends_on_id  INTEGER NOT NULL,
    PRIMARY KEY (task_id, depends_on_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (depends_on_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_deps_task ON deps(task_id);
CREATE INDEX IF NOT EXISTS idx_deps_depends ON deps(depends_on_id);
"""


def _iso_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)


def _parse_due(due_text: Optional[str]) -> Optional[date]:
    if due_text is None:
        return None
    return date.fromisoformat(due_text)


def _row_to_task(row: sqlite3.Row) -> Task:
    return Task(
        id=int(row["id"]),
        title=str(row["title"]),
        description=str(row["description"]),
        priority=int(row["priority"]),
        due=_parse_due(row["due"]),
        status=str(row["status"]),
        tags=str(row["tags"]),
        created_at=datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00")),
        updated_at=datetime.fromisoformat(str(row["updated_at"]).replace("Z", "+00:00")),
    )


def add_task(
    db_path: Path,
    *,
    title: str,
    description: str = "",
    priority: int = 0,
    due: Optional[date] = None,
    tags: str = "",
) -> int:
    now = _iso_now()
    due_text = due.isoformat() if due else None

    with connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO tasks (title, description, priority, due, status, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'todo', ?, ?, ?)
            """,
            (title, description, priority, due_text, tags, now, now),
        )
        return int(cur.lastrowid)


def get_task(db_path: Path, task_id: int) -> Optional[Task]:
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return _row_to_task(row) if row else None


def list_tasks(db_path: Path, status: Optional[str] = None) -> list[Task]:
    with connect(db_path) as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY id ASC", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tasks ORDER BY id ASC").fetchall()
        return [_row_to_task(r) for r in rows]


def mark_done(db_path: Path, task_id: int) -> bool:
    now = _iso_now()
    with connect(db_path) as conn:
        cur = conn.execute(
            "UPDATE tasks SET status = 'done', updated_at = ? WHERE id = ?",
            (now, task_id),
        )
        return cur.rowcount > 0


def add_dependency(db_path: Path, task_id: int, depends_on_id: int) -> None:
    """
    Edge: task_id -> depends_on_id (task depends on prerequisite).
    """
    with connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO deps (task_id, depends_on_id) VALUES (?, ?)",
            (task_id, depends_on_id),
        )


def get_dependencies(db_path: Path) -> list[tuple[int, int]]:
    with connect(db_path) as conn:
        rows = conn.execute("SELECT task_id, depends_on_id FROM deps").fetchall()
        return [(int(r["task_id"]), int(r["depends_on_id"])) for r in rows]


def ready_tasks(db_path: Path) -> list[Task]:
    """
    Tasks that are todo and whose prerequisites are all done.
    """
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT t.*
            FROM tasks t
            WHERE t.status = 'todo'
              AND NOT EXISTS (
                SELECT 1
                FROM deps d
                JOIN tasks prereq ON prereq.id = d.depends_on_id
                WHERE d.task_id = t.id
                  AND prereq.status != 'done'
              )
            ORDER BY
              CASE WHEN t.due IS NULL THEN 1 ELSE 0 END,
              t.due ASC,
              t.priority DESC,
              t.id ASC
            """
        ).fetchall()
        return [_row_to_task(r) for r in rows]


def export_json(db_path: Path) -> dict:
    tasks = list_tasks(db_path)
    deps = get_dependencies(db_path)

    def task_to_dict(t: Task) -> dict:
        d = asdict(t)
        d["due"] = t.due.isoformat() if t.due else None
        d["created_at"] = t.created_at.isoformat()
        d["updated_at"] = t.updated_at.isoformat()
        return d

    return {"tasks": [task_to_dict(t) for t in tasks], "deps": deps}


def import_json(db_path: Path, data: dict) -> None:
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute("DELETE FROM deps")
        conn.execute("DELETE FROM tasks")

        for t in data.get("tasks", []):
            conn.execute(
                """
                INSERT INTO tasks (id, title, description, priority, due, status, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(t["id"]),
                    t["title"],
                    t.get("description", ""),
                    int(t.get("priority", 0)),
                    t.get("due"),
                    t.get("status", "todo"),
                    t.get("tags", ""),
                    t.get("created_at", _iso_now()),
                    t.get("updated_at", _iso_now()),
                ),
            )

        for task_id, depends_on_id in data.get("deps", []):
            conn.execute(
                "INSERT INTO deps (task_id, depends_on_id) VALUES (?, ?)",
                (int(task_id), int(depends_on_id)),
            )