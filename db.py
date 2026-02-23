import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.getenv("DB_PATH", "tasks.db")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                deadline INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                notified_24h INTEGER NOT NULL DEFAULT 0,
                notified_1h INTEGER NOT NULL DEFAULT 0,
                notified_deadline INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()


def row_to_task(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "title": row["title"],
        "description": row["description"],
        "deadline": row["deadline"],
        "status": row["status"],
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
        "notified_24h": bool(row["notified_24h"]),
        "notified_1h": bool(row["notified_1h"]),
        "notified_deadline": bool(row["notified_deadline"]),
    }


def create_task(user_id: int, title: str, description: str | None, deadline: int) -> dict:
    created_at = utc_now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (
                user_id, title, description, deadline, status, created_at,
                completed_at, notified_24h, notified_1h, notified_deadline
            )
            VALUES (?, ?, ?, ?, 'active', ?, NULL, 0, 0, 0)
            """,
            (user_id, title, description, deadline, created_at),
        )
        task_id = cursor.lastrowid
        conn.commit()

        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return row_to_task(row)


def get_tasks(user_id: int, task_filter: str | None) -> list[dict]:
    now_ts = int(datetime.now(timezone.utc).timestamp())

    query = "SELECT * FROM tasks WHERE user_id = ?"
    params: list = [user_id]

    if task_filter == "active":
        query += " AND status = 'active'"
    elif task_filter == "completed":
        query += " AND status = 'completed'"
    elif task_filter == "today":
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        end = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=999999)
        query += " AND deadline BETWEEN ? AND ?"
        params.extend([int(start.timestamp()), int(end.timestamp())])
    else:
        query += " AND deadline >= ?"
        params.append(now_ts)

    query += " ORDER BY deadline ASC"

    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [row_to_task(row) for row in rows]


def get_task_by_id(task_id: int, user_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)
        ).fetchone()
    if row is None:
        return None
    return row_to_task(row)


def complete_task(task_id: int, user_id: int) -> dict | None:
    completed_at = utc_now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE tasks
            SET status = 'completed', completed_at = ?
            WHERE id = ? AND user_id = ? AND status = 'active'
            """,
            (completed_at, task_id, user_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)
            ).fetchone()
            return row_to_task(row) if row else None

        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return row_to_task(row)


def delete_task(task_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)
        )
        conn.commit()
    return cursor.rowcount > 0


def mark_notification(task_id: int, field: str) -> None:
    if field not in {"notified_24h", "notified_1h", "notified_deadline"}:
        return

    with get_connection() as conn:
        conn.execute(f"UPDATE tasks SET {field} = 1 WHERE id = ?", (task_id,))
        conn.commit()


def complete_task_by_system(task_id: int) -> None:
    completed_at = utc_now_iso()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status = 'completed', completed_at = ?
            WHERE id = ? AND status = 'active'
            """,
            (completed_at, task_id),
        )
        conn.commit()


def get_active_tasks_for_notifications() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM tasks WHERE status = 'active'").fetchall()
    return [row_to_task(row) for row in rows]


def get_leaderboard(limit: int = 10) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT user_id, COUNT(*) AS completed_count
            FROM tasks
            WHERE status = 'completed'
            GROUP BY user_id
            ORDER BY completed_count DESC, user_id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [{"user_id": row["user_id"], "completed_count": row["completed_count"]} for row in rows]
