"""Command-line entrypoint for managing uniform inventory.

The commands prioritize the day-to-day flows for a security company:
- stocking uniforms into the warehouse
- issuing uniforms to guards
- receiving returns or exchanges
- tracking shortages via minimum stock alerts

Usage examples::

    python -m inventory_system.cli init
    python -m inventory_system.cli add-item "制服衬衫" --size L --category 夏季 --min-stock 20
    python -m inventory_system.cli stock-in "制服衬衫" --size L --category 夏季 --quantity 50
    python -m inventory_system.cli add-employee "张三" --role 班长 --badge 10086
    python -m inventory_system.cli issue "制服衬衫" --size L --to "张三" --quantity 2 --note "入职发放"
    python -m inventory_system.cli status
"""
from __future__ import annotations

import argparse
from typing import Any, Dict, List

from .db import DB_PATH, get_connection, init_db
from .operations import (
    add_employee,
    add_item,
    ensure_item,
    get_employee,
    get_status_rows,
    log_transaction,
    search_transactions,
)


TRANSACTION_TYPES = {"stock_in", "issue", "return", "adjust"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="安全公司服装出入库管理")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="初始化数据库")

    add_item_cmd = sub.add_parser("add-item", help="添加新的服装款式")
    add_item_cmd.add_argument("name")
    add_item_cmd.add_argument("--size", default="")
    add_item_cmd.add_argument("--category", default="")
    add_item_cmd.add_argument("--min-stock", type=int, default=0)

    add_emp_cmd = sub.add_parser("add-employee", help="录入员工信息")
    add_emp_cmd.add_argument("name")
    add_emp_cmd.add_argument("--role", default="")
    add_emp_cmd.add_argument("--badge", default=None)

    stock_in_cmd = sub.add_parser("stock-in", help="入库/补货")
    stock_in_cmd.add_argument("name")
    stock_in_cmd.add_argument("--size", default="")
    stock_in_cmd.add_argument("--category", default="")
    stock_in_cmd.add_argument("--quantity", type=int, required=True)
    stock_in_cmd.add_argument("--note", default="")

    issue_cmd = sub.add_parser("issue", help="发放给员工")
    issue_cmd.add_argument("name")
    issue_cmd.add_argument("--size", default="")
    issue_cmd.add_argument("--category", default="")
    issue_cmd.add_argument("--to", required=True, help="员工姓名")
    issue_cmd.add_argument("--quantity", type=int, required=True)
    issue_cmd.add_argument("--note", default="")

    return_cmd = sub.add_parser("return", help="员工归还")
    return_cmd.add_argument("name")
    return_cmd.add_argument("--size", default="")
    return_cmd.add_argument("--category", default="")
    return_cmd.add_argument("--from", dest="from_", required=True, help="员工姓名")
    return_cmd.add_argument("--quantity", type=int, required=True)
    return_cmd.add_argument("--note", default="")

    adjust_cmd = sub.add_parser("adjust", help="盘点调整数量")
    adjust_cmd.add_argument("name")
    adjust_cmd.add_argument("--size", default="")
    adjust_cmd.add_argument("--category", default="")
    adjust_cmd.add_argument("--quantity", type=int, required=True, help="调整数值，可为负")
    adjust_cmd.add_argument("--note", default="")

    sub.add_parser("status", help="查看库存与安全库存预警")

    history_cmd = sub.add_parser("history", help="查询出入库记录")
    history_cmd.add_argument("--name", default=None, help="按服装名称过滤")
    history_cmd.add_argument("--employee", default=None, help="按员工姓名过滤")

    return parser


def _print_table(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print("暂无记录")
        return
    headers = rows[0].keys()
    widths = {h: max(len(h), *(len(str(r[h])) for r in rows)) for h in headers}
    header_line = "  ".join(f"{h:<{widths[h]}}" for h in headers)
    print(header_line)
    print("-" * len(header_line))
    for r in rows:
        print("  ".join(f"{str(r[h]):<{widths[h]}}" for h in headers))


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        init_db()
        print("数据库已初始化：", DB_PATH.resolve())
        return

    init_db()

    if args.command == "add-item":
        item = add_item(args.name, args.size, args.category, args.min_stock)
        print(f"已创建/更新款式 #{item['id']}: {item['name']} {item['size']} {item['category']}")
        return

    if args.command == "add-employee":
        emp = add_employee(args.name, args.role, args.badge)
        print(f"已录入员工 #{emp['id']}: {emp['name']} ({emp['role']})")
        return

    if args.command == "stock-in":
        item = ensure_item(args.name, args.size, args.category)
        log_transaction(item_id=item["id"], quantity=args.quantity, ttype="stock_in", note=args.note)
        print(f"入库 {args.quantity} 件 {item['name']} {item['size']}")
        return

    if args.command == "issue":
        item = ensure_item(args.name, args.size, args.category)
        emp = get_employee(args.to)
        log_transaction(item_id=item["id"], employee_id=emp["id"], quantity=-abs(args.quantity), ttype="issue", note=args.note)
        print(f"已向 {emp['name']} 发放 {abs(args.quantity)} 件 {item['name']} {item['size']}")
        return

    if args.command == "return":
        item = ensure_item(args.name, args.size, args.category)
        emp = get_employee(args.from_)
        log_transaction(item_id=item["id"], employee_id=emp["id"], quantity=abs(args.quantity), ttype="return", note=args.note)
        print(f"已从 {emp['name']} 收回 {abs(args.quantity)} 件 {item['name']} {item['size']}")
        return

    if args.command == "adjust":
        item = ensure_item(args.name, args.size, args.category)
        log_transaction(item_id=item["id"], quantity=args.quantity, ttype="adjust", note=args.note)
        print(f"已调整 {item['name']} {item['size']} 数量 {args.quantity}")
        return

    if args.command == "status":
        rows = get_status_rows()
        _print_table(rows)
        return

    if args.command == "history":
        rows = search_transactions(name=args.name, employee=args.employee)
        _print_table(rows)
        return

    raise RuntimeError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
