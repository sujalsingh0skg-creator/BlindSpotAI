"""SQLite storage with owner-scoped reads/writes and encrypted plan data."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from security import decrypt_text, encrypt_text

DATABASE_PATH = Path(__file__).parent / "data" / "blindspot_ai.db"


class AuthorizationError(PermissionError):
    """Raised when a record is not owned by the authenticated account."""


def _connect(database_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 15000")
    return connection


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}


def initialize_database(database_path: Path = DATABASE_PATH) -> None:
    """Create schema and transactionally encrypt legacy plaintext records.

    Existing analyses stay ownerless until an authenticated user explicitly
    imports one; initialization never assigns legacy records arbitrarily.
    """
    migrated_sensitive_rows = False
    with _connect(database_path) as connection:
        connection.execute("PRAGMA secure_delete = ON")
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                email TEXT COLLATE NOCASE UNIQUE,
                display_name TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL,
                must_change_password INTEGER NOT NULL DEFAULT 0 CHECK (must_change_password IN (0,1)),
                role TEXT NOT NULL CHECK (role IN ('admin','user')),
                status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_activity TEXT,
                CHECK (role != 'admin' OR email IS NULL)
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                last_activity INTEGER NOT NULL,
                absolute_expires INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
            CREATE TABLE IF NOT EXISTS login_attempts (
                subject_hash TEXT NOT NULL,
                attempted_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_login_attempts_subject_time ON login_attempts(subject_hash, attempted_at);
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id INTEGER,
                event_type TEXT NOT NULL,
                target_ref TEXT,
                outcome TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at DESC);
            CREATE TABLE IF NOT EXISTS password_resets (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan TEXT NOT NULL DEFAULT '', domain_key TEXT NOT NULL, domain_name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, limitations TEXT NOT NULL DEFAULT '',
                owner_id INTEGER,
                plan_ciphertext BLOB, plan_nonce BLOB, plan_key_version TEXT,
                confirmed_ciphertext BLOB, confirmed_nonce BLOB, confirmed_key_version TEXT,
                limitations_ciphertext BLOB, limitations_nonce BLOB, limitations_key_version TEXT,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT, analysis_id INTEGER NOT NULL,
                requirement_id TEXT NOT NULL, title TEXT NOT NULL, payload TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Open',
                payload_ciphertext BLOB, payload_nonce BLOB, payload_key_version TEXT,
                FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
            );
        """)
        # Additive migration for databases created by previous project versions.
        user_columns = _columns(connection, "users")
        if "must_change_password" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0")
        analysis_columns = _columns(connection, "analyses")
        for name, definition in {
            "owner_id": "INTEGER REFERENCES users(id) ON DELETE SET NULL",
            "plan_ciphertext": "BLOB", "plan_nonce": "BLOB", "plan_key_version": "TEXT",
            "confirmed_ciphertext": "BLOB", "confirmed_nonce": "BLOB", "confirmed_key_version": "TEXT",
            "limitations_ciphertext": "BLOB", "limitations_nonce": "BLOB", "limitations_key_version": "TEXT",
        }.items():
            if name not in analysis_columns:
                connection.execute(f"ALTER TABLE analyses ADD COLUMN {name} {definition}")
        finding_columns = _columns(connection, "findings")
        for name, definition in {
            "payload_ciphertext": "BLOB", "payload_nonce": "BLOB", "payload_key_version": "TEXT",
        }.items():
            if name not in finding_columns:
                connection.execute(f"ALTER TABLE findings ADD COLUMN {name} {definition}")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_analyses_owner_created ON analyses(owner_id, created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_findings_analysis ON findings(analysis_id)")
        migrated_sensitive_rows = _encrypt_legacy_rows(connection)
    if migrated_sensitive_rows:
        # Checkpoint and compact away historical plaintext pages after the
        # encryption transaction has committed.
        with _connect(database_path) as connection:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            connection.execute("VACUUM")
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def _encrypt_legacy_rows(connection: sqlite3.Connection) -> bool:
    legacy_analyses = connection.execute(
        "SELECT id, plan, limitations, plan_ciphertext, limitations_ciphertext FROM analyses "
        "WHERE (plan != '' AND plan_ciphertext IS NULL) OR (limitations != '' AND limitations_ciphertext IS NULL)"
    ).fetchall()
    legacy_findings = connection.execute(
        "SELECT id, analysis_id, payload FROM findings WHERE payload NOT IN ('', '{}') AND payload_ciphertext IS NULL"
    ).fetchall()
    if not legacy_analyses and not legacy_findings:
        return False
    for row in legacy_analyses:
        analysis_id = row["id"]
        if row["plan"] and row["plan_ciphertext"] is None:
            cipher, nonce, version = encrypt_text(row["plan"], aad=f"analysis:{analysis_id}:plan")
            connection.execute("UPDATE analyses SET plan_ciphertext=?, plan_nonce=?, plan_key_version=?, plan='' WHERE id=?", (cipher, nonce, version, analysis_id))
        if row["limitations"] and row["limitations_ciphertext"] is None:
            cipher, nonce, version = encrypt_text(row["limitations"], aad=f"analysis:{analysis_id}:limitations")
            connection.execute("UPDATE analyses SET limitations_ciphertext=?, limitations_nonce=?, limitations_key_version=?, limitations='' WHERE id=?", (cipher, nonce, version, analysis_id))
    for row in legacy_findings:
        cipher, nonce, version = encrypt_text(row["payload"], aad=f"finding:{row['id']}:payload")
        connection.execute("UPDATE findings SET payload_ciphertext=?, payload_nonce=?, payload_key_version=?, payload='' WHERE id=?", (cipher, nonce, version, row["id"]))
    return True


def _audit(connection: sqlite3.Connection, actor_id: int | None, event: str, target: str | None, outcome: str) -> None:
    connection.execute("INSERT INTO audit_logs(actor_id,event_type,target_ref,outcome) VALUES(?,?,?,?)", (actor_id, event, target, outcome))


def record_audit(event: str, actor_id: int | None = None, target: str | None = None, outcome: str = "success", database_path: Path = DATABASE_PATH) -> None:
    with _connect(database_path) as connection:
        _audit(connection, actor_id, event, target, outcome)


def _require_workspace_owner(connection: sqlite3.Connection, owner_id: int) -> None:
    owner = connection.execute("SELECT role,status FROM users WHERE id=?", (owner_id,)).fetchone()
    if not owner or owner["role"] != "user" or owner["status"] != "active":
        _audit(connection, owner_id if owner else None, "unauthorized_workspace_access", None, "denied")
        raise AuthorizationError("An active user workspace is required.")


def save_analysis(result: dict[str, Any], database_path: Path = DATABASE_PATH, *, owner_id: int) -> int:
    """Save encrypted plan/findings, associated to the authenticated owner."""
    initialize_database(database_path)
    with _connect(database_path) as connection:
        _require_workspace_owner(connection, owner_id)
        cursor = connection.execute(
            "INSERT INTO analyses (plan, domain_key, domain_name, limitations, owner_id) VALUES ('', ?, ?, '', ?)",
            (result["domain_key"], result["domain"], owner_id),
        )
        analysis_id = int(cursor.lastrowid)
        cipher, nonce, version = encrypt_text(result["plan"], aad=f"analysis:{analysis_id}:plan")
        connection.execute("UPDATE analyses SET plan_ciphertext=?,plan_nonce=?,plan_key_version=? WHERE id=?", (cipher, nonce, version, analysis_id))
        confirmed = json.dumps(result.get("confirmed_mentions", []), ensure_ascii=False)
        if confirmed != "[]":
            cipher, nonce, version = encrypt_text(confirmed, aad=f"analysis:{analysis_id}:confirmed")
            connection.execute("UPDATE analyses SET confirmed_ciphertext=?,confirmed_nonce=?,confirmed_key_version=? WHERE id=?", (cipher, nonce, version, analysis_id))
        limits = result.get("limitations", "")
        if limits:
            cipher, nonce, version = encrypt_text(limits, aad=f"analysis:{analysis_id}:limitations")
            connection.execute("UPDATE analyses SET limitations_ciphertext=?,limitations_nonce=?,limitations_key_version=? WHERE id=?", (cipher, nonce, version, analysis_id))
        for item in result["findings"]:
            cursor = connection.execute(
                "INSERT INTO findings (analysis_id, requirement_id, title, payload, status) VALUES (?,?,?,'',?)",
                (analysis_id, item["requirement_id"], item["title"], item.get("status", "Open")),
            )
            finding_id = int(cursor.lastrowid)
            payload = json.dumps(item, ensure_ascii=False)
            cipher, nonce, version = encrypt_text(payload, aad=f"finding:{finding_id}:payload")
            connection.execute("UPDATE findings SET payload_ciphertext=?,payload_nonce=?,payload_key_version=? WHERE id=?", (cipher, nonce, version, finding_id))
    return analysis_id


def _owned_analysis(connection: sqlite3.Connection, analysis_id: int, owner_id: int) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM analyses WHERE id=? AND owner_id=?", (analysis_id, owner_id)).fetchone()


def get_analysis(analysis_id: int, database_path: Path = DATABASE_PATH, *, owner_id: int) -> dict[str, Any] | None:
    initialize_database(database_path)
    with _connect(database_path) as connection:
        _require_workspace_owner(connection, owner_id)
        row = _owned_analysis(connection, analysis_id, owner_id)
        if row is None:
            _audit(connection, owner_id, "unauthorized_access", str(analysis_id), "denied")
            return None
        if row["plan_ciphertext"] is None:
            return None
        plan = decrypt_text(row["plan_ciphertext"], row["plan_nonce"], row["plan_key_version"], aad=f"analysis:{analysis_id}:plan")
        limitations = ""
        if row["limitations_ciphertext"] is not None:
            limitations = decrypt_text(row["limitations_ciphertext"], row["limitations_nonce"], row["limitations_key_version"], aad=f"analysis:{analysis_id}:limitations")
        confirmed_mentions = []
        if row["confirmed_ciphertext"] is not None:
            confirmed_mentions = json.loads(decrypt_text(row["confirmed_ciphertext"], row["confirmed_nonce"], row["confirmed_key_version"], aad=f"analysis:{analysis_id}:confirmed"))
        findings = []
        finding_rows = connection.execute("SELECT * FROM findings WHERE analysis_id=? ORDER BY id", (analysis_id,)).fetchall()
        for finding_row in finding_rows:
            if finding_row["payload_ciphertext"] is None:
                continue
            payload = json.loads(decrypt_text(finding_row["payload_ciphertext"], finding_row["payload_nonce"], finding_row["payload_key_version"], aad=f"finding:{finding_row['id']}:payload"))
            payload.update({"database_id": finding_row["id"], "status": finding_row["status"]})
            findings.append(payload)
        return {"analysis_id": row["id"], "owner_id": row["owner_id"], "plan": plan, "domain_key": row["domain_key"], "domain": row["domain_name"], "created_at": row["created_at"], "limitations": limitations, "confirmed_mentions": confirmed_mentions, "findings": findings}


def list_analyses(database_path: Path = DATABASE_PATH, *, owner_id: int) -> list[dict[str, Any]]:
    initialize_database(database_path)
    with _connect(database_path) as connection:
        _require_workspace_owner(connection, owner_id)
        rows = connection.execute("SELECT id, domain_name, created_at, owner_id FROM analyses WHERE owner_id=? ORDER BY id DESC", (owner_id,)).fetchall()
        results = []
        for row in rows:
            plan = connection.execute("SELECT plan_ciphertext,plan_nonce,plan_key_version FROM analyses WHERE id=?", (row["id"],)).fetchone()
            summary = ""
            if plan["plan_ciphertext"] is not None:
                summary = decrypt_text(plan["plan_ciphertext"], plan["plan_nonce"], plan["plan_key_version"], aad=f"analysis:{row['id']}:plan")
            results.append({"id": row["id"], "domain_name": row["domain_name"], "created_at": row["created_at"], "owner_id": row["owner_id"], "plan": summary})
    return results


def update_finding_status(finding_id: int, status: str, database_path: Path = DATABASE_PATH, *, owner_id: int) -> bool:
    if status not in {"Open", "In Progress", "Resolved"}:
        raise ValueError("Invalid finding status.")
    initialize_database(database_path)
    with _connect(database_path) as connection:
        _require_workspace_owner(connection, owner_id)
        cursor = connection.execute("UPDATE findings SET status=? WHERE id=? AND analysis_id IN (SELECT id FROM analyses WHERE owner_id=?)", (status, finding_id, owner_id))
        if cursor.rowcount == 0:
            _audit(connection, owner_id, "unauthorized_access", str(finding_id), "denied")
        return cursor.rowcount == 1


def delete_analysis(analysis_id: int, database_path: Path = DATABASE_PATH, *, owner_id: int) -> bool:
    initialize_database(database_path)
    with _connect(database_path) as connection:
        _require_workspace_owner(connection, owner_id)
        cursor = connection.execute("DELETE FROM analyses WHERE id=? AND owner_id=?", (analysis_id, owner_id))
        if cursor.rowcount == 0:
            _audit(connection, owner_id, "unauthorized_access", str(analysis_id), "denied")
        return cursor.rowcount == 1


def admin_user_rows(actor_id: int, search: str = "", status: str = "all", database_path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    """Return user metadata/counts, never plan or finding plaintext."""
    initialize_database(database_path)
    clauses, params = ["u.role='user'"], []
    if search.strip():
        clauses.append("(u.username LIKE ? OR u.email LIKE ?)")
        needle = f"%{search.strip()}%"; params.extend([needle, needle])
    if status in {"active", "disabled"}:
        clauses.append("u.status=?"); params.append(status)
    query = f"""
        SELECT u.id,u.username,u.email,u.status,u.created_at,u.last_activity,
               COUNT(DISTINCT a.id) AS plan_count, COUNT(DISTINCT a.id) AS session_count
        FROM users u LEFT JOIN analyses a ON a.owner_id=u.id
        WHERE {' AND '.join(clauses)} GROUP BY u.id ORDER BY u.created_at DESC
    """
    with _connect(database_path) as connection:
        _require_admin(connection, actor_id)
        return [dict(row) for row in connection.execute(query, params).fetchall()]


def _require_admin(connection: sqlite3.Connection, actor_id: int) -> None:
    actor = connection.execute("SELECT role,status FROM users WHERE id=?", (actor_id,)).fetchone()
    if not actor or actor["role"] != "admin" or actor["status"] != "active":
        _audit(connection, actor_id if actor else None, "unauthorized_admin_access", None, "denied")
        raise AuthorizationError("Administrator access required.")


def admin_encrypted_records(actor_id: int, user_id: int, database_path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    """Ciphertext-only view for admins; this function never decrypts content."""
    initialize_database(database_path)
    with _connect(database_path) as connection:
        _require_admin(connection, actor_id)
        return [dict(row) for row in connection.execute("""
            SELECT a.id AS analysis_id,a.domain_name,a.created_at,a.owner_id,
                   a.plan_ciphertext,a.plan_nonce,a.plan_key_version,
                   f.id AS finding_id,f.title,f.requirement_id,f.payload_ciphertext,f.payload_nonce,f.payload_key_version
            FROM analyses a LEFT JOIN findings f ON f.analysis_id=a.id
            WHERE a.owner_id=? ORDER BY a.id DESC,f.id
        """, (user_id,)).fetchall()]


def audit_rows(actor_id: int, limit: int = 200, database_path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    initialize_database(database_path)
    with _connect(database_path) as connection:
        _require_admin(connection, actor_id)
        return [dict(row) for row in connection.execute("""
            SELECT l.id,l.actor_id,u.username AS actor,l.event_type,l.target_ref,l.outcome,l.created_at
            FROM audit_logs l LEFT JOIN users u ON u.id=l.actor_id ORDER BY l.id DESC LIMIT ?
        """, (max(1, min(limit, 500)),)).fetchall()]


def assign_legacy_analysis(actor_id: int, analysis_id: int, user_id: int, database_path: Path = DATABASE_PATH) -> bool:
    """Explicitly assign a legacy unowned record after a human ownership decision."""
    initialize_database(database_path)
    with _connect(database_path) as connection:
        _require_admin(connection, actor_id)
        target = connection.execute("SELECT role,status FROM users WHERE id=?", (user_id,)).fetchone()
        if not target or target["role"] != "user" or target["status"] != "active":
            _audit(connection, actor_id, "legacy_analysis_assignment", str(analysis_id), "rejected")
            return False
        cursor = connection.execute("UPDATE analyses SET owner_id=? WHERE id=? AND owner_id IS NULL", (user_id, analysis_id))
        outcome = "success" if cursor.rowcount == 1 else "rejected"
        _audit(connection, actor_id, "legacy_analysis_assignment", f"analysis:{analysis_id}:user:{user_id}", outcome)
        return cursor.rowcount == 1


def unassigned_legacy_analyses(actor_id: int, database_path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    """List legacy record metadata only; never decrypt their contents."""
    initialize_database(database_path)
    with _connect(database_path) as connection:
        _require_admin(connection, actor_id)
        return [dict(row) for row in connection.execute("SELECT id,domain_name,created_at,plan_ciphertext FROM analyses WHERE owner_id IS NULL ORDER BY id")]
