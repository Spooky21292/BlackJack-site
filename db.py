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
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_seen_at TEXT NOT NULL
            )
            """
        )
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
                notified_deadline INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            """
        )
        conn.commit()


def upsert_user(user_id: int, username: str | None, first_name: str | None) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (user_id, username, first_name, last_seen_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_seen_at=excluded.last_seen_at
            """,
            (user_id, username, first_name, utc_now_iso()),
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
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (
                user_id, title, description, deadline, status, created_at,
                completed_at, notified_24h, notified_1h, notified_deadline
            )
            VALUES (?, ?, ?, ?, 'active', ?, NULL, 0, 0, 0)
            """,
            (user_id, title, description, deadline, utc_now_iso()),
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


def complete_task(task_id: int, user_id: int) -> dict | None:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE tasks
            SET status = 'completed', completed_at = ?
            WHERE id = ? AND user_id = ? AND status = 'active'
            """,
            (utc_now_iso(), task_id, user_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            row = conn.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)).fetchone()
            return row_to_task(row) if row else None

        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return row_to_task(row)


def delete_task(task_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
        conn.commit()
    return cursor.rowcount > 0


def mark_notification(task_id: int, field: str) -> None:
    if field not in {"notified_24h", "notified_1h", "notified_deadline"}:
        return
    with get_connection() as conn:
        conn.execute(f"UPDATE tasks SET {field} = 1 WHERE id = ?", (task_id,))
        conn.commit()


def complete_task_by_system(task_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE tasks SET status = 'completed', completed_at = ? WHERE id = ? AND status = 'active'",
            (utc_now_iso(), task_id),
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
            SELECT
                t.user_id,
                COUNT(*) AS completed_count,
                u.username,
                u.first_name
            FROM tasks t
            LEFT JOIN users u ON u.user_id = t.user_id
            WHERE t.status = 'completed'
            GROUP BY t.user_id
            ORDER BY completed_count DESC, t.user_id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    result = []
    for row in rows:
        username = row["username"]
        if username:
            display_name = f"@{username}"
        elif row["first_name"]:
            display_name = row["first_name"]
        else:
            display_name = f"id:{row['user_id']}"

        result.append(
            {
                "user_id": row["user_id"],
                "username": username,
                "first_name": row["first_name"],
                "display_name": display_name,
                "completed_count": row["completed_count"],
            }
        )
    return result


def get_stats() -> dict:
    with get_connection() as conn:
        total_users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        total_tasks = conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()["c"]
        completed_tasks = conn.execute("SELECT COUNT(*) AS c FROM tasks WHERE status='completed'").fetchone()["c"]
        users = conn.execute(
            "SELECT user_id, username, first_name, last_seen_at FROM users ORDER BY last_seen_at DESC"
        ).fetchall()

    user_list = [
        {
            "user_id": row["user_id"],
            "username": row["username"],
            "first_name": row["first_name"],
            "last_seen_at": row["last_seen_at"],
        }
        for row in users
    ]

    return {
        "total_users": total_users,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "users": user_list,
    }
