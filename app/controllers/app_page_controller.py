from flask import g, render_template, request

from app.models import (
    get_reconciliation_totals,
    get_statement_reconciliation_totals,
    get_statements_for_reconciliation,
)
def app_page():
    group_code = g.current_user["group_code"]
    statements = get_statements_for_reconciliation(group_code)
    totals = get_reconciliation_totals(group_code)

    statement_id_raw = request.args.get("statement_id", "").strip()
    try:
        statement_id = int(statement_id_raw) if statement_id_raw else 0
    except ValueError:
        statement_id = 0

    selected_statement = None
    for statement in statements:
        if statement["id"] == statement_id:
            selected_statement = statement
            break

    statement_totals = None
    if selected_statement is not None:
        statement_totals = get_statement_reconciliation_totals(group_code, statement_id)

    return render_template(
        "postlogin/app.html",
        totals=totals,
        statements=statements,
        selected_statement=selected_statement,
        statement_totals=statement_totals,
    )
