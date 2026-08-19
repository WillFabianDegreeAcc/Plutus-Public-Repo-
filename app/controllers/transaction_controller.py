from datetime import date
from decimal import Decimal, InvalidOperation

from flask import flash, g, redirect, render_template, request, url_for

from app.messages import INVALID_TRANSACTION, MISSING_FIELDS
from app.models import add_transaction
def transactions_page():
    return render_template("postlogin/transactions.html")


def create_transaction():
    name = request.form.get("name", "").strip()
    transaction_date_raw = request.form.get("date", "").strip()
    amount_raw = request.form.get("amount", "").strip()
    transaction_type_raw = request.form.get("transaction_type", "").strip()
    transaction_genre = request.form.get("genre", "").strip().lower()

    if not all([name, transaction_date_raw, amount_raw, transaction_type_raw, transaction_genre]):
        flash(MISSING_FIELDS, "error")
        return redirect(url_for("main.transactions_page"))

    try:
        transaction_date = date.fromisoformat(transaction_date_raw)
        amount = Decimal(amount_raw)
    except (ValueError, InvalidOperation):
        flash(INVALID_TRANSACTION, "error")
        return redirect(url_for("main.transactions_page"))

    transaction_type = {"debit": "Debit", "credit": "Credit"}.get(transaction_type_raw.lower())

    if amount <= 0 or transaction_type is None:
        flash(INVALID_TRANSACTION, "error")
        return redirect(url_for("main.transactions_page"))

    user_id = g.current_user["id"]
    group_code = g.current_user["group_code"]
    created_transaction_id = add_transaction(
        user_id,
        group_code,
        name,
        transaction_date,
        amount,
        transaction_type,
        transaction_genre,
    )
    if created_transaction_id is None:
        flash(INVALID_TRANSACTION, "error")
        return redirect(url_for("main.transactions_page"))

    return redirect(url_for("main.transactions_page"))
