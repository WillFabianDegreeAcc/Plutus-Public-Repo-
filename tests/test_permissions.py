import pytest

from app.controllers import record_viewer_controller


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/settings"),
        ("post", "/settings/invite"),
        ("post", "/settings/users"),
        ("post", "/transactions"),
        ("post", "/bank-import/formats"),
        ("post", "/bank-import/upload"),
        ("get", "/reconcile"),
    ],
)
def test_regular_user_cannot_access_admin_routes(client, log_in, method, path):
    log_in(client)

    response = getattr(client, method)(path)

    assert response.status_code == 403


def test_regular_user_can_browse_financial_records(
    client, log_in, monkeypatch
):
    log_in(client)

    class EmptyCursor:
        def fetchone(self):
            return (0,)

        def fetchall(self):
            return []

    monkeypatch.setattr(
        record_viewer_controller,
        "execute",
        lambda *args, **kwargs: EmptyCursor(),
    )

    response = client.get("/record-viewer?table=transactions")

    assert response.status_code == 200


def test_regular_user_cannot_browse_sensitive_records(client, log_in):
    log_in(client)

    response = client.get("/record-viewer?table=users")

    assert response.status_code == 403


def test_regular_user_cannot_change_records(client, log_in, monkeypatch):
    log_in(client)
    database_called = False

    def execute(*args, **kwargs):
        nonlocal database_called
        database_called = True

    monkeypatch.setattr(record_viewer_controller, "execute", execute)

    response = client.post(
        "/record-viewer",
        data={"table": "transactions", "action": "delete", "row_id": "1"},
    )

    assert response.status_code == 403
    assert not database_called


def test_administrator_can_access_settings(client, log_in):
    log_in(client, admin=True)

    response = client.get("/settings")

    assert response.status_code == 200
    assert b"Create user" in response.data


def test_anonymous_user_is_redirected_from_protected_page(client):
    response = client.get("/transactions")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_invalid_session_is_cleared(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.session_service.get_user_for_session",
        lambda user_id, token: None,
    )
    with client.session_transaction() as session:
        session["user_id"] = 99
        session["session_token"] = "expired-token"

    response = client.get("/transactions")

    assert response.status_code == 302
    with client.session_transaction() as session:
        assert "user_id" not in session
        assert "session_token" not in session
