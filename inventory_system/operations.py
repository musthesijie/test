"""Core business logic for the uniform inventory system."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional

from .db import get_connection


@dataclass
class Employee:
    id: int
    name: str
    role: str
    badge: Optional[str]


@dataclass
class Item:
    id: int
    name: str
    size: str
    category: str
    min_stock: int


@dataclass
class Transaction:
    id: int
    item_id: int
    employee_id: Optional[int]
    type: str
    quantity: int
    note: str
    created_at: str


TRANSACTION_LABELS = {
    "stock_in": "入库/补货",
    "issue": "发放",
    "return": "归还",
    "adjust": "盘点调整",
}


# Employee helpers


def list_employees() -> List[Dict]:
    """Return all employees ordered by name for UI dropdowns."""
    with get_connection() as conn:
        cur = conn.execute("SELECT id, name, role, badge FROM employees ORDER BY name")
        return [dict(row) for row in cur.fetchall()]


def add_employee(name: str, role: str = "", badge: str | None = None) -> Dict:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO employees (name, role, badge) VALUES (?, ?, ?)\n"
            "ON CONFLICT(badge) DO UPDATE SET name=excluded.name, role=excluded.role\n"
            "RETURNING id, name, role, badge",
            (name, role, badge),
        )
        row = cur.fetchone()
        return dict(row)


def get_employee(name: str) -> sqlite3.Row:
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM employees WHERE name = ?", (name,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"未找到员工：{name}")
        return row


# Item helpers


def list_items() -> List[Dict]:
    """Return all items ordered by name and size for UI dropdowns."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT i.id, i.name, i.size, i.category, i.min_stock,
                   COALESCE(s.quantity, 0) AS quantity
            FROM items i
            LEFT JOIN stock_levels s ON s.item_id = i.id
            ORDER BY i.name, i.size
            """
        )
        return [dict(row) for row in cur.fetchall()]


def add_item(name: str, size: str, category: str, min_stock: int) -> Dict:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO items (name, size, category, min_stock) VALUES (?, ?, ?, ?)\n"
            "ON CONFLICT(name, size, category) DO UPDATE SET min_stock=excluded.min_stock\n"
            "RETURNING id, name, size, category, min_stock",
            (name, size, category, min_stock),
        )
        row = cur.fetchone()
        conn.execute(
            "INSERT INTO stock_levels (item_id, quantity) VALUES (?, 0)\n"
            "ON CONFLICT(item_id) DO NOTHING",
            (row["id"],),
        )
        return dict(row)


def ensure_item(name: str, size: str, category: str) -> sqlite3.Row:
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM items WHERE name = ? AND size = ? AND category = ?",
            (name, size, category),
        )
        row = cur.fetchone()
        if row:
            return row
    raise ValueError(
        f"未找到该款式，请先使用 add-item 创建：{name} {size} {category}"
    )


# Transactions and reporting

def log_transaction(
    *,
    item_id: int,
    quantity: int,
    ttype: str,
    note: str = "",
    employee_id: int | None = None,
) -> Dict:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO transactions (item_id, employee_id, type, quantity, note)\n"
            "VALUES (?, ?, ?, ?, ?)\n"
            "RETURNING id, item_id, employee_id, type, quantity, note, created_at",
            (item_id, employee_id, ttype, quantity, note),
        )
        transaction = cur.fetchone()
        conn.execute(
            "INSERT INTO stock_levels (item_id, quantity) VALUES (?, 0)\n"
            "ON CONFLICT(item_id) DO NOTHING",
            (item_id,),
        )
        conn.execute(
            "UPDATE stock_levels SET quantity = quantity + ? WHERE item_id = ?",
            (quantity, item_id),
        )
        return dict(transaction)


def get_status_rows() -> List[Dict]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT i.id, i.name, i.size, i.category, s.quantity, i.min_stock,
                   CASE WHEN s.quantity < i.min_stock THEN '⚠️ 低于安全库存' ELSE '' END AS alert
            FROM items i
            LEFT JOIN stock_levels s ON s.item_id = i.id
            ORDER BY i.name, i.size
            """
        )
        return [dict(row) for row in cur.fetchall()]


def search_transactions(name: str | None = None, employee: str | None = None) -> List[Dict]:
    query = [
        "SELECT t.id, i.name, i.size, i.category,",
        "       COALESCE(e.name, '') AS employee,",
        "       t.type, t.quantity, t.note, t.created_at",
        "FROM transactions t",
        "JOIN items i ON i.id = t.item_id",
        "LEFT JOIN employees e ON e.id = t.employee_id",
        "WHERE 1=1",
    ]
    params: list[object] = []
    if name:
        query.append("AND i.name LIKE ?")
        params.append(f"%{name}%")
    if employee:
        query.append("AND e.name LIKE ?")
        params.append(f"%{employee}%")

    query.append("ORDER BY t.created_at DESC")
    sql = "\n".join(query)
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        results: List[Dict] = []
        for row in rows:
            result = dict(row)
            result["type_label"] = TRANSACTION_LABELS.get(result["type"], result["type"])
            results.append(result)
        return results


__all__ = [
    "Employee",
    "Item",
    "Transaction",
    "add_employee",
    "add_item",
    "ensure_item",
    "get_employee",
    "get_status_rows",
    "list_employees",
    "list_items",
    "log_transaction",
    "search_transactions",
]
