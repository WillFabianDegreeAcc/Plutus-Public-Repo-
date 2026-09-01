import os

from dotenv import load_dotenv
from flask import Flask
from flask_minify import Minify
from flask_wtf.csrf import CSRFProtect

load_dotenv()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=True,
    )
    csrf.init_app(app)
    Minify(app=app, html=False, js=True, cssless=True, static=True)

    @app.after_request
    def add_security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'self'; form-action 'self'; "
            "frame-ancestors 'none'; object-src 'none'"
        )
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), geolocation=(), microphone=()"
        )
        return response

    from app.models import init_db

    init_db()

    from app.error_handlers import bp as errors_bp
    from app.main_routes import bp as main_bp
    from app.services.session_service import load_current_user

    app.register_blueprint(main_bp)
    app.register_blueprint(errors_bp)
    app.before_request(load_current_user)

    return app


__all__ = ["create_app"]
