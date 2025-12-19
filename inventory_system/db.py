"""SQLite database helpers for the uniform inventory system.

This module centralizes connection handling and schema creation so that
CLI commands can assume tables exist. The schema keeps a small set of
normalized tables for employees, uniform items, and transaction history.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

DB_PATH = Path("inventory.db")


SCHEMA_STATEMENTS: Iterable[str] = (
    """
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT,
        badge TEXT UNIQUE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        size TEXT,
        category TEXT,
        min_stock INTEGER DEFAULT 0,
        UNIQUE(name, size, category)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS stock_levels (
        item_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (item_id),
        FOREIGN KEY (item_id) REFERENCES items(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        employee_id INTEGER,
        type TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (item_id) REFERENCES items(id),
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    );
    """,
)


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Create tables if they do not exist."""
    with get_connection() as conn:
        for stmt in SCHEMA_STATEMENTS:
            conn.executescript(stmt)


__all__ = ["get_connection", "init_db", "DB_PATH"]
