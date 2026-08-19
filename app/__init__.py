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
    csrf.init_app(app)
    Minify(app=app, html=False, js=True, cssless=True, static=True)

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
