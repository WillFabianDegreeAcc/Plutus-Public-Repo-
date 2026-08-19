import uuid

from flask import session
from werkzeug.security import check_password_hash, generate_password_hash

from app.models import (
    add_invited_user,
    add_user,
    clear_session_token,
    create_invite_link as create_invite_link_model,
    get_invite_link,
    get_user_by_email,
    set_session_token,
)


def authenticate(email, password):
    row = get_user_by_email(email)
    if not row:
        return None

    user_id, password_hash = row
    return user_id if check_password_hash(password_hash, password) else None


def create_user(name, email, password):
    password_hash = generate_password_hash(password)
    group_code = uuid.uuid4().hex.upper()
    new_user_id = add_user(name, email, password_hash, True, group_code)
    return new_user_id


def create_invited_user(name, email, password, invite_token):
    password_hash = generate_password_hash(password)
    return add_invited_user(name, email, password_hash, invite_token)


def create_group_user(name, email, password, is_admin, group_code):
    password_hash = generate_password_hash(password)
    return add_user(name, email, password_hash, is_admin, group_code)


def create_invite_link(admin_user_id, group_code):
    invite_token = uuid.uuid4().hex
    invite_id = create_invite_link_model(admin_user_id, group_code, invite_token)
    if invite_id is None:
        return None
    return invite_token


def read_invite(invite_token):
    row = get_invite_link(invite_token)
    if not row:
        return None
    return {
        "id": row[0],
        "admin_user_id": row[1],
        "group_code": row[2],
        "token": row[3],
        "used": row[4],
    }


def start_session(user_id):
    token = uuid.uuid4().hex
    session.clear()
    session["user_id"] = user_id
    session["session_token"] = token
    session.permanent = True
    set_session_token(user_id, token)


def logout():
    user_id = session.get("user_id")
    token = session.get("session_token")
    clear_session_token(user_id=user_id, token=token)
    session.clear()
