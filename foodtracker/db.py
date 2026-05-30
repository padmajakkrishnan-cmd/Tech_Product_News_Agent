"""SQLite storage layer for the food & habit tracker.

Uses the Python standard-library sqlite3 module — no external DB needed.
All dates are stored as ISO 'YYYY-MM-DD' strings supplied by the client so
that "today" always matches the user's local day.
"""

import json
import sqlite3
from contextlib import contextmanager

from foodtracker.config import Config


SCHEMA = """
CREATE TABLE IF NOT EXISTS foods (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    log_date    TEXT NOT NULL,            -- YYYY-MM-DD (local)
    meal        TEXT,                     -- breakfast | lunch | dinner | snack
    name        TEXT NOT NULL,
    quantity    TEXT,                     -- free text e.g. "2 slices", "1 bowl"
    calories    REAL DEFAULT 0,
    protein_g   REAL DEFAULT 0,
    carbs_g     REAL DEFAULT 0,
    fat_g       REAL DEFAULT 0,
    fiber_g     REAL DEFAULT 0,
    source      TEXT,                     -- text | voice | photo
    raw_input   TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS habits (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    log_date    TEXT NOT NULL,
    habit_type  TEXT NOT NULL,            -- see config.HABIT_TYPES
    value       TEXT,                     -- normalised value (e.g. "06:30", "30")
    detail      TEXT,                     -- human-readable description
    numeric     REAL,                     -- optional numeric for aggregation
    source      TEXT,
    raw_input   TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS goals (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_foods_date  ON foods(log_date);
CREATE INDEX IF NOT EXISTS idx_habits_date ON habits(log_date);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables and seed default goals if missing."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        for key, val in Config.DEFAULT_GOALS.items():
            conn.execute(
                "INSERT OR IGNORE INTO goals (key, value) VALUES (?, ?)",
                (key, json.dumps(val)),
            )


# ---------------------------------------------------------------- foods

def add_food(log_date, item, source, raw_input):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO foods
               (log_date, meal, name, quantity, calories, protein_g,
                carbs_g, fat_g, fiber_g, source, raw_input)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                log_date,
                item.get("meal"),
                item.get("name", "unknown"),
                item.get("quantity", ""),
                float(item.get("calories", 0) or 0),
                float(item.get("protein_g", 0) or 0),
                float(item.get("carbs_g", 0) or 0),
                float(item.get("fat_g", 0) or 0),
                float(item.get("fiber_g", 0) or 0),
                source,
                raw_input,
            ),
        )


def get_foods(log_date):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM foods WHERE log_date = ? ORDER BY created_at", (log_date,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_foods_range(start_date, end_date):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM foods WHERE log_date BETWEEN ? AND ? ORDER BY log_date",
            (start_date, end_date),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_food(food_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM foods WHERE id = ?", (food_id,))


# ---------------------------------------------------------------- habits

def add_habit(log_date, item, source, raw_input):
    numeric = item.get("numeric")
    try:
        numeric = float(numeric) if numeric is not None else None
    except (TypeError, ValueError):
        numeric = None
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO habits
               (log_date, habit_type, value, detail, numeric, source, raw_input)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                log_date,
                item.get("habit_type", "other"),
                str(item.get("value", "")),
                item.get("detail", ""),
                numeric,
                source,
                raw_input,
            ),
        )


def get_habits(log_date):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM habits WHERE log_date = ? ORDER BY created_at", (log_date,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_habits_range(start_date, end_date):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM habits WHERE log_date BETWEEN ? AND ? ORDER BY log_date",
            (start_date, end_date),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_habit(habit_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))


# ---------------------------------------------------------------- goals

def get_goals():
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM goals").fetchall()
    return {r["key"]: json.loads(r["value"]) for r in rows}


def set_goals(goals: dict):
    with get_conn() as conn:
        for key, val in goals.items():
            conn.execute(
                "INSERT INTO goals (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, json.dumps(val)),
            )
