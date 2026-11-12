"""SQLite persistence for the Telegram rewards bot."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("BOT_DATABASE_PATH", BASE_DIR / "data" / "bot.sqlite3"))


class BusinessError(Exception):
    """A user-facing operation that cannot be completed."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=20)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 20000")
    return connection


@contextmanager
def _transaction() -> Iterator[sqlite3.Connection]:
    connection = _connect()
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    connection = _connect()
    try:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version > 1:
            raise RuntimeError("The bot database was created by a newer version.")

        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                last_mining_at INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS ledger_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(user_id),
                amount INTEGER NOT NULL CHECK (amount != 0),
                kind TEXT NOT NULL,
                reference TEXT NOT NULL UNIQUE,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ledger_user_created_idx
                ON ledger_entries(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                instructions TEXT NOT NULL,
                reward_points INTEGER NOT NULL CHECK (reward_points > 0),
                is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS task_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL REFERENCES tasks(id),
                user_id INTEGER NOT NULL REFERENCES users(user_id),
                proof TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'approved', 'rejected')),
                reviewer_id INTEGER,
                created_at TEXT NOT NULL,
                reviewed_at TEXT,
                UNIQUE(task_id, user_id)
            );
            CREATE INDEX IF NOT EXISTS submissions_status_created_idx
                ON task_submissions(status, created_at);

            CREATE TABLE IF NOT EXISTS withdrawal_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(user_id),
                points INTEGER NOT NULL CHECK (points > 0),
                method TEXT NOT NULL CHECK (method IN ('ccp', 'binance')),
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'approved', 'rejected', 'paid')),
                reviewer_id INTEGER,
                created_at TEXT NOT NULL,
                reviewed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS withdrawals_status_created_idx
                ON withdrawal_requests(status, created_at);

            CREATE TABLE IF NOT EXISTS user_states (
                user_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                state TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        connection.execute("PRAGMA user_version = 1")
    finally:
        connection.close()


def register_user(user_id: int, first_name: str, username: str | None) -> None:
    with _transaction() as connection:
        connection.execute(
            """
            INSERT INTO users (user_id, username, first_name, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
            """,
            (user_id, username, first_name[:128], _now()),
        )


def get_balance(user_id: int) -> int:
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT COALESCE(SUM(amount), 0) AS balance FROM ledger_entries WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return int(row["balance"])
    finally:
        connection.close()


def set_state(user_id: int, state: str, payload: dict[str, Any] | None = None) -> None:
    with _transaction() as connection:
        connection.execute(
            """
            INSERT INTO user_states (user_id, state, payload_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                state = excluded.state,
                payload_json = excluded.payload_json,
                updated_at = excluded.updated_at
            """,
            (user_id, state, json.dumps(payload or {}, ensure_ascii=False), _now()),
        )


def get_state(user_id: int) -> tuple[str, dict[str, Any]] | None:
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT state, payload_json FROM user_states WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        try:
            payload = json.loads(row["payload_json"])
        except (TypeError, json.JSONDecodeError):
            payload = {}
        return str(row["state"]), payload
    finally:
        connection.close()


def clear_state(user_id: int) -> None:
    with _transaction() as connection:
        connection.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))


def list_active_tasks(limit: int = 12) -> list[dict[str, Any]]:
    connection = _connect()
    try:
        rows = connection.execute(
            """
            SELECT id, title, instructions, reward_points
            FROM tasks
            WHERE is_active = 1
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def submit_task_proof(task_id: int, user_id: int, proof: str) -> int:
    with _transaction() as connection:
        task = connection.execute(
            "SELECT id, is_active FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        if task is None or not task["is_active"]:
            raise BusinessError("هذه المهمة غير متاحة الآن.")

        existing = connection.execute(
            "SELECT id, status FROM task_submissions WHERE task_id = ? AND user_id = ?",
            (task_id, user_id),
        ).fetchone()
        if existing and existing["status"] == "pending":
            raise BusinessError("لديك إثبات قيد المراجعة لهذه المهمة.")
        if existing and existing["status"] == "approved":
            raise BusinessError("سبق اعتماد هذه المهمة لحسابك.")

        if existing:
            connection.execute(
                """
                UPDATE task_submissions
                SET proof = ?, status = 'pending', reviewer_id = NULL,
                    created_at = ?, reviewed_at = NULL
                WHERE id = ?
                """,
                (proof[:2000], _now(), existing["id"]),
            )
            submission_id = int(existing["id"])
        else:
            cursor = connection.execute(
                """
                INSERT INTO task_submissions (task_id, user_id, proof, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (task_id, user_id, proof[:2000], _now()),
            )
            submission_id = int(cursor.lastrowid)
        return submission_id


def create_task(title: str, instructions: str, reward_points: int, admin_id: int) -> int:
    if reward_points <= 0:
        raise BusinessError("قيمة المكافأة يجب أن تكون رقمًا موجبًا.")
    if not title.strip() or not instructions.strip():
        raise BusinessError("أدخل عنوان المهمة وتعليماتها.")
    with _transaction() as connection:
        cursor = connection.execute(
            """
            INSERT INTO tasks (title, instructions, reward_points, created_by, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title[:100], instructions[:1500], reward_points, admin_id, _now()),
        )
        task_id = int(cursor.lastrowid)
        _audit(connection, admin_id, "task_created", "task", task_id)
        return task_id


def pause_task(task_id: int, admin_id: int) -> bool:
    with _transaction() as connection:
        row = connection.execute(
            "SELECT id, is_active FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        if row is None:
            raise BusinessError("لم أجد هذه المهمة.")
        new_status = 0 if row["is_active"] else 1
        connection.execute(
            "UPDATE tasks SET is_active = ? WHERE id = ?",
            (new_status, task_id),
        )
        _audit(connection, admin_id, "task_activated" if new_status else "task_paused", "task", task_id)
        return bool(new_status)


def review_submission(submission_id: int, admin_id: int, approve: bool) -> dict[str, Any]:
    with _transaction() as connection:
        row = connection.execute(
            """
            SELECT s.id, s.user_id, s.status, t.reward_points, t.title
            FROM task_submissions s
            JOIN tasks t ON t.id = s.task_id
            WHERE s.id = ?
            """,
            (submission_id,),
        ).fetchone()
        if row is None:
            raise BusinessError("لم أجد طلب المهمة.")
        if row["status"] != "pending":
            raise BusinessError("تمت مراجعة هذا الإثبات من قبل.")

        status = "approved" if approve else "rejected"
        connection.execute(
            """
            UPDATE task_submissions
            SET status = ?, reviewer_id = ?, reviewed_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (status, admin_id, _now(), submission_id),
        )
        if approve:
            _insert_ledger(
                connection,
                int(row["user_id"]),
                int(row["reward_points"]),
                "task_reward",
                f"task_submission:{submission_id}",
                f"مكافأة المهمة: {row['title'][:100]}",
            )
        _audit(connection, admin_id, f"task_{status}", "submission", submission_id)
        return {
            "user_id": int(row["user_id"]),
            "points": int(row["reward_points"]),
            "title": str(row["title"]),
            "status": status,
        }


def claim_mining(user_id: int, reward_points: int, cooldown_seconds: int) -> int:
    now = int(datetime.now(timezone.utc).timestamp())
    with _transaction() as connection:
        row = connection.execute(
            "SELECT last_mining_at FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            raise BusinessError("أرسل /start أولًا.")
        remaining = cooldown_seconds - (now - int(row["last_mining_at"]))
        if remaining > 0:
            raise BusinessError(f"يمكنك المحاولة مجددًا بعد {format_duration(remaining)}.")

        connection.execute(
            "UPDATE users SET last_mining_at = ? WHERE user_id = ?",
            (now, user_id),
        )
        _insert_ledger(
            connection,
            user_id,
            reward_points,
            "simulated_mining",
            f"mining:{user_id}:{now}",
            "نقاط تعدين تجريبية",
        )
        return get_balance_in_transaction(connection, user_id)


def create_withdrawal(user_id: int, points: int, method: str) -> int:
    if points <= 0:
        raise BusinessError("أدخل عدد نقاط أكبر من صفر.")
    if method not in ("ccp", "binance"):
        raise BusinessError("طريقة السحب غير معروفة.")

    with _transaction() as connection:
        balance = get_balance_in_transaction(connection, user_id)
        if points > balance:
            raise BusinessError(f"رصيدك الحالي {balance} نقطة فقط.")
        cursor = connection.execute(
            """
            INSERT INTO withdrawal_requests (user_id, points, method, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, points, method, _now()),
        )
        request_id = int(cursor.lastrowid)
        _insert_ledger(
            connection,
            user_id,
            -points,
            "withdrawal_reserved",
            f"withdrawal:{request_id}:reserve",
            f"حجز نقاط لطلب السحب #{request_id}",
        )
        return request_id


def review_withdrawal(request_id: int, admin_id: int, action: str) -> dict[str, Any]:
    if action not in ("approve", "reject", "paid"):
        raise BusinessError("إجراء السحب غير معروف.")
    with _transaction() as connection:
        row = connection.execute(
            """
            SELECT id, user_id, points, method, status
            FROM withdrawal_requests WHERE id = ?
            """,
            (request_id,),
        ).fetchone()
        if row is None:
            raise BusinessError("لم أجد طلب السحب.")

        current_status = str(row["status"])
        if action == "approve" and current_status == "pending":
            new_status = "approved"
        elif action == "reject" and current_status in ("pending", "approved"):
            new_status = "rejected"
            _insert_ledger(
                connection,
                int(row["user_id"]),
                int(row["points"]),
                "withdrawal_refund",
                f"withdrawal:{request_id}:refund",
                f"إرجاع نقاط الطلب #{request_id}",
            )
        elif action == "paid" and current_status == "approved":
            new_status = "paid"
        else:
            raise BusinessError("لا يمكن تنفيذ هذا الإجراء على حالة الطلب الحالية.")

        connection.execute(
            """
            UPDATE withdrawal_requests
            SET status = ?, reviewer_id = ?, reviewed_at = ?
            WHERE id = ?
            """,
            (new_status, admin_id, _now(), request_id),
        )
        _audit(connection, admin_id, f"withdrawal_{new_status}", "withdrawal", request_id)
        return {
            "user_id": int(row["user_id"]),
            "points": int(row["points"]),
            "method": str(row["method"]),
            "status": new_status,
        }


def get_pending_items(limit: int = 10) -> dict[str, list[dict[str, Any]]]:
    connection = _connect()
    try:
        submissions = connection.execute(
            """
            SELECT s.id, s.user_id, s.proof, s.created_at, t.title
            FROM task_submissions s
            JOIN tasks t ON t.id = s.task_id
            WHERE s.status = 'pending'
            ORDER BY s.created_at
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        withdrawals = connection.execute(
            """
            SELECT w.id, w.user_id, w.points, w.method, w.created_at,
                   w.status, u.username, u.first_name
            FROM withdrawal_requests w
            JOIN users u ON u.user_id = w.user_id
            WHERE w.status IN ('pending', 'approved')
            ORDER BY w.created_at
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return {
            "submissions": [dict(row) for row in submissions],
            "withdrawals": [dict(row) for row in withdrawals],
        }
    finally:
        connection.close()


def get_stats() -> dict[str, int]:
    connection = _connect()
    try:
        users = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
        pending_tasks = connection.execute(
            "SELECT COUNT(*) AS count FROM task_submissions WHERE status = 'pending'"
        ).fetchone()["count"]
        pending_withdrawals = connection.execute(
            "SELECT COUNT(*) AS count FROM withdrawal_requests WHERE status IN ('pending', 'approved')"
        ).fetchone()["count"]
        return {
            "users": int(users),
            "pending_tasks": int(pending_tasks),
            "pending_withdrawals": int(pending_withdrawals),
        }
    finally:
        connection.close()


def get_submission(submission_id: int) -> dict[str, Any] | None:
    connection = _connect()
    try:
        row = connection.execute(
            """
            SELECT s.id, s.user_id, s.proof, s.status, t.title
            FROM task_submissions s
            JOIN tasks t ON t.id = s.task_id
            WHERE s.id = ?
            """,
            (submission_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_balance_in_transaction(connection: sqlite3.Connection, user_id: int) -> int:
    row = connection.execute(
        "SELECT COALESCE(SUM(amount), 0) AS balance FROM ledger_entries WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return int(row["balance"])


def _insert_ledger(
    connection: sqlite3.Connection,
    user_id: int,
    amount: int,
    kind: str,
    reference: str,
    note: str,
) -> None:
    connection.execute(
        """
        INSERT INTO ledger_entries (user_id, amount, kind, reference, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, amount, kind, reference, note[:200], _now()),
    )


def _audit(
    connection: sqlite3.Connection,
    actor_id: int,
    action: str,
    target_type: str,
    target_id: int,
) -> None:
    connection.execute(
        """
        INSERT INTO audit_events (actor_id, action, target_type, target_id, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (actor_id, action, target_type, target_id, _now()),
    )


def format_duration(seconds: int) -> str:
    hours, remainder = divmod(max(0, seconds), 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours} ساعة و{minutes} دقيقة"
    return f"{max(1, minutes)} دقيقة"
