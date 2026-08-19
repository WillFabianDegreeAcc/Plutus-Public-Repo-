from flask import flash, g, redirect, render_template, request, url_for

from app.models import (
    add_reconciled_statement,
    get_statements_for_reconciliation,
    get_unreconciled_bank_transactions,
    get_unreconciled_transactions,
)
def reconcile_page():
    group_code = g.current_user["group_code"]
    user_id = g.current_user["id"]
    statements = get_statements_for_reconciliation(group_code)

    selected_statement_id = request.values.get("statement_id", "").strip()
    try:
        selected_statement_id = int(selected_statement_id) if selected_statement_id else 0
    except ValueError:
        selected_statement_id = 0

    selected_statement = None
    for statement in statements:
        if statement["id"] == selected_statement_id:
            selected_statement = statement
            break

    if request.method == "GET" and selected_statement is None and statements:
        selected_statement = statements[0]
        selected_statement_id = selected_statement["id"]

    bank_transactions = []
    manual_transactions = []

    if selected_statement is not None:
        bank_transactions = get_unreconciled_bank_transactions(
            selected_statement_id,
            group_code,
        )
        manual_transactions = get_unreconciled_transactions(group_code)

    if request.method == "POST":
        if selected_statement is None:
            flash("Please select a statement to reconcile.", "error")
            return redirect(url_for("main.reconcile_page"))

        available_bank_transactions = {
            str(bank_transaction["id"]): bank_transaction
            for bank_transaction in bank_transactions
        }
        available_transactions = {
            str(transaction["id"]): transaction for transaction in manual_transactions
        }

        lines = []
        used_transaction_ids = set()
        bank_transaction_ids = request.form.getlist("bank_transaction_id")
        transaction_ids = request.form.getlist("transaction_id")

        for bank_transaction_id, transaction_id in zip(bank_transaction_ids, transaction_ids):
            transaction_id = transaction_id.strip()
            if not transaction_id:
                continue

            bank_transaction = available_bank_transactions.get(bank_transaction_id)
            manual_transaction = available_transactions.get(transaction_id)

            if bank_transaction is None or manual_transaction is None:
                flash("One of the selected transactions is no longer available.", "error")
                return redirect(
                    url_for("main.reconcile_page", statement_id=selected_statement_id)
                )

            if transaction_id in used_transaction_ids:
                flash("A manual transaction can only be used once.", "error")
                return redirect(
                    url_for("main.reconcile_page", statement_id=selected_statement_id)
                )

            if (
                bank_transaction["amount"] != manual_transaction["amount"]
                or bank_transaction["transaction_type"] != manual_transaction["transaction_type"]
            ):
                flash("Matched lines must have the same amount and type.", "error")
                return redirect(
                    url_for("main.reconcile_page", statement_id=selected_statement_id)
                )

            used_transaction_ids.add(transaction_id)
            lines.append((bank_transaction["id"], manual_transaction["id"]))

        if not lines:
            flash("Select at least one line to reconcile.", "error")
            return redirect(url_for("main.reconcile_page", statement_id=selected_statement_id))

        reconciled_statement_id = add_reconciled_statement(
            user_id,
            selected_statement_id,
            group_code,
            lines,
        )

        if reconciled_statement_id is None:
            flash("Could not save reconciled statement.", "error")
        else:
            flash(f"Reconciled statement saved with {len(lines)} line(s).", "success")

        return redirect(url_for("main.reconcile_page", statement_id=selected_statement_id))

    return render_template(
        "postlogin/reconcile.html",
        statements=statements,
        selected_statement=selected_statement,
        bank_transactions=bank_transactions,
        manual_transactions=manual_transactions,
    )
