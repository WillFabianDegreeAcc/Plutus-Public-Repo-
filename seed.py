"""Run ``python seed.py`` to populate the configured database with sample data."""

import os
from datetime import date, timedelta
from decimal import Decimal

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from app.models import init_db
from app.models.db import get_conn

load_dotenv()

SAMPLE_EMAIL = os.getenv("SAMPLE_USER_EMAIL", "demo@plutus.local")
SAMPLE_PASSWORD = os.getenv("SAMPLE_USER_PASSWORD", "SamplePassword1!")
SAMPLE_GROUP_CODE = "PLUTUS_SAMPLE"


def seed():
    if not init_db():
        raise RuntimeError("Could not initialise the database schema.")

    connection = get_conn()
    today = date.today()
    transactions = [
        (
            "Monthly salary",
            today - timedelta(days=25),
            Decimal("2800.00"),
            "Credit",
            "salary",
        ),
        ("Rent", today - timedelta(days=22), Decimal("950.00"), "Debit", "housing"),
        ("Groceries", today - timedelta(days=15), Decimal("64.32"), "Debit", "food"),
        (
            "Train tickets",
            today - timedelta(days=8),
            Decimal("27.50"),
            "Debit",
            "transport",
        ),
        (
            "Cinema",
            today - timedelta(days=3),
            Decimal("18.00"),
            "Debit",
            "entertainment",
        ),
    ]
    bank_transactions = [
        (
            "EMPLOYER PAYROLL",
            today - timedelta(days=25),
            Decimal("2800.00"),
            "Credit",
        ),
        ("LANDLORD", today - timedelta(days=22), Decimal("950.00"), "Debit"),
        ("TESCO", today - timedelta(days=15), Decimal("64.32"), "Debit"),
        ("NATIONAL RAIL", today - timedelta(days=8), Decimal("31.50"), "Debit"),
        ("ENERGY COMPANY", today - timedelta(days=5), Decimal("82.00"), "Debit"),
    ]
    reconciled_transaction_indexes = (0, 2)

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE group_code = %s",
                (SAMPLE_GROUP_CODE,),
            )
            if cursor.fetchone() is not None:
                connection.rollback()
                print("Sample data already exists.")
                return

            cursor.execute(
                """
                INSERT INTO users (name, email, password, admin, group_code)
                VALUES (%s, %s, %s, TRUE, %s)
                RETURNING id
                """,
                (
                    "Sample User",
                    SAMPLE_EMAIL,
                    generate_password_hash(SAMPLE_PASSWORD),
                    SAMPLE_GROUP_CODE,
                ),
            )
            user_id = cursor.fetchone()[0]

            transaction_ids = []
            for transaction in transactions:
                cursor.execute(
                    """
                    INSERT INTO transactions (
                        user_id,
                        group_code,
                        name,
                        transaction_date,
                        amount,
                        transaction_type,
                        transaction_genre
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (user_id, SAMPLE_GROUP_CODE, *transaction),
                )
                transaction_ids.append(cursor.fetchone()[0])

            cursor.execute(
                """
                INSERT INTO "bankFileFormats" (
                    user_id,
                    group_code,
                    format_name,
                    delimiter,
                    date_format,
                    data_start_row,
                    date_column,
                    name_column,
                    amount_column,
                    transaction_type_column
                )
                VALUES (%s, %s, %s, ',', '%%Y-%%m-%%d', 2, 1, 2, 3, 4)
                RETURNING id
                """,
                (user_id, SAMPLE_GROUP_CODE, "Sample CSV"),
            )
            bank_file_format_id = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO statements (user_id, bank_file_format_id, group_code, name)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (
                    user_id,
                    bank_file_format_id,
                    SAMPLE_GROUP_CODE,
                    f"sample-statement-{today:%Y-%m}.csv",
                ),
            )
            statement_id = cursor.fetchone()[0]

            bank_transaction_ids = []
            for bank_transaction in bank_transactions:
                cursor.execute(
                    """
                    INSERT INTO "bankTransactions" (
                        statement_id,
                        group_code,
                        name,
                        transaction_date,
                        amount,
                        transaction_type
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (statement_id, SAMPLE_GROUP_CODE, *bank_transaction),
                )
                bank_transaction_ids.append(cursor.fetchone()[0])

            cursor.execute(
                """
                INSERT INTO "reconciledStatements" (user_id, statement_id, group_code)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (user_id, statement_id, SAMPLE_GROUP_CODE),
            )
            reconciled_statement_id = cursor.fetchone()[0]

            for index in reconciled_transaction_indexes:
                cursor.execute(
                    """
                    INSERT INTO "reconciledStatementLines" (
                        reconciled_statement_id,
                        group_code,
                        bank_transaction_id,
                        transaction_id
                    )
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        reconciled_statement_id,
                        SAMPLE_GROUP_CODE,
                        bank_transaction_ids[index],
                        transaction_ids[index],
                    ),
                )

        connection.commit()
    except Exception:
        connection.rollback()
        raise

    print(f"Sample data created. Log in with {SAMPLE_EMAIL} / {SAMPLE_PASSWORD}")


if __name__ == "__main__":
    seed()
