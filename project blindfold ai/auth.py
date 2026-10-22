"""Account provisioning, registration, authentication, sessions and recovery."""
from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
import time
from typing import Any

from database import DATABASE_PATH, _audit, _connect, initialize_database
from security import hash_password, password_needs_rehash, password_strength_error, verify_password

IDLE_TIMEOUT_SECONDS = 30 * 60
ABSOLUTE_TIMEOUT_SECONDS = 12 * 60 * 60
LOGIN_WINDOW_SECONDS = 15 * 60
MAX_LOGIN_ATTEMPTS = 5
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class AuthSetupError(RuntimeError):
    """Raised when private administrator setup is incomplete."""


def _now() -> int:
    return int(time.time())


def _normalize_identifier(identifier: str) -> str:
    return identifier.strip().casefold()


def _subject_hash(identifier: str) -> str:
    return hashlib.sha256(_normalize_identifier(identifier).encode("utf-8")).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def bootstrap_admin(database_path=DATABASE_PATH) -> int:
    """Create exactly one initial admin; never mutate an existing admin."""
    initialize_database(database_path)
    with _connect(database_path) as connection:
        found = connection.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
        if found:
            return int(found["id"])
        import os
        admin_name = os.environ.get("ADMIN_NAME", "").strip()
        admin_password = os.environ.get("ADMIN_PASSWORD", "")
        if not admin_name or not admin_password:
            raise AuthSetupError(
                "No administrator exists. Set ADMIN_NAME and ADMIN_PASSWORD privately, then restart. "
                "See SECURITY.md; public administrator registration is disabled."
            )
        # If the operator supplies a weak initial bootstrap secret, permit
        # one login only to let them replace it immediately. App routes gate
        # every dashboard until this account flag has been cleared.
        must_change = int(password_strength_error(admin_password) is not None)
        connection.execute(
            "INSERT INTO users(username,email,display_name,password_hash,must_change_password,role,status) VALUES('admin',NULL,?,?,?,'admin','active')",
            (admin_name[:80], hash_password(admin_password), must_change),
        )
        admin_id = connection.execute("SELECT id FROM users WHERE username='admin'").fetchone()[0]
        _audit(connection, admin_id, "admin_bootstrapped", "admin", "success")
        return int(admin_id)


def register_user(username: str, email: str, password: str, confirmation: str, *, role: str = "user", database_path=DATABASE_PATH) -> int:
    """Validate and register a normal user. Privilege input is rejected."""
    if role != "user":
        raise ValueError("Public registration can create user accounts only.")
    username = username.strip()
    normalized_email = email.strip().casefold()
    if not USERNAME_RE.fullmatch(username) or username.casefold() == "admin":
        raise ValueError("Username must be 3–32 letters, numbers, dots, dashes, or underscores; 'admin' is reserved.")
    if len(normalized_email) > 254 or not EMAIL_RE.fullmatch(normalized_email):
        raise ValueError("Enter a valid email address.")
    if password != confirmation:
        raise ValueError("Passwords do not match.")
    strength_error = password_strength_error(password)
    if strength_error:
        raise ValueError(strength_error)
    initialize_database(database_path)
    try:
        with _connect(database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO users(username,email,display_name,password_hash,role,status) VALUES(?,?,?,?,'user','active')",
                (username, normalized_email, username, hash_password(password)),
            )
            user_id = int(cursor.lastrowid)
            _audit(connection, user_id, "user_registered", str(user_id), "success")
            return user_id
    except sqlite3.IntegrityError as error:
        message = str(error).lower()
        if "username" in message:
            raise ValueError("That username is already in use.") from error
        if "email" in message:
            raise ValueError("That email address is already in use.") from error
        raise ValueError("Registration could not be completed.") from error


def authenticate(identifier: str, password: str, *, database_path=DATABASE_PATH) -> dict[str, Any] | None:
    """Authenticate with generic errors and per-identifier throttling."""
    initialize_database(database_path)
    now, subject = _now(), _subject_hash(identifier)
    with _connect(database_path) as connection:
        connection.execute("DELETE FROM login_attempts WHERE attempted_at < ?", (now - LOGIN_WINDOW_SECONDS,))
        attempts = connection.execute("SELECT COUNT(*) FROM login_attempts WHERE subject_hash=? AND attempted_at>=?", (subject, now - LOGIN_WINDOW_SECONDS)).fetchone()[0]
        row = connection.execute(
            "SELECT * FROM users WHERE username=? COLLATE NOCASE OR email=? COLLATE NOCASE",
            (_normalize_identifier(identifier), _normalize_identifier(identifier)),
        ).fetchone()
        if attempts >= MAX_LOGIN_ATTEMPTS:
            if row:
                _audit(connection, row["id"], "login_failed", str(row["id"]), "rate_limited")
            return None
        valid = bool(row and row["status"] == "active" and verify_password(row["password_hash"], password))
        # Spend a comparable Argon2 operation on unknown accounts.
        if row is None:
            verify_password(_DUMMY_HASH, password)
        if not valid:
            connection.execute("INSERT INTO login_attempts(subject_hash,attempted_at) VALUES(?,?)", (subject, now))
            _audit(connection, row["id"] if row else None, "login_failed", str(row["id"]) if row else "unknown", "failure")
            return None
        connection.execute("DELETE FROM login_attempts WHERE subject_hash=?", (subject,))
        if password_needs_rehash(row["password_hash"]):
            connection.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(password), row["id"]))
        connection.execute("UPDATE users SET last_activity=CURRENT_TIMESTAMP WHERE id=?", (row["id"],))
        _audit(connection, row["id"], "login_succeeded", str(row["id"]), "success")
        return {"id": row["id"], "username": row["username"], "display_name": row["display_name"], "role": row["role"], "status": row["status"], "must_change_password": row["must_change_password"]}


_DUMMY_HASH = hash_password("Not-a-real-password-7!")


def create_session(user_id: int, *, database_path=DATABASE_PATH) -> str:
    """Create an opaque random session token; only its digest is persisted."""
    token = secrets.token_urlsafe(32)
    now = _now()
    initialize_database(database_path)
    with _connect(database_path) as connection:
        connection.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        connection.execute("INSERT INTO sessions(token_hash,user_id,created_at,last_activity,absolute_expires) VALUES(?,?,?,?,?)", (_token_hash(token), user_id, now, now, now + ABSOLUTE_TIMEOUT_SECONDS))
    return token


def validate_session(token: str | None, *, database_path=DATABASE_PATH) -> dict[str, Any] | None:
    if not token:
        return None
    now = _now()
    initialize_database(database_path)
    with _connect(database_path) as connection:
        row = connection.execute("""
            SELECT s.*,u.id,u.username,u.display_name,u.role,u.status,u.must_change_password
            FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?
        """, (_token_hash(token),)).fetchone()
        if not row:
            return None
        if row["status"] != "active" or now - row["last_activity"] > IDLE_TIMEOUT_SECONDS or now >= row["absolute_expires"]:
            connection.execute("DELETE FROM sessions WHERE token_hash=?", (_token_hash(token),))
            _audit(connection, row["id"], "session_expired_or_revoked", str(row["id"]), "blocked")
            return None
        connection.execute("UPDATE sessions SET last_activity=? WHERE token_hash=?", (now, _token_hash(token)))
        connection.execute("UPDATE users SET last_activity=CURRENT_TIMESTAMP WHERE id=?", (row["id"],))
        return {"id": row["id"], "username": row["username"], "display_name": row["display_name"], "role": row["role"], "status": row["status"], "must_change_password": row["must_change_password"]}


def logout(token: str | None, *, database_path=DATABASE_PATH) -> None:
    if not token:
        return
    with _connect(database_path) as connection:
        row = connection.execute("SELECT user_id FROM sessions WHERE token_hash=?", (_token_hash(token),)).fetchone()
        connection.execute("DELETE FROM sessions WHERE token_hash=?", (_token_hash(token),))
        if row:
            _audit(connection, row["user_id"], "logout", str(row["user_id"]), "success")


def set_account_status(actor_id: int, user_id: int, status: str, *, database_path=DATABASE_PATH) -> bool:
    if status not in {"active", "disabled"}:
        raise ValueError("Invalid account status.")
    initialize_database(database_path)
    with _connect(database_path) as connection:
        actor = connection.execute("SELECT role,status FROM users WHERE id=?", (actor_id,)).fetchone()
        if not actor or actor["role"] != "admin" or actor["status"] != "active":
            _audit(connection, actor_id if actor else None, "account_status_change", str(user_id), "unauthorized")
            raise PermissionError("Administrator access required.")
        target = connection.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
        if not target or target["role"] != "user":
            _audit(connection, actor_id, "account_status_change", str(user_id), "rejected")
            return False
        connection.execute("UPDATE users SET status=? WHERE id=?", (status, user_id))
        if status == "disabled":
            connection.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        _audit(connection, actor_id, "account_status_change", str(user_id), status)
        return True


def create_password_reset(actor_id: int, user_id: int, *, database_path=DATABASE_PATH) -> str | None:
    """Issue one time, one hour reset secret. Only its digest is stored."""
    raw = secrets.token_urlsafe(32)
    initialize_database(database_path)
    with _connect(database_path) as connection:
        actor = connection.execute("SELECT role,status FROM users WHERE id=?", (actor_id,)).fetchone()
        if not actor or actor["role"] != "admin" or actor["status"] != "active":
            _audit(connection, actor_id if actor else None, "password_reset_initiated", str(user_id), "unauthorized")
            raise PermissionError("Administrator access required.")
        row = connection.execute("SELECT role,status FROM users WHERE id=?", (user_id,)).fetchone()
        if not row or row["role"] != "user" or row["status"] != "active":
            _audit(connection, actor_id, "password_reset_initiated", str(user_id), "rejected")
            return None
        connection.execute("DELETE FROM password_resets WHERE user_id=?", (user_id,))
        connection.execute("INSERT INTO password_resets(token_hash,user_id,expires_at) VALUES(?,?,?)", (_token_hash(raw), user_id, _now() + 3600))
        _audit(connection, actor_id, "password_reset_initiated", str(user_id), "success")
    return raw


def complete_password_reset(token: str, password: str, confirmation: str, *, database_path=DATABASE_PATH) -> bool:
    if password != confirmation:
        raise ValueError("Passwords do not match.")
    error = password_strength_error(password)
    if error:
        raise ValueError(error)
    initialize_database(database_path)
    with _connect(database_path) as connection:
        row = connection.execute("SELECT user_id,expires_at FROM password_resets WHERE token_hash=?", (_token_hash(token),)).fetchone()
        if not row or row["expires_at"] <= _now():
            if row:
                connection.execute("DELETE FROM password_resets WHERE token_hash=?", (_token_hash(token),))
            _audit(connection, None, "password_reset_failed", None, "failure")
            return False
        user_id = row["user_id"]
        connection.execute("UPDATE users SET password_hash=?,must_change_password=0 WHERE id=?", (hash_password(password), user_id))
        connection.execute("DELETE FROM password_resets WHERE user_id=?", (user_id,))
        connection.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        _audit(connection, user_id, "password_reset_completed", str(user_id), "success")
        return True


def change_admin_password(admin_id: int, current_password: str, new_password: str, confirmation: str, *, database_path=DATABASE_PATH) -> None:
    if new_password != confirmation:
        raise ValueError("Passwords do not match.")
    error = password_strength_error(new_password)
    if error:
        raise ValueError(error)
    initialize_database(database_path)
    with _connect(database_path) as connection:
        row = connection.execute("SELECT role,password_hash FROM users WHERE id=? AND status='active'", (admin_id,)).fetchone()
        if not row or row["role"] != "admin" or not verify_password(row["password_hash"], current_password):
            _audit(connection, admin_id if row else None, "admin_password_change", str(admin_id), "rejected")
            raise PermissionError("Administrator access and the current password are required.")
        connection.execute("UPDATE users SET password_hash=?,must_change_password=0 WHERE id=?", (hash_password(new_password), admin_id))
        connection.execute("DELETE FROM sessions WHERE user_id=?", (admin_id,))
        _audit(connection, admin_id, "admin_password_change", str(admin_id), "success")


def verify_current_password(user_id: int, password: str, *, database_path=DATABASE_PATH) -> bool:
    with _connect(database_path) as connection:
        row = connection.execute("SELECT password_hash FROM users WHERE id=? AND status='active'", (user_id,)).fetchone()
        return bool(row and verify_password(row["password_hash"], password))


def revoke_password_reset(token: str, *, database_path=DATABASE_PATH) -> None:
    with _connect(database_path) as connection:
        connection.execute("DELETE FROM password_resets WHERE token_hash=?", (_token_hash(token),))
