"""Flask-powered web UI for the uniform inventory system."""
from __future__ import annotations

from typing import Callable, Dict, Tuple

from flask import Flask, redirect, render_template, request, url_for

from .db import init_db
from .operations import (
    add_employee,
    add_item,
    ensure_item,
    get_employee,
    get_status_rows,
    list_employees,
    list_items,
    log_transaction,
    search_transactions,
)


def create_app() -> Flask:
    app = Flask(__name__)
    init_db()

    def _redirect_with_message(target: str, message: str | None = None, error: str | None = None):
        params = {}
        if message:
            params["message"] = message
        if error:
            params["error"] = error
        return redirect(url_for(target, **params))

    def _handle_action(action: Callable[[], str]) -> Tuple[str, int]:
        try:
            message = action()
            return _redirect_with_message("dashboard", message=message), 302
        except Exception as exc:  # noqa: BLE001 - render to UI as friendly text
            return _redirect_with_message("dashboard", error=str(exc)), 302

    @app.get("/")
    def dashboard():
        status_rows = get_status_rows()
        employees = list_employees()
        items = list_items()
        message = request.args.get("message")
        error = request.args.get("error")
        return render_template(
            "dashboard.html",
            status_rows=status_rows,
            employees=employees,
            items=items,
            message=message,
            error=error,
            recent_history=search_transactions()[:10],
        )

    @app.get("/history")
    def history():
        name = request.args.get("name") or None
        employee = request.args.get("employee") or None
        message = request.args.get("message")
        error = request.args.get("error")
        results = search_transactions(name=name, employee=employee)
        return render_template(
            "history.html",
            transactions=results,
            message=message,
            error=error,
            filters={"name": name or "", "employee": employee or ""},
        )

    @app.post("/add-item")
    def add_item_route():
        def _action() -> str:
            form: Dict[str, str] = request.form.to_dict()
            min_stock = int(form.get("min_stock", "0") or 0)
            item = add_item(
                form.get("name", "").strip(),
                form.get("size", "").strip(),
                form.get("category", "").strip(),
                min_stock,
            )
            return f"已创建/更新款式：{item['name']} {item['size']} {item['category']}"

        return _handle_action(_action)

    @app.post("/add-employee")
    def add_employee_route():
        def _action() -> str:
            form: Dict[str, str] = request.form.to_dict()
            emp = add_employee(
                form.get("name", "").strip(),
                form.get("role", "").strip(),
                form.get("badge") or None,
            )
            return f"已录入员工：{emp['name']}"

        return _handle_action(_action)

    def _transaction_action(ttype: str, signed_quantity: Callable[[int], int]):
        def wrapper():
            form: Dict[str, str] = request.form.to_dict()
            quantity = signed_quantity(int(form.get("quantity", "0") or 0))
            item = ensure_item(
                form.get("name", "").strip(),
                form.get("size", "").strip(),
                form.get("category", "").strip(),
            )
            employee_id = None
            employee_name = form.get("employee") or form.get("employee_name")
            if employee_name:
                employee = get_employee(employee_name.strip())
                employee_id = employee["id"]
            log_transaction(
                item_id=item["id"],
                employee_id=employee_id,
                quantity=quantity,
                ttype=ttype,
                note=form.get("note", "").strip(),
            )
            return f"已记录 {ttype}：{item['name']} {item['size']} 数量 {quantity}"

        return _handle_action(wrapper)

    @app.post("/stock-in")
    def stock_in():
        return _transaction_action("stock_in", lambda q: abs(q))

    @app.post("/issue")
    def issue():
        return _transaction_action("issue", lambda q: -abs(q))

    @app.post("/return")
    def return_item():
        return _transaction_action("return", lambda q: abs(q))

    @app.post("/adjust")
    def adjust():
        return _transaction_action("adjust", lambda q: q)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
