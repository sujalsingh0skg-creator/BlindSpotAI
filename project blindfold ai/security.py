"""Password hashing and authenticated encryption helpers."""
from __future__ import annotations

import base64
import json
import os
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class SecurityConfigurationError(RuntimeError):
    """Raised when a required secret is missing or malformed."""


class EncryptedDataError(RuntimeError):
    """Raised when ciphertext cannot be authenticated or decrypted."""


_PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16)


def password_strength_error(password: str) -> str | None:
    if len(password) < 12 or len(password) > 256:
        return "Use a password between 12 and 256 characters."
    if not any(char.islower() for char in password) or not any(char.isupper() for char in password):
        return "Use a mix of uppercase and lowercase letters."
    if not any(char.isdigit() for char in password) or not any(not char.isalnum() for char in password):
        return "Include at least one number and one symbol."
    return None


def hash_password(password: str) -> str:
    return _PASSWORD_HASHER.hash(password)


def verify_password(encoded: str, password: str) -> bool:
    try:
        return _PASSWORD_HASHER.verify(encoded, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(encoded: str) -> bool:
    try:
        return _PASSWORD_HASHER.check_needs_rehash(encoded)
    except (VerificationError, InvalidHashError):
        return True


def _keyring() -> tuple[dict[str, bytes], str]:
    raw = os.environ.get("BLINDSPOT_ENCRYPTION_KEYS", "").strip()
    active = os.environ.get("BLINDSPOT_ACTIVE_KEY_VERSION", "").strip()
    if not raw or not active:
        raise SecurityConfigurationError(
            "Encrypted history needs BLINDSPOT_ENCRYPTION_KEYS and BLINDSPOT_ACTIVE_KEY_VERSION. "
            "See SECURITY.md for secure key generation and configuration."
        )
    try:
        encoded_keys: dict[str, Any] = json.loads(raw)
        keys = {str(version): base64.b64decode(value, validate=True) for version, value in encoded_keys.items()}
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        raise SecurityConfigurationError("BLINDSPOT_ENCRYPTION_KEYS must be a JSON object of base64-encoded keys.") from error
    if active not in keys or any(len(value) != 32 for value in keys.values()):
        raise SecurityConfigurationError("Each encryption key must decode to 32 bytes and include the active key version.")
    return keys, active


def encrypt_text(value: str, *, aad: str) -> tuple[bytes, bytes, str]:
    keys, active = _keyring()
    nonce = os.urandom(12)
    ciphertext = AESGCM(keys[active]).encrypt(nonce, value.encode("utf-8"), aad.encode("utf-8"))
    return ciphertext, nonce, active


def decrypt_text(ciphertext: bytes, nonce: bytes, version: str, *, aad: str) -> str:
    keys, _ = _keyring()
    key = keys.get(version)
    if key is None:
        raise SecurityConfigurationError(f"Encryption key version {version!r} is not configured; encrypted data was left unchanged.")
    try:
        return AESGCM(key).decrypt(bytes(nonce), bytes(ciphertext), aad.encode("utf-8")).decode("utf-8")
    except (InvalidTag, UnicodeDecodeError, ValueError) as error:
        raise EncryptedDataError("Encrypted data failed authentication and was not displayed.") from error
