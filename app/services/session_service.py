from functools import wraps

from flask import abort, g, redirect, session, url_for

from app.models import get_user_for_session


def load_current_user():
    g.current_user = None
    user_id = session.get("user_id")
    token = session.get("session_token")
    if not user_id or not token:
        return

    row = get_user_for_session(user_id, token)
    if row is None:
        session.clear()
        return

    g.current_user = {
        "id": row[0],
        "name": row[1],
        "is_admin": bool(row[2]),
        "group_code": row[3],
    }


def is_logged_in():
    return g.get("current_user") is not None


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not is_logged_in():
            session.clear()
            return redirect(url_for("main.home"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped_view(*args, **kwargs):
        if not g.current_user["is_admin"]:
            abort(403)
        return view(*args, **kwargs)

    return wrapped_view
