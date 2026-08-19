import psycopg2

from app.models.db import execute, get_conn


def add_user(name, email, password, admin=False, group_code=""):
    try:
        cursor = execute(
            """
            INSERT INTO users (name, email, password, admin, group_code)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (name, email, password, admin, group_code),
            commit=True,
        )
        row = cursor.fetchone()
        return row[0] if row else None
    except psycopg2.IntegrityError:
        return None
    except psycopg2.Error:
        return None


def get_user_by_email(email):
    try:
        row = execute(
            "SELECT id, password FROM users WHERE email = %s",
            (email,),
        ).fetchone()
        return row
    except psycopg2.Error:
        return None


def create_invite_link(admin_user_id, group_code, invite_token):
    try:
        cursor = execute(
            """
            INSERT INTO "groupInvites" (admin_user_id, group_code, invite_token)
            SELECT id, group_code, %s
            FROM users
            WHERE id = %s AND group_code = %s AND admin = TRUE
            RETURNING id
            """,
            (invite_token, admin_user_id, group_code),
            commit=True,
        )
        row = cursor.fetchone()
        return row[0] if row else None
    except psycopg2.IntegrityError:
        return None
    except psycopg2.Error:
        return None


def get_invite_link(invite_token):
    try:
        row = execute(
            """
            SELECT id, admin_user_id, group_code, invite_token, used
            FROM "groupInvites" invites
            WHERE invite_token = %s
              AND EXISTS (
                  SELECT 1
                  FROM users admins
                  WHERE admins.id = invites.admin_user_id
                    AND admins.group_code = invites.group_code
                    AND admins.admin = TRUE
              )
            """,
            (invite_token,),
        ).fetchone()
        return row
    except psycopg2.Error:
        return None


def add_invited_user(name, email, password, invite_token):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT invites.id, invites.group_code
            FROM "groupInvites" invites
            JOIN users admins
              ON admins.id = invites.admin_user_id
             AND admins.group_code = invites.group_code
             AND admins.admin = TRUE
            WHERE invites.invite_token = %s AND invites.used = FALSE
            FOR UPDATE OF invites
            """,
            (invite_token,),
        )
        invite = cursor.fetchone()
        if invite is None:
            conn.rollback()
            return None

        invite_id, group_code = invite
        cursor.execute(
            """
            INSERT INTO users (name, email, password, admin, group_code)
            VALUES (%s, %s, %s, FALSE, %s)
            RETURNING id
            """,
            (name, email, password, group_code),
        )
        new_user_id = cursor.fetchone()[0]
        cursor.execute(
            """
            UPDATE "groupInvites"
            SET used = TRUE, used_by_user_id = %s, used_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (new_user_id, invite_id),
        )
        conn.commit()
        return new_user_id
    except psycopg2.IntegrityError:
        conn.rollback()
        return None
    except psycopg2.Error:
        conn.rollback()
        return None


def set_session_token(user_id, token):
    try:
        cursor = execute(
            "UPDATE users SET session_token = %s WHERE id = %s",
            (token, user_id),
            commit=True,
        )
        return cursor.rowcount
    except psycopg2.Error:
        return 0


def get_user_for_session(user_id, token):
    try:
        row = execute(
            """
            SELECT id, name, admin, group_code
            FROM users
            WHERE id = %s AND session_token = %s
            """,
            (user_id, token),
        ).fetchone()
        return row
    except psycopg2.Error:
        return None


def clear_session_token(user_id, token):
    try:
        cursor = execute(
            """
            UPDATE users
            SET session_token = NULL
            WHERE id = %s AND session_token = %s
            """,
            (user_id, token),
            commit=True,
        )
        return cursor.rowcount
    except psycopg2.Error:
        return 0
