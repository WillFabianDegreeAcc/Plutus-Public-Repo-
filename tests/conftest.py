import pytest

from app import create_app
from app.services import session_service


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setattr("app.models.init_db", lambda: True)

    test_app = create_app()
    test_app.config.update(
        TESTING=True,
        RATELIMIT_ENABLED=False,
        WTF_CSRF_ENABLED=False,
    )
    return test_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def log_in(monkeypatch):
    def log_in_user(client, *, admin=False):
        user = (1, "Test User", admin, "GROUP-1")
        monkeypatch.setattr(
            session_service,
            "get_user_for_session",
            lambda user_id, token: user
            if user_id == 1 and token == "valid-token"
            else None,
        )
        with client.session_transaction() as session:
            session["user_id"] = 1
            session["session_token"] = "valid-token"

    return log_in_user
