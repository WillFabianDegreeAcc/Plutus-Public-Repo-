from datetime import date
from decimal import Decimal, InvalidOperation

from flask import abort, flash, g, redirect, render_template, request, url_for
from psycopg2 import Error, sql

from app.models.db import execute
from app.services.auth_service import is_email_valid

PAGE_SIZE = 20
TRANSACTION_TYPE_MAP = {"debit": "Debit", "credit": "Credit"}
TRANSACTION_GENRES = {
    "entertainment",
    "food",
    "housing",
    "other",
    "salary",
    "transport",
    "utilities",
}
FINANCIAL_RECORD_TABLES = {
    "transactions": {
        "columns": (
            "id",
            "name",
            "transaction_date",
            "amount",
            "transaction_type",
            "transaction_genre",
        ),
        "editable": (
            "name",
            "transaction_date",
            "amount",
            "transaction_type",
            "transaction_genre",
        ),
    },
    "bankFileFormats": {
        "columns": (
            "id",
            "format_name",
            "delimiter",
            "date_format",
            "data_start_row",
            "date_column",
            "name_column",
            "amount_column",
            "debit_amount_column",
            "credit_amount_column",
            "transaction_type_column",
        ),
        "editable": (
            "format_name",
            "delimiter",
            "date_format",
            "data_start_row",
            "date_column",
            "name_column",
            "amount_column",
            "debit_amount_column",
            "credit_amount_column",
            "transaction_type_column",
        ),
    },
    "statements": {
        "columns": ("id", "bank_file_format_id", "name", "imported_at"),
        "editable": ("name",),
    },
    "bankTransactions": {
        "columns": (
            "id",
            "statement_id",
            "name",
            "transaction_date",
            "amount",
            "transaction_type",
        ),
        "editable": ("name", "transaction_date", "amount", "transaction_type"),
    },
    "reconciledStatements": {
        "columns": ("id", "statement_id", "created_at"),
        "editable": (),
    },
    "reconciledStatementLines": {
        "columns": (
            "id",
            "reconciled_statement_id",
            "bank_transaction_id",
            "transaction_id",
        ),
        "editable": (),
    },
}
SENSITIVE_RECORD_TABLES = {
    "users": {
        "columns": ("id", "name", "email", "admin"),
        "editable": ("name", "email", "admin"),
    },
    "groupInvites": {
        "columns": (
            "id",
            "admin_user_id",
            "used",
            "used_by_user_id",
            "used_at",
            "created_at",
        ),
        "editable": ("used",),
    },
}


def record_viewer_page():
    group_code = g.current_user["group_code"]
    is_admin = g.current_user["is_admin"]
    source = request.form if request.method == "POST" else request.args
    record_tables = dict(FINANCIAL_RECORD_TABLES)
    if is_admin:
        record_tables.update(SENSITIVE_RECORD_TABLES)
    tables = list(record_tables)

    selected_table = source.get("table", "").strip()
    if selected_table in SENSITIVE_RECORD_TABLES and not is_admin:
        abort(403)
    if selected_table and selected_table not in record_tables:
        abort(404)
    if not selected_table:
        selected_table = tables[0]

    try:
        page = int(source.get("page", "1"))
    except ValueError:
        page = 1

    table_config = record_tables[selected_table]
    columns = table_config["columns"]
    editable_columns = table_config["editable"] if is_admin else ()
    rows = []
    total_rows = 0
    total_pages = 1

    try:
        if request.method == "POST":
            if not is_admin:
                abort(403)
            _change_record(selected_table, editable_columns, group_code, is_admin)
            return redirect(
                url_for("main.record_viewer_page", table=selected_table, page=page)
            )

        table_identifier = sql.Identifier(selected_table)
        count_query = sql.SQL(
            "SELECT COUNT(*) FROM {} WHERE group_code = %s"
        ).format(table_identifier)
        total_rows = execute(count_query, (group_code,)).fetchone()[0]
        total_pages = max(1, (total_rows + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(1, min(page, total_pages))
        offset = (page - 1) * PAGE_SIZE

        data_query = sql.SQL(
            "SELECT {} FROM {} WHERE group_code = %s ORDER BY id LIMIT %s OFFSET %s"
        ).format(
            sql.SQL(", ").join(map(sql.Identifier, columns)),
            table_identifier,
        )
        data_rows = execute(
            data_query,
            (group_code, PAGE_SIZE, offset),
        ).fetchall() or []
        rows = [dict(zip(columns, row)) for row in data_rows]
    except Error:
        if request.method == "POST":
            flash("Could not save that row.", "error")
            return redirect(
                url_for("main.record_viewer_page", table=selected_table, page=page)
            )
        rows = []
        total_rows = 0
        total_pages = 1
        page = 1

    return render_template(
        "postlogin/record_viewer.html",
        tables=tables,
        selected_table=selected_table,
        columns=columns,
        editable_columns=editable_columns,
        rows=rows,
        total_rows=total_rows,
        page=page,
        total_pages=total_pages,
        is_admin=is_admin,
    )


def _change_record(selected_table, editable_columns, group_code, is_admin):
    action = request.form.get("action", "").strip()
    try:
        row_id = int(request.form.get("row_id", "0"))
    except ValueError:
        row_id = 0

    if row_id < 1:
        flash("Row was not found.", "error")
        return

    if action == "delete":
        if not is_admin:
            abort(403)
        query = sql.SQL(
            "DELETE FROM {} WHERE id = %s AND group_code = %s RETURNING id"
        ).format(sql.Identifier(selected_table))
        changed_row = execute(query, (row_id, group_code), commit=True).fetchone()
        message = "Row deleted."
    elif action == "update" and editable_columns:
        values = _read_update_values(selected_table, editable_columns)
        if values is None:
            flash("Invalid values for this row.", "error")
            return

        assignments = [
            sql.SQL("{} = %s").format(sql.Identifier(column))
            for column in editable_columns
        ]
        query = (
            sql.SQL("UPDATE {} SET ").format(sql.Identifier(selected_table))
            + sql.SQL(", ").join(assignments)
            + sql.SQL(" WHERE id = %s AND group_code = %s RETURNING id")
        )
        changed_row = execute(
            query,
            tuple(values + [row_id, group_code]),
            commit=True,
        ).fetchone()
        message = "Row updated."
    elif action == "update":
        flash("This table cannot be updated here.", "error")
        return
    else:
        flash("This action is invalid.", "error")
        return

    if changed_row:
        flash(message, "success")
    else:
        flash("Row was not found.", "error")


def _read_update_values(selected_table, editable_columns):
    values = {
        column: request.form.get(column, "").strip() for column in editable_columns
    }

    optional_columns = {
        "amount_column",
        "credit_amount_column",
        "debit_amount_column",
        "transaction_type_column",
    }
    if any(
        not value for column, value in values.items() if column not in optional_columns
    ):
        return None

    try:
        if selected_table in {"transactions", "bankTransactions"}:
            values["transaction_date"] = date.fromisoformat(
                values["transaction_date"]
            )
            values["amount"] = Decimal(values["amount"])
            values["transaction_type"] = TRANSACTION_TYPE_MAP.get(
                values["transaction_type"].lower()
            )
            if (
                not values["amount"].is_finite()
                or values["amount"] <= 0
                or values["transaction_type"] is None
            ):
                return None
            if selected_table == "transactions":
                values["transaction_genre"] = values["transaction_genre"].lower()
                if values["transaction_genre"] not in TRANSACTION_GENRES:
                    return None
        elif selected_table == "bankFileFormats":
            if len(values["delimiter"]) != 1:
                return None

            integer_columns = {
                "amount_column",
                "credit_amount_column",
                "data_start_row",
                "date_column",
                "debit_amount_column",
                "name_column",
                "transaction_type_column",
            }
            for column in integer_columns:
                values[column] = int(values[column]) if values[column] else None
                if values[column] is not None and values[column] < 1:
                    return None

            if not any(
                values[column]
                for column in (
                    "amount_column",
                    "credit_amount_column",
                    "debit_amount_column",
                )
            ):
                return None
        elif selected_table in {"users", "groupInvites"}:
            boolean_column = "admin" if selected_table == "users" else "used"
            boolean_value = values[boolean_column].lower()
            if (
                boolean_value not in {"true", "false"}
                or (
                    selected_table == "users"
                    and not is_email_valid(values["email"])
                )
            ):
                return None
            values[boolean_column] = boolean_value == "true"
    except (InvalidOperation, ValueError):
        return None

    return [values[column] for column in editable_columns]
