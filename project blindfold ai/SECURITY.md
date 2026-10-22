# Authentication, encryption, and recovery

## First run and administrator account

The first application start creates the one private administrator only when no administrator exists. Public registration has no role field, reserves the `admin` username, and always creates a `user`. The private account logs in as **admin**; `ADMIN_NAME` is its display name. The application stores an Argon2id password hash. It never stores or displays the configured password. Changing the environment value later does not overwrite the existing account.

Copy `.env.example` to `.env`, set `BLINDSPOT_ENV_FILE` to a private env file, or inject the variables through a secrets manager. `.env` is ignored by Git. Set:

```text
ADMIN_NAME=Your Administrator Display Name
ADMIN_PASSWORD=YourUniqueStrongPassword9!
```

Use a unique administrator secret with at least 12 characters, uppercase and lowercase letters, a number, and a symbol. If the private bootstrap value is weaker, the first login is allowed only to reach a forced password-change screen; no admin dashboard or user workspace is available until a strong replacement is set. The reserved login name is `admin`; the name variable is a display name. To change the password later, sign in as admin, re-enter the current password in **Administrator password**, then set the new value. This changes the database hash and revokes existing administrator sessions. Do not edit the environment password expecting an already-provisioned account to change.

If the admin account is absent and either administrator variable is missing, startup stops with setup instructions. No public administrator registration or role-promotion interface exists.

## Encryption key generation and storage

BlindSpot AI encrypts plan text, limitations, confirmed requirement mentions, and complete finding payloads with AES-256-GCM. Each field uses a random 96-bit nonce and authenticated additional data bound to its record ID and field. Authentication failures are rejected. Ciphertext, nonce, and key version are stored in SQLite. The username, email, status, timestamps, domain, requirement identifiers, finding titles, and status remain metadata and are not encrypted.

Generate a fresh random 32-byte key (do not use the administrator password):

```powershell
python -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

Put the output in private environment configuration:

```text
BLINDSPOT_ENCRYPTION_KEYS={"v1":"PASTE_BASE64_OUTPUT_HERE"}
BLINDSPOT_ACTIVE_KEY_VERSION=v1
```

For a `.env` file, quote the JSON value as shown in `.env.example`. Keep the key outside the database and source tree, restrict access to the `.env` file using operating-system permissions, and preferably use a secrets manager. On Windows, this app also checks `%LOCALAPPDATA%\BlindSpotAI\secrets.env` when no project `.env` exists. Make a separately encrypted offline backup of the key and record its version. A database backup without its matching key cannot recover encrypted content; a key without the database cannot recover deleted content. Do not rotate, discard, or overwrite the only key backup before verifying a restored copy.

### Key rotation

1. Back up the database and every configured encryption key.
2. Add a newly generated key as a second entry in `BLINDSPOT_ENCRYPTION_KEYS` and set `BLINDSPOT_ACTIVE_KEY_VERSION` to its new version. Keep the prior version configured so old records can be decrypted.
3. Stop the app, then run `python rotate_encryption.py`. The tool decrypts and re-encrypts encrypted fields in one SQLite transaction. A missing key or invalid authentication tag aborts the transaction without replacing ciphertext.
4. Verify the output and test a restored database. Only then remove the retired key from the active secret configuration and retain its protected backup according to your recovery policy.

If a key is missing, invalid, or the ciphertext is tampered with, reads fail closed. Data is not decrypted as garbage and initialization does not clear ciphertext. Restore the correct key/version or recover the verified backup; do not create a new key with the same version to try to open old data.

## Existing database migration and ownership

The current project database had 28 analyses and 257 findings in its pre-auth schema. On first startup after the encryption key is configured, initialization adds user/session/audit tables and owner and ciphertext columns. It encrypts the old plan, limitations, and finding payload fields in a database transaction, blanks the old plaintext fields, then checkpoints and compacts the SQLite file. If the key is missing or malformed, the encryption migration fails before changing those legacy values. Keep the app stopped during first migration and keep a separate encrypted backup of the original database until verification is complete; the original unencrypted backup contains sensitive plan text and should be securely removed once no longer needed.

Old records have no trustworthy account owner. They remain explicitly **unassigned** (`owner_id IS NULL`), encrypted, and hidden from user workspaces. The admin dashboard shows only their IDs, domain/date metadata, and encrypted ciphertext. An administrator can manually assign a specific legacy record to a user only after confirming ownership from an independent source. This action is audited. No legacy record is silently assigned to the admin or to the first registrant. New analyses get their owner from the authenticated session on the server.

To back up an SQLite database consistently, stop the application and use SQLite's backup API or make a file copy while the application is stopped. Store the backup on an encrypted volume with access restricted to the operator. Back up the matching keyring separately. Recovery consists of restoring the database and the matching key versions, then starting the application; do not run a migration or key rotation against the only backup.

## Administrator visibility and password recovery

The administrator dashboard can see usernames, email addresses, account status, account creation and last-activity timestamps, counts of saved analyses, security audit metadata, and base64 ciphertext/nonce/key-version values. It cannot see user plan text, finding evidence payloads, or report plaintext through the admin UI or admin database functions. It does not show password hashes. This app currently has no separate chat/conversation store; analyses and findings are the encrypted workspace records.

An administrator can disable/reactivate user accounts and initiate a one-time password reset code. Reset delivery is disabled until authenticated SMTP settings are configured. The code is emailed directly to the registered user, stored only as a hash, expires in one hour, and is invalidated after use. The administrator UI never receives the code. Reset invalidates that user's existing sessions. Admins cannot enter another user's workspace, change roles, or impersonate a user through the UI.

Audit logs contain event names, actor IDs/usernames, numeric target references, outcomes, and timestamps. They exclude passwords, reset codes, plan/chat plaintext, encryption keys, and session tokens. Administrator access to audit and user metadata is enforced in backend query functions.

## Session, transport, and deployment limits

The app stores an opaque random session token in Streamlit's per-browser server-side session state and only its SHA-256 digest in the database. Authentication replaces any prior session for that account. Sessions expire after 30 minutes of inactivity or 12 hours absolute; each rerun rechecks the account status, and deactivation deletes sessions. Login attempts are throttled to five failures per normalized account identifier per 15 minutes. Login errors are generic. Streamlit's XSRF and CORS protections are enabled in `.streamlit/config.toml`.

Streamlit does not expose application controls here for setting a custom HttpOnly/Secure/SameSite authentication cookie or for implementing a conventional form-token CSRF flow. Its session is tied to Streamlit's websocket/browser session, and state-changing actions use Streamlit's own widget protocol. Deploy only behind HTTPS, keep Streamlit and its reverse proxy current, and configure the proxy to reject untrusted origins. Do not expose the development server directly to the public internet for production use. Session revocation takes effect on the next application rerun/request.

Application encryption protects a copied database only while its keys remain separate. It does **not** protect plaintext from an administrator who also controls the server, process environment, source code, or runtime: that operator can alter the app to capture content or read keys. This implementation does not claim protection against that level of server control.
