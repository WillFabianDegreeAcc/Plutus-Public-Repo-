import pytest

from app.controllers import bank_import_controller, record_viewer_controller
from app.messages import (
    INVALID_EMAIL,
    INVALID_TRANSACTION,
    MISSING_FIELDS,
    WEAK_PASSWORD,
)
from app.services import auth_service


@pytest.mark.parametrize(
    "data",
    [
        {},
        {
            "name": "Purchase",
            "date": "not-a-date",
            "amount": "10.00",
            "transaction_type": "debit",
            "genre": "food",
        },
        {
            "name": "Purchase",
            "date": "2026-09-28",
            "amount": "-1.00",
            "transaction_type": "debit",
            "genre": "food",
        },
        {
            "name": "Purchase",
            "date": "2026-09-28",
            "amount": "NaN",
            "transaction_type": "debit",
            "genre": "food",
        },
        {
            "name": "Purchase",
            "date": "2026-09-28",
            "amount": "Infinity",
            "transaction_type": "debit",
            "genre": "food",
        },
        {
            "name": "Purchase",
            "date": "2026-09-28",
            "amount": "10.00",
            "transaction_type": "refund",
            "genre": "food",
        },
    ],
)
def test_invalid_transactions_are_rejected(client, log_in, monkeypatch, data):
    log_in(client, admin=True)
    created = False

    def add_transaction(*args):
        nonlocal created
        created = True

    monkeypatch.setattr(
        "app.controllers.transaction_controller.add_transaction",
        add_transaction,
    )

    response = client.post("/transactions", data=data)

    assert response.status_code == 302
    assert not created
    with client.session_transaction() as session:
        assert session["_flashes"][-1][1] in {MISSING_FIELDS, INVALID_TRANSACTION}


@pytest.mark.parametrize(
    ("password", "expected_message"),
    [
        ("", MISSING_FIELDS),
        ("short", WEAK_PASSWORD),
        ("alllowercase123!", WEAK_PASSWORD),
    ],
)
def test_invalid_signup_is_rejected(
    client, monkeypatch, password, expected_message
):
    created = False

    def create_user(*args):
        nonlocal created
        created = True

    monkeypatch.setattr(
        "app.controllers.auth_controller.auth_service.create_user",
        create_user,
    )

    response = client.post(
        "/signup",
        data={"name": "Test User", "email": "test@example.com", "password": password},
    )

    assert response.status_code == 302
    assert not created
    with client.session_transaction() as session:
        assert session["_flashes"][-1][1] == expected_message


@pytest.mark.parametrize(
    ("email", "is_valid"),
    [
        ("user@example.com", True),
        ("user.name+tag@example.co.uk", True),
        ("user.example.com", False),
        ("user@example", False),
        ("user @example.com", False),
    ],
)
def test_email_validation(email, is_valid):
    assert auth_service.is_email_valid(email) is is_valid


@pytest.mark.parametrize(
    ("path", "create_method", "requires_admin", "requires_invite"),
    [
        ("/signup", "create_user", False, False),
        (
            "/invite/invite-token/signup",
            "create_invited_user",
            False,
            True,
        ),
        ("/settings/users", "create_group_user", True, False),
    ],
)
def test_invalid_creation_email_is_rejected(
    client,
    log_in,
    monkeypatch,
    path,
    create_method,
    requires_admin,
    requires_invite,
):
    if requires_admin:
        log_in(client, admin=True)
    if requires_invite:
        monkeypatch.setattr(
            auth_service,
            "read_invite",
            lambda token: {"used": False},
        )

    created = False

    def create_user(*args):
        nonlocal created
        created = True

    monkeypatch.setattr(auth_service, create_method, create_user)

    response = client.post(
        path,
        data={
            "name": "Test User",
            "email": "invalid-email",
            "password": "StrongPassword1!",
        },
    )

    assert response.status_code == 302
    assert not created
    with client.session_transaction() as session:
        assert session["_flashes"][-1][1] == INVALID_EMAIL


@pytest.mark.parametrize(
    "changes",
    [
        {"amount": "0"},
        {"amount": "not-a-number"},
        {"transaction_date": "31/12/2026"},
        {"transaction_type": "Transfer"},
        {"transaction_genre": "Unknown"},
    ],
)
def test_invalid_record_updates_are_rejected(
    client, log_in, monkeypatch, changes
):
    log_in(client, admin=True)
    database_called = False

    def execute(*args, **kwargs):
        nonlocal database_called
        database_called = True

    monkeypatch.setattr(record_viewer_controller, "execute", execute)
    data = {
        "action": "update",
        "table": "transactions",
        "row_id": "1",
        "name": "Purchase",
        "transaction_date": "2026-09-28",
        "amount": "10.00",
        "transaction_type": "Debit",
        "transaction_genre": "food",
    }
    data.update(changes)

    response = client.post("/record-viewer", data=data)

    assert response.status_code == 302
    assert not database_called
    with client.session_transaction() as session:
        assert session["_flashes"][-1][1] == "Invalid values for this row."


@pytest.mark.parametrize(
    "data",
    [
        {},
        {
            "format_name": "Bank",
            "delimiter": "::",
            "date_format": "%Y-%m-%d",
            "data_start_row": "2",
            "date_column": "1",
            "name_column": "2",
            "amount_column": "3",
        },
        {
            "format_name": "Bank",
            "delimiter": ",",
            "date_format": "%Y-%m-%d",
            "data_start_row": "0",
            "date_column": "1",
            "name_column": "2",
            "amount_column": "3",
        },
        {
            "format_name": "Bank",
            "delimiter": ",",
            "date_format": "%Y-%m-%d",
            "data_start_row": "2",
            "date_column": "1",
            "name_column": "2",
        },
    ],
)
def test_invalid_bank_formats_are_rejected(
    client, log_in, monkeypatch, data
):
    log_in(client, admin=True)
    created = False

    def add_bank_file_format(*args):
        nonlocal created
        created = True

    monkeypatch.setattr(
        bank_import_controller,
        "add_bank_file_format",
        add_bank_file_format,
    )

    response = client.post("/bank-import/formats", data=data)

    assert response.status_code == 302
    assert not created
