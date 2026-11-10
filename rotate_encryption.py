"""Re-encrypt stored analysis data under the configured active key version."""
from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from database import DATABASE_PATH, _connect, initialize_database
from security import decrypt_text, encrypt_text


def rotate_encrypted_records(database_path: Path = DATABASE_PATH) -> int:
    """Rotate encrypted plan/evidence fields atomically; fail without rewriting on missing keys."""
    initialize_database(database_path)
    changed = 0
    with _connect(database_path) as connection:
        fields = [
            ("analyses", "id", "plan_ciphertext", "plan_nonce", "plan_key_version", "plan"),
            ("analyses", "id", "confirmed_ciphertext", "confirmed_nonce", "confirmed_key_version", "confirmed"),
            ("analyses", "id", "limitations_ciphertext", "limitations_nonce", "limitations_key_version", "limitations"),
            ("findings", "id", "payload_ciphertext", "payload_nonce", "payload_key_version", "payload"),
        ]
        for table, id_field, cipher_field, nonce_field, version_field, purpose in fields:
            rows = connection.execute(
                f"SELECT {id_field},{cipher_field},{nonce_field},{version_field} FROM {table} WHERE {cipher_field} IS NOT NULL"
            ).fetchall()
            for row in rows:
                aad = f"analysis:{row[id_field]}:{purpose}" if table == "analyses" else f"finding:{row[id_field]}:{purpose}"
                plaintext = decrypt_text(row[cipher_field], row[nonce_field], row[version_field], aad=aad)
                ciphertext, nonce, version = encrypt_text(plaintext, aad=aad)
                connection.execute(
                    f"UPDATE {table} SET {cipher_field}=?,{nonce_field}=?,{version_field}=? WHERE {id_field}=?",
                    (ciphertext, nonce, version, row[id_field]),
                )
                changed += 1
    return changed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DATABASE_PATH)
    args = parser.parse_args()
    count = rotate_encrypted_records(args.database)
    print(f"Re-encrypted {count} encrypted record fields under the active key version.")
