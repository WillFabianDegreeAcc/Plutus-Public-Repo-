import psycopg2

from app.models.db import execute, get_conn


def get_reconciliation_totals(group_code):
    try:
        cursor = execute(
            """
            SELECT
                COUNT(bt.id),
                COUNT(rsl.id)
            FROM "bankTransactions" bt
            LEFT JOIN "reconciledStatementLines" rsl ON rsl.bank_transaction_id = bt.id
            WHERE bt.group_code = %s
            """,
            (group_code,),
        )
        row = cursor.fetchone()
        if row is None:
            return {"unreconciled_count": 0, "reconciled_count": 0}
        total_count = row[0] or 0
        reconciled_count = row[1] or 0
        return {
            "unreconciled_count": total_count - reconciled_count,
            "reconciled_count": reconciled_count,
        }
    except psycopg2.Error:
        return {"unreconciled_count": 0, "reconciled_count": 0}


def get_statement_reconciliation_totals(group_code, statement_id):
    try:
        cursor = execute(
            """
            SELECT
                COUNT(bt.id),
                COUNT(rsl.id)
            FROM "bankTransactions" bt
            LEFT JOIN "reconciledStatementLines" rsl ON rsl.bank_transaction_id = bt.id
            WHERE bt.group_code = %s AND bt.statement_id = %s
            """,
            (group_code, statement_id),
        )
        row = cursor.fetchone()
        if row is None:
            return {"unreconciled_count": 0, "reconciled_count": 0}
        total_count = row[0] or 0
        reconciled_count = row[1] or 0
        return {
            "unreconciled_count": total_count - reconciled_count,
            "reconciled_count": reconciled_count,
        }
    except psycopg2.Error:
        return {"unreconciled_count": 0, "reconciled_count": 0}


def get_statements_for_reconciliation(group_code):
    try:
        cursor = execute(
            """
            SELECT id, name, imported_at
            FROM statements
            WHERE group_code = %s
            ORDER BY imported_at DESC, id DESC
            """,
            (group_code,),
        )
        rows = cursor.fetchall() or []
        return [
            {"id": row[0], "name": row[1], "imported_at": row[2]}
            for row in rows
        ]
    except psycopg2.Error:
        return []


def get_unreconciled_bank_transactions(statement_id, group_code):
    try:
        cursor = execute(
            """
            SELECT bt.id, bt.name, bt.transaction_date, bt.amount, bt.transaction_type
            FROM "bankTransactions" bt
            LEFT JOIN "reconciledStatementLines" rsl ON rsl.bank_transaction_id = bt.id
            WHERE bt.statement_id = %s AND bt.group_code = %s AND rsl.id IS NULL
            ORDER BY bt.transaction_date, bt.id
            """,
            (statement_id, group_code),
        )
        rows = cursor.fetchall() or []
        return [
            {
                "id": row[0],
                "name": row[1],
                "transaction_date": row[2],
                "amount": row[3],
                "transaction_type": row[4],
            }
            for row in rows
        ]
    except psycopg2.Error:
        return []


def get_unreconciled_transactions(group_code):
    try:
        cursor = execute(
            """
            SELECT t.id, t.name, t.transaction_date, t.amount, t.transaction_type
            FROM transactions t
            LEFT JOIN "reconciledStatementLines" rsl ON rsl.transaction_id = t.id
            WHERE t.group_code = %s AND rsl.id IS NULL
            ORDER BY t.transaction_date, t.id
            """,
            (group_code,),
        )
        rows = cursor.fetchall() or []
        return [
            {
                "id": row[0],
                "name": row[1],
                "transaction_date": row[2],
                "amount": row[3],
                "transaction_type": row[4],
            }
            for row in rows
        ]
    except psycopg2.Error:
        return []


def add_reconciled_statement(user_id, statement_id, group_code, lines):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO "reconciledStatements" (
                user_id,
                statement_id,
                group_code
            )
            SELECT users.id, statements.id, %s
            FROM users
            CROSS JOIN statements
            WHERE users.id = %s
              AND users.group_code = %s
              AND statements.id = %s
              AND statements.group_code = %s
            RETURNING id
            """,
            (group_code, user_id, group_code, statement_id, group_code),
        )
        row = cursor.fetchone()
        if row is None:
            conn.rollback()
            return None

        reconciled_statement_id = row[0]

        for bank_transaction_id, transaction_id in lines:
            cursor.execute(
                """
                INSERT INTO "reconciledStatementLines" (
                    reconciled_statement_id,
                    group_code,
                    bank_transaction_id,
                    transaction_id
                )
                SELECT %s, %s, bank_transactions.id, transactions.id
                FROM "bankTransactions" bank_transactions
                JOIN transactions ON transactions.id = %s
                WHERE bank_transactions.id = %s
                  AND bank_transactions.statement_id = %s
                  AND bank_transactions.group_code = %s
                  AND transactions.group_code = %s
                """,
                (
                    reconciled_statement_id,
                    group_code,
                    transaction_id,
                    bank_transaction_id,
                    statement_id,
                    group_code,
                    group_code,
                ),
            )
            if cursor.rowcount != 1:
                conn.rollback()
                return None

        conn.commit()
        return reconciled_statement_id
    except psycopg2.Error:
        conn.rollback()
        return None
