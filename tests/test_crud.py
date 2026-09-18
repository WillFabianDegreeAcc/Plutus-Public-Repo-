from datetime import date
from decimal import Decimal

from app.controllers import record_viewer_controller, transaction_controller
from app.models import transaction_model


class Cursor:
    def __init__(self, *, row=None, rows=None):
        self.row = row
        self.rows = rows

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


def test_create_transaction(client, log_in, monkeypatch):
    log_in(client, admin=True)
    created_values = []
    monkeypatch.setattr(
        transaction_controller,
        "add_transaction",
        lambda *values: created_values.append(values) or 42,
    )

    response = client.post(
        "/transactions",
        data={
            "name": "Groceries",
            "date": "2026-09-28",
            "amount": "12.50",
            "transaction_type": "debit",
            "genre": "food",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/transactions")
    assert created_values == [
        (
            1,
            "GROUP-1",
            "Groceries",
            date(2026, 9, 28),
            Decimal("12.50"),
            "Debit",
            "food",
        )
    ]


def test_browse_records_is_limited_to_the_users_group(
    client, log_in, monkeypatch
):
    log_in(client)
    calls = []
    cursors = iter(
        [
            Cursor(row=(1,)),
            Cursor(
                rows=[
                    (1, "Groceries", date(2026, 9, 28), Decimal("12.50"), "Debit", "food")
                ]
            ),
        ]
    )

    def execute(query, params=(), *, commit=False):
        calls.append((query, params, commit))
        return next(cursors)

    monkeypatch.setattr(record_viewer_controller, "execute", execute)

    response = client.get("/record-viewer?table=transactions")

    assert response.status_code == 200
    assert b"Groceries" in response.data
    assert calls[0][1] == ("GROUP-1",)
    assert calls[1][1] == ("GROUP-1", 20, 0)
    assert not calls[0][2]
    assert not calls[1][2]


def test_update_record(client, log_in, monkeypatch):
    log_in(client, admin=True)
    calls = []

    def execute(query, params=(), *, commit=False):
        calls.append((query, params, commit))
        return Cursor(row=(7,))

    monkeypatch.setattr(record_viewer_controller, "execute", execute)

    response = client.post(
        "/record-viewer",
        data={
            "action": "update",
            "table": "transactions",
            "row_id": "7",
            "name": "Updated purchase",
            "transaction_date": "2026-09-27",
            "amount": "25.00",
            "transaction_type": "credit",
            "transaction_genre": "other",
        },
    )

    assert response.status_code == 302
    assert calls[0][1] == (
        "Updated purchase",
        date(2026, 9, 27),
        Decimal("25.00"),
        "Credit",
        "other",
        7,
        "GROUP-1",
    )
    assert calls[0][2]


def test_delete_record(client, log_in, monkeypatch):
    log_in(client, admin=True)
    calls = []

    def execute(query, params=(), *, commit=False):
        calls.append((query, params, commit))
        return Cursor(row=(7,))

    monkeypatch.setattr(record_viewer_controller, "execute", execute)

    response = client.post(
        "/record-viewer",
        data={
            "action": "delete",
            "table": "transactions",
            "row_id": "7",
        },
    )

    assert response.status_code == 302
    assert calls[0][1] == (7, "GROUP-1")
    assert calls[0][2]


def test_create_query_uses_parameters(monkeypatch):
    calls = []
    malicious_name = "Lunch'); DROP TABLE transactions; --"

    def execute(query, params=(), *, commit=False):
        calls.append((query, params, commit))
        return Cursor(row=(8,))

    monkeypatch.setattr(transaction_model, "execute", execute)

    transaction_id = transaction_model.add_transaction(
        1,
        "GROUP-1",
        malicious_name,
        date(2026, 9, 28),
        Decimal("9.99"),
        "Debit",
        "food",
    )

    assert transaction_id == 8
    assert malicious_name not in calls[0][0]
    assert calls[0][1][2] == malicious_name
    assert calls[0][2]
