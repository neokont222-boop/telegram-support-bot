import sqlite3
from datetime import datetime

DB_NAME = "tickets.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop TEXT,
            problem TEXT,
            subproblem TEXT,
            critical TEXT,
            description TEXT,
            phone TEXT,
            author_id INTEGER,
            author_name TEXT,
            status TEXT DEFAULT 'new',
            admin_comment TEXT,
            created_at TEXT
        )
        """)

        conn.commit()


def create_ticket(
    shop, problem, subproblem, critical,
    description, phone, author_id, author_name
):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO tickets (
            shop, problem, subproblem, critical,
            description, phone, author_id, author_name,
            status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            shop,
            problem,
            subproblem,
            critical,
            description,
            phone,
            author_id,
            author_name,
            "new",
            datetime.now().isoformat()
        ))

        conn.commit()
        return cursor.lastrowid


def update_ticket_status(ticket_id: int, status: str):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE tickets SET status = ? WHERE id = ?",
            (status, ticket_id)
        )

        conn.commit()


def save_admin_comment(ticket_id: int, comment: str):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE tickets SET admin_comment = ? WHERE id = ?",
            (comment, ticket_id)
        )

        conn.commit()


def get_ticket_author(ticket_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT author_id FROM tickets WHERE id = ?",
            (ticket_id,)
        )

        row = cursor.fetchone()
        return row[0] if row else None


def get_all_tickets():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT
            id,
            shop,
            problem,
            subproblem,
            critical,
            status,
            created_at
        FROM tickets
        ORDER BY id DESC
        """)

        return cursor.fetchall()


def get_tickets_by_status(status=None):
    with get_connection() as conn:
        cursor = conn.cursor()

        if status:
            cursor.execute("""
            SELECT
                id,
                shop,
                problem,
                subproblem,
                critical,
                status,
                created_at
            FROM tickets
            WHERE status = ?
            ORDER BY id DESC
            """, (status,))
        else:
            cursor.execute("""
            SELECT
                id,
                shop,
                problem,
                subproblem,
                critical,
                status,
                created_at
            FROM tickets
            ORDER BY id DESC
            """)

        return cursor.fetchall()
