import psycopg2
from psycopg2 import sql

from app.models.db import execute

BANK_FILE_FORMAT_SELECT_COLUMNS = sql.SQL(
    """
                id,
                format_name,
                delimiter,
                date_format,
                data_start_row,
                date_column,
                name_column,
                amount_column,
                debit_amount_column,
                credit_amount_column,
                transaction_type_column
"""
)


def add_bank_file_format(
    user_id,
    group_code,
    format_name,
    delimiter,
    date_format,
    data_start_row,
    date_column,
    name_column,
    amount_column,
    debit_amount_column,
    credit_amount_column,
    transaction_type_column,
):
    try:
        cursor = execute(
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
                debit_amount_column,
                credit_amount_column,
                transaction_type_column
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                group_code,
                format_name,
                delimiter,
                date_format,
                data_start_row,
                date_column,
                name_column,
                amount_column,
                debit_amount_column,
                credit_amount_column,
                transaction_type_column,
            ),
            commit=True,
        )
        row = cursor.fetchone()
        return row[0] if row else None
    except psycopg2.Error:
        return None


def get_bank_file_formats_for_group(group_code):
    try:
        return execute(
            sql.SQL(
                """
            SELECT
{}
            FROM "bankFileFormats"
            WHERE group_code = %s
            ORDER BY format_name ASC, id ASC
            """
            ).format(BANK_FILE_FORMAT_SELECT_COLUMNS),
            (group_code,),
        ).fetchall()
    except psycopg2.Error:
        return []


def get_bank_file_format_by_id(group_code, bank_file_format_id):
    try:
        return execute(
            sql.SQL(
                """
            SELECT
{}
            FROM "bankFileFormats"
            WHERE group_code = %s AND id = %s
            """
            ).format(BANK_FILE_FORMAT_SELECT_COLUMNS),
            (group_code, bank_file_format_id),
        ).fetchone()
    except psycopg2.Error:
        return None
