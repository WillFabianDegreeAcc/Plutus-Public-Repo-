"""Regression tests for OWASP Top 10 controls.

A01:2021 Broken Access Control is covered by the permission tests and tenant filters.
A03:2021 Injection is covered by table allow-listing, SQL parameters, and HTML escaping.
A05:2021 Security Misconfiguration is covered by response-header assertions.
A07:2021 Identification and Authentication Failures is covered by session tests.
"""

from datetime import date
from decimal import Decimal

from app.controllers import record_viewer_controller


class Cursor:
    def __init__(self, *, row=None, rows=None):
        self.row = row
        self.rows = rows

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


def test_a01_cross_tenant_updates_include_group_filter(
    client, log_in, monkeypatch
):
    log_in(client, admin=True)
    calls = []

    def execute(query, params=(), *, commit=False):
        calls.append((query, params, commit))
        return Cursor(row=None)

    monkeypatch.setattr(record_viewer_controller, "execute", execute)

    client.post(
        "/record-viewer",
        data={
            "action": "delete",
            "table": "transactions",
            "row_id": "99",
        },
    )

    assert calls[0][1] == (99, "GROUP-1")


def test_a03_unlisted_table_name_is_rejected(client, log_in, monkeypatch):
    log_in(client, admin=True)
    database_called = False

    def execute(*args, **kwargs):
        nonlocal database_called
        database_called = True

    monkeypatch.setattr(record_viewer_controller, "execute", execute)

    response = client.get("/record-viewer?table=transactions%3BDELETE%20FROM%20users")

    assert response.status_code == 404
    assert not database_called


def test_a03_database_content_is_html_escaped(client, log_in, monkeypatch):
    log_in(client)
    cursors = iter(
        [
            Cursor(row=(1,)),
            Cursor(
                rows=[
                    (
                        1,
                        "<script>alert(1)</script>",
                        date(2026, 9, 28),
                        Decimal("10.00"),
                        "Debit",
                        "food",
                    )
                ]
            ),
        ]
    )
    monkeypatch.setattr(
        record_viewer_controller,
        "execute",
        lambda *args, **kwargs: next(cursors),
    )

    response = client.get("/record-viewer?table=transactions")

    assert b"<script>alert(1)</script>" not in response.data
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in response.data


def test_a05_security_headers_are_set(client):
    response = client.get("/")

    assert response.headers["Content-Security-Policy"].startswith("default-src 'self'")
    assert response.headers["Strict-Transport-Security"] == (
        "max-age=31536000; includeSubDomains"
    )
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == (
        "camera=(), geolocation=(), microphone=()"
    )


def test_a05_session_cookie_settings_are_secure(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_post_without_csrf_token_is_rejected(client, app):
    app.config["WTF_CSRF_ENABLED"] = True

    response = client.post(
        "/signup",
        data={
            "name": "Test User",
            "email": "test@example.com",
            "password": "StrongPassword1!",
        },
    )

    assert response.status_code == 400
