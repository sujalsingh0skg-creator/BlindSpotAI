from __future__ import annotations

import json
import base64
import sqlite3
from pathlib import Path

import pytest

import auth
from analyzer import analyze_plan
from auth import (
    AuthSetupError, authenticate, bootstrap_admin, change_admin_password, complete_password_reset,
    create_password_reset, create_session, register_user, set_account_status,
    logout, validate_session,
)
from database import (
    AuthorizationError, admin_encrypted_records, admin_user_rows, audit_rows,
    assign_legacy_analysis, delete_analysis, get_analysis, initialize_database, list_analyses,
    save_analysis, unassigned_legacy_analyses, update_finding_status,
)
from report_generator import report_csv, report_html, report_json
from security import EncryptedDataError, SecurityConfigurationError
from rotate_encryption import rotate_encrypted_records

PASSWORD = "UserTestPassword8!"


@pytest.fixture
def account_db(tmp_path: Path):
    path = tmp_path / "accounts.db"
    initialize_database(path)
    bootstrap_admin(path)
    admin = authenticate("admin", "TestAdminPassword9!", database_path=path)
    assert admin and admin["role"] == "admin"
    alice_id = register_user("alice_user", "alice@example.test", PASSWORD, PASSWORD, database_path=path)
    bob_id = register_user("bob_user", "bob@example.test", PASSWORD, PASSWORD, database_path=path)
    return path, admin["id"], alice_id, bob_id


def _save(path: Path, owner_id: int, plan: str):
    return save_analysis(analyze_plan(plan, "website_deployment"), path, owner_id=owner_id)


def test_registration_login_hash_and_no_public_admin(account_db):
    path, admin_id, alice_id, _ = account_db
    assert authenticate("alice_user", PASSWORD, database_path=path)["id"] == alice_id
    assert authenticate("ALICE@example.test", PASSWORD, database_path=path)["id"] == alice_id
    assert authenticate("alice_user", "wrong", database_path=path) is None
    with sqlite3.connect(path) as connection:
        alice_hash = connection.execute("SELECT password_hash FROM users WHERE id=?", (alice_id,)).fetchone()[0]
        assert alice_hash.startswith("$argon2id$")
        assert PASSWORD not in alice_hash
        assert connection.execute("SELECT role FROM users WHERE id=?", (alice_id,)).fetchone()[0] == "user"
    with pytest.raises(ValueError):
        register_user("another_user", "another@example.test", PASSWORD, PASSWORD, role="admin", database_path=path)
    with pytest.raises(ValueError):
        register_user("admin", "admin@example.test", PASSWORD, PASSWORD, database_path=path)
    with pytest.raises(ValueError, match="already in use"):
        register_user("alice_user", "new@example.test", PASSWORD, PASSWORD, database_path=path)
    with pytest.raises(ValueError, match="already in use"):
        register_user("other_user", "alice@example.test", PASSWORD, PASSWORD, database_path=path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0] == 1


def test_admin_is_bootstrapped_once_and_requires_private_strong_configuration(tmp_path, monkeypatch):
    path = tmp_path / "bootstrap.db"
    initialize_database(path)
    monkeypatch.delenv("ADMIN_NAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    with pytest.raises(AuthSetupError, match="Set ADMIN_NAME"):
        bootstrap_admin(path)
    monkeypatch.setenv("ADMIN_NAME", "Provisioned Owner")
    monkeypatch.setenv("ADMIN_PASSWORD", "Weak pass")
    admin_id = bootstrap_admin(path)
    weak_login = authenticate("admin", "Weak pass", database_path=path)
    assert weak_login and weak_login["must_change_password"] == 1
    change_admin_password(admin_id, "Weak pass", "AReallyStrongAdmin9!", "AReallyStrongAdmin9!", database_path=path)
    monkeypatch.setenv("ADMIN_PASSWORD", "AReallyStrongAdmin9!")
    bootstrap_admin(path)
    monkeypatch.setenv("ADMIN_PASSWORD", "ChangedEnvironmentIgnored9!")
    bootstrap_admin(path)
    admin = authenticate("admin", "AReallyStrongAdmin9!", database_path=path)
    assert admin and admin["display_name"] == "Provisioned Owner" and admin["must_change_password"] == 0
    assert authenticate("admin", "ChangedEnvironmentIgnored9!", database_path=path) is None


def test_owner_scoped_history_status_delete_and_exports(account_db):
    path, _, alice, bob = account_db
    secret_a = "Alice private plan phrase"
    secret_b = "Bob private deployment phrase"
    alice_id = _save(path, alice, secret_a)
    bob_id = _save(path, bob, secret_b)
    alice_report = get_analysis(alice_id, path, owner_id=alice)
    assert alice_report and secret_a in alice_report["plan"]
    assert get_analysis(bob_id, path, owner_id=alice) is None
    assert [item["id"] for item in list_analyses(path, owner_id=alice)] == [alice_id]
    alice_finding = alice_report["findings"][0]["database_id"]
    bob_report = get_analysis(bob_id, path, owner_id=bob)
    bob_finding = bob_report["findings"][0]["database_id"]
    assert update_finding_status(bob_finding, "Resolved", path, owner_id=alice) is False
    assert delete_analysis(bob_id, path, owner_id=alice) is False
    assert update_finding_status(alice_finding, "Resolved", path, owner_id=alice) is True
    assert delete_analysis(alice_id, path, owner_id=alice) is True
    assert get_analysis(bob_id, path, owner_id=bob) is not None
    assert "password" not in report_json(bob_report).lower()
    assert "Bob private" in report_html(bob_report)
    assert "title,status,evidence_status" in report_csv(bob_report)
    assert get_analysis(bob_id, path, owner_id=alice) is None


def test_ciphertext_storage_admin_metadata_and_admin_reads_are_encrypted_only(account_db):
    path, admin_id, alice, _ = account_db
    secret = "SECRET-PLAN-TEXT-9f3c"
    analysis_id = _save(path, alice, secret)
    with sqlite3.connect(path) as connection:
        plan, plan_cipher, payload, finding_cipher = connection.execute(
            "SELECT plan,plan_ciphertext,(SELECT payload FROM findings WHERE analysis_id=analyses.id LIMIT 1),"
            "(SELECT payload_ciphertext FROM findings WHERE analysis_id=analyses.id LIMIT 1) FROM analyses WHERE id=?",
            (analysis_id,),
        ).fetchone()
        assert plan == "" and payload == ""
        assert secret.encode() not in plan_cipher and secret.encode() not in finding_cipher
    rows = admin_encrypted_records(admin_id, alice, path)
    assert rows and rows[0]["plan_ciphertext"]
    assert all("plan" not in key and "payload" not in key or "ciphertext" in key or "nonce" in key or "key_version" in key for key in rows[0])
    metadata = admin_user_rows(admin_id, "alice", "all", path)
    assert metadata[0]["email"] == "alice@example.test"
    assert metadata[0]["plan_count"] == 1
    with pytest.raises(AuthorizationError):
        admin_encrypted_records(alice, alice, path)
    with pytest.raises(AuthorizationError):
        admin_user_rows(alice, database_path=path)
    with pytest.raises(AuthorizationError):
        get_analysis(analysis_id, path, owner_id=admin_id)
    assert audit_rows(admin_id, 20, path)


def test_authenticated_owner_can_decrypt_and_tampering_is_rejected(account_db):
    path, _, alice, _ = account_db
    analysis_id = _save(path, alice, "Visible to the owning user only")
    report = get_analysis(analysis_id, path, owner_id=alice)
    assert report and report["plan"] == "Visible to the owning user only"
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE analyses SET plan_ciphertext=? WHERE id=?", (b"tampered", analysis_id))
    with pytest.raises(EncryptedDataError):
        get_analysis(analysis_id, path, owner_id=alice)


def test_missing_key_preserves_encrypted_records(account_db, monkeypatch):
    path, _, alice, _ = account_db
    analysis_id = _save(path, alice, "Do not destroy this encrypted plan")
    with sqlite3.connect(path) as connection:
        before = connection.execute("SELECT plan_ciphertext,plan_nonce FROM analyses WHERE id=?", (analysis_id,)).fetchone()
    monkeypatch.delenv("BLINDSPOT_ENCRYPTION_KEYS")
    with pytest.raises(SecurityConfigurationError):
        get_analysis(analysis_id, path, owner_id=alice)
    with sqlite3.connect(path) as connection:
        after = connection.execute("SELECT plan_ciphertext,plan_nonce FROM analyses WHERE id=?", (analysis_id,)).fetchone()
    assert before == after


def test_encryption_key_rotation_preserves_readability(account_db, monkeypatch):
    path, _, alice, _ = account_db
    analysis_id = _save(path, alice, "Rotate this private plan safely")
    old_key = base64.b64encode(b"0123456789abcdef0123456789abcdef").decode("ascii")
    new_key = base64.b64encode(b"abcdef0123456789abcdef0123456789").decode("ascii")
    monkeypatch.setenv("BLINDSPOT_ENCRYPTION_KEYS", json.dumps({"test-v1": old_key, "test-v2": new_key}))
    monkeypatch.setenv("BLINDSPOT_ACTIVE_KEY_VERSION", "test-v2")
    assert rotate_encrypted_records(path) >= 1
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT plan_key_version FROM analyses WHERE id=?", (analysis_id,)).fetchone()[0] == "test-v2"
    assert get_analysis(analysis_id, path, owner_id=alice)["plan"] == "Rotate this private plan safely"


def test_legacy_migration_preserves_rows_and_leaves_them_unassigned(tmp_path):
    path = tmp_path / "old-schema.db"
    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TABLE analyses(id INTEGER PRIMARY KEY AUTOINCREMENT,plan TEXT NOT NULL,domain_key TEXT NOT NULL,domain_name TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,limitations TEXT NOT NULL);
            CREATE TABLE findings(id INTEGER PRIMARY KEY AUTOINCREMENT,analysis_id INTEGER NOT NULL,requirement_id TEXT NOT NULL,title TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'Open',FOREIGN KEY(analysis_id) REFERENCES analyses(id) ON DELETE CASCADE);
            INSERT INTO analyses(plan,domain_key,domain_name,limitations) VALUES('LEGACY PLAN EXACT TEXT','website_deployment','Website Deployment','Legacy limitations');
            INSERT INTO findings(analysis_id,requirement_id,title,payload) VALUES(1,'x','Requirement','{"supporting_phrase":"LEGACY EVIDENCE EXACT TEXT"}');
        """)
    initialize_database(path)
    with sqlite3.connect(path) as connection:
        row = connection.execute("SELECT owner_id,plan,plan_ciphertext,limitations FROM analyses WHERE id=1").fetchone()
        finding = connection.execute("SELECT payload,payload_ciphertext FROM findings WHERE id=1").fetchone()
        assert row[0] is None and row[1] == "" and row[2] and row[3] == ""
        assert finding[0] == "" and finding[1]
    admin = bootstrap_admin(path)
    user_id = register_user("legacy_owner", "legacy@example.test", PASSWORD, PASSWORD, database_path=path)
    assert get_analysis(1, path, owner_id=user_id) is None
    assert assign_legacy_analysis(admin, 1, user_id, path)
    legacy = get_analysis(1, path, owner_id=user_id)
    assert legacy and legacy["plan"] == "LEGACY PLAN EXACT TEXT"
    assert "LEGACY EVIDENCE EXACT TEXT" in legacy["findings"][0]["supporting_phrase"]
    assert list_analyses(path, owner_id=user_id)[0]["plan"] == "LEGACY PLAN EXACT TEXT"


def test_missing_encryption_key_does_not_alter_legacy_plaintext(tmp_path, monkeypatch):
    path = tmp_path / "legacy-no-key.db"
    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TABLE analyses(id INTEGER PRIMARY KEY AUTOINCREMENT,plan TEXT NOT NULL,domain_key TEXT NOT NULL,domain_name TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,limitations TEXT NOT NULL);
            CREATE TABLE findings(id INTEGER PRIMARY KEY AUTOINCREMENT,analysis_id INTEGER NOT NULL,requirement_id TEXT NOT NULL,title TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'Open');
            INSERT INTO analyses(plan,domain_key,domain_name,limitations) VALUES('DO NOT OVERWRITE','website_deployment','Website Deployment','legacy');
        """)
    monkeypatch.delenv("BLINDSPOT_ENCRYPTION_KEYS")
    with pytest.raises(SecurityConfigurationError):
        initialize_database(path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT plan,limitations FROM analyses WHERE id=1").fetchone() == ("DO NOT OVERWRITE", "legacy")
    monkeypatch.setenv("BLINDSPOT_ENCRYPTION_KEYS", '{"test-v1":"MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="}')
    initialize_database(path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT plan,plan_ciphertext FROM analyses WHERE id=1").fetchone()[0] == ""


def test_rate_limit_logout_expiration_and_deactivation(account_db, monkeypatch):
    path, admin_id, alice, _ = account_db
    analysis_id = _save(path, alice, "Disabled users lose workspace access")
    for _ in range(auth.MAX_LOGIN_ATTEMPTS):
        assert authenticate("alice_user", "wrong", database_path=path) is None
    assert authenticate("alice_user", PASSWORD, database_path=path) is None
    with sqlite3.connect(path) as connection:
        connection.execute("DELETE FROM login_attempts")
    token = create_session(alice, database_path=path)
    assert validate_session(token, database_path=path)["id"] == alice
    logout(token, database_path=path)
    assert validate_session(token, database_path=path) is None
    token = create_session(alice, database_path=path)
    now = auth._now()
    monkeypatch.setattr(auth, "_now", lambda: now + auth.IDLE_TIMEOUT_SECONDS + 1)
    assert validate_session(token, database_path=path) is None
    monkeypatch.setattr(auth, "_now", lambda: now)
    token = create_session(alice, database_path=path)
    with pytest.raises(PermissionError):
        set_account_status(alice, alice, "disabled", database_path=path)
    assert set_account_status(admin_id, alice, "disabled", database_path=path)
    assert validate_session(token, database_path=path) is None
    with pytest.raises(AuthorizationError):
        get_analysis(analysis_id, path, owner_id=alice)
    assert authenticate("alice_user", PASSWORD, database_path=path) is None
    assert set_account_status(admin_id, alice, "active", database_path=path)


def test_secure_password_reset_is_one_time_and_revokes_sessions(account_db):
    path, admin_id, alice, _ = account_db
    token = create_session(alice, database_path=path)
    reset_code = create_password_reset(admin_id, alice, database_path=path)
    assert reset_code
    new_password = "AnotherValidPassword7!"
    assert complete_password_reset(reset_code, new_password, new_password, database_path=path)
    assert complete_password_reset(reset_code, new_password, new_password, database_path=path) is False
    assert validate_session(token, database_path=path) is None
    assert authenticate("alice_user", new_password, database_path=path)["id"] == alice


def test_admin_cannot_initiate_reset_or_access_audit_as_user(account_db):
    path, _, alice, _ = account_db
    with pytest.raises(PermissionError):
        create_password_reset(alice, alice, database_path=path)
    with pytest.raises(AuthorizationError):
        audit_rows(alice, database_path=path)


def test_legacy_assignment_requires_admin_and_explicit_target(account_db):
    path, admin_id, alice, _ = account_db
    with sqlite3.connect(path) as connection:
        cursor = connection.execute("INSERT INTO analyses(plan,domain_key,domain_name,limitations) VALUES(?,?,?,?)", ("A pre-account saved plan", "website_deployment", "Website Deployment", ""))
        legacy_id = cursor.lastrowid
    initialize_database(path)
    assert unassigned_legacy_analyses(admin_id, path)[0]["id"] == legacy_id
    with pytest.raises(AuthorizationError):
        assign_legacy_analysis(alice, legacy_id, alice, path)
    assert assign_legacy_analysis(admin_id, legacy_id, alice, path)
    assert unassigned_legacy_analyses(admin_id, path) == []
    assert get_analysis(legacy_id, path, owner_id=alice)["plan"] == "A pre-account saved plan"
