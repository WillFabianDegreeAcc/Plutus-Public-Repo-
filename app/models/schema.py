import psycopg2

from app.models.db import execute

SCHEMA_SQL = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        session_token TEXT,
        admin BOOLEAN NOT NULL DEFAULT FALSE,
        group_code TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS "groupInvites" (
        id SERIAL PRIMARY KEY,
        admin_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        group_code TEXT NOT NULL,
        invite_token TEXT NOT NULL UNIQUE,
        used BOOLEAN NOT NULL DEFAULT FALSE,
        used_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        used_at TIMESTAMP,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        group_code TEXT NOT NULL,
        name TEXT NOT NULL,
        transaction_date DATE NOT NULL,
        amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
        transaction_type TEXT NOT NULL CHECK (transaction_type IN ('Debit', 'Credit')),
        transaction_genre TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS "bankFileFormats" (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        group_code TEXT NOT NULL,
        format_name TEXT NOT NULL,
        delimiter TEXT NOT NULL,
        date_format TEXT NOT NULL,
        data_start_row INTEGER NOT NULL CHECK (data_start_row > 0),
        date_column INTEGER NOT NULL CHECK (date_column > 0),
        name_column INTEGER NOT NULL CHECK (name_column > 0),
        amount_column INTEGER CHECK (amount_column > 0),
        debit_amount_column INTEGER CHECK (debit_amount_column > 0),
        credit_amount_column INTEGER CHECK (credit_amount_column > 0),
        transaction_type_column INTEGER CHECK (transaction_type_column > 0)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS statements (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        bank_file_format_id INTEGER NOT NULL REFERENCES "bankFileFormats"(id) ON DELETE RESTRICT,
        group_code TEXT NOT NULL,
        name TEXT NOT NULL,
        imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS "bankTransactions" (
        id SERIAL PRIMARY KEY,
        statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
        group_code TEXT NOT NULL,
        name TEXT NOT NULL,
        transaction_date DATE NOT NULL,
        amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
        transaction_type TEXT NOT NULL CHECK (transaction_type IN ('Debit', 'Credit'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS "reconciledStatements" (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
        group_code TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS "reconciledStatementLines" (
        id SERIAL PRIMARY KEY,
        reconciled_statement_id INTEGER NOT NULL REFERENCES "reconciledStatements"(id) ON DELETE CASCADE,
        group_code TEXT NOT NULL,
        bank_transaction_id INTEGER NOT NULL REFERENCES "bankTransactions"(id) ON DELETE CASCADE UNIQUE,
        transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE UNIQUE
    )
    """
]


def init_db():
    try:
        for schema_sql in SCHEMA_SQL:
            execute(schema_sql, commit=True)
        return True
    except psycopg2.Error:
        return False
