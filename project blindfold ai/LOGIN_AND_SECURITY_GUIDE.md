# BlindSpot AI Login and Security Guide

This guide explains how to sign in, register, use the private workspace, and understand the security protections in BlindSpot AI. It describes the current Streamlit application; it does not change application behavior.

For operator-only setup, key management, migration, rotation, backup, and deployment details, see [SECURITY.md](SECURITY.md). For the analysis engine and project architecture, see [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md).

## Opening BlindSpot AI

For a local installation, start the app from the project folder:

```powershell
streamlit run app.py
```

Open the local address printed by Streamlit, usually `http://localhost:8501`. Keep the computer and Streamlit process running while you use the app. If you were given a temporary public link, it works only while the host and tunnel process are running. A temporary tunnel address can change when it is restarted.

## Signing in

The sign-in panel asks for:

1. **Username or email** — users enter the username or email address they registered with. Administrators enter their administrator login name.
2. **Password** — passwords are case-sensitive.

After a successful sign-in, BlindSpot AI routes the account to the dashboard for its assigned role. There is no role selector on the login page.

The initial private administrator login name is **`admin`**. `ADMIN_NAME` is the administrator's display name; it is not the login name. An operator may privately provision additional administrator accounts with their own login names. Use the exact login name provided by the operator. Administrator passwords are private and are not displayed by the app or stored in recoverable plaintext.

Login errors are intentionally generic. If a correct password appears not to work, check the username, password case, keyboard layout, account status, and whether the account has been rate-limited. Ask the operator to verify the account rather than sharing a password in chat or email.

## Creating a user account

Choose **Create user account** on the login screen. Public registration creates a standard `user` account only. Administrator registration and self-promotion are not available.

Registration asks for a username, email address, password, and password confirmation. Usernames must be 3–32 letters, numbers, dots, dashes, or underscores. Usernames and email addresses must be unique. Passwords must be 12–256 characters and contain uppercase and lowercase letters, at least one number, and at least one symbol. The app checks these rules on the server before saving an account.

After registration, return to the login screen and sign in with the new username or email address and password.

## User workspace

The user workspace has two main views:

### Analyze plan

1. Choose a sample plan or **Custom plan**.
2. Describe the plan, including what is ready and what remains uncertain. At least 10 characters are required by the analysis engine.
3. Choose a domain or leave **Auto-detect** selected.
4. Select **Begin plan analysis**.
5. Review the findings, evidence, potential severity, recommendations, charts, and any available dependency relationships.

BlindSpot AI compares the text with local, editable checklists. It does not independently verify that tasks were completed. A finding is a potential gap in the evidence supplied, not proof that a safeguard or task is missing. Scores are heuristic impact-by-likelihood ratings, not probabilities or certifications.

When a saved finding offers a status control, its status can be changed to **Open**, **In Progress**, or **Resolved**. A **What-if analysis** describes a possible consequence for a selected potential gap; it is explanatory, not a prediction.

### History and reports

Open **History** to see analyses saved to your account. Select **Open report** to continue reviewing one, or **Delete** to remove one from your workspace. The report view supports filters for risk and evidence status and offers JSON, CSV, and HTML downloads.

Reports contain the plan and analysis details needed to explain findings. Treat downloaded reports as sensitive files and store or share them carefully.

Every workspace query checks the signed-in account's owner ID in backend database operations. Changing an analysis or finding ID in a URL, request, or browser state does not grant access to another user's record. Exports also use the authenticated owner's record.

## Administrator workspace

Administrator accounts open a separate admin dashboard. An administrator can:

- Search and filter registered user accounts.
- See usernames, email addresses, status, account creation and last-activity timestamps, and counts of saved analyses.
- Disable or reactivate user accounts.
- Initiate a one-time password reset for an active user, if authenticated email delivery is configured.
- Review security audit events.
- See encrypted workspace record fields and limited finding metadata.

The administrator view does not display password hashes or plaintext user plans, evidence, finding payloads, or reports. Encrypted fields are shown as ciphertext with their nonce and key version; some record metadata such as domain, date, requirement identifier, and finding title is visible. BlindSpot AI currently has no separate chat or message-history store.

Administrators cannot use the dashboard to impersonate users, enter a user's workspace, promote a public account, or retrieve a user's password. Backend authorization enforces administrator-only operations and user ownership checks.

An administrator can change their own password from the **Administrator password** section by entering the current password and a strong replacement. A weak bootstrap password requires a strong replacement before the admin dashboard becomes available. Changing the password in the environment after the first admin account has been created does not change that account's password.

## Password reset and account status

User password reset delivery requires the operator to configure authenticated SMTP settings. An administrator can initiate a reset from the user profile. A one-time code is sent to the email address registered to the user, expires after one hour, and is stored in the database only as a hash. The admin interface does not reveal the code. Completing a reset invalidates the user's existing sessions.

If reset email is unavailable, contact the application operator. The public registration and reset screens cannot create or reset an administrator account. Forgotten administrator passwords require operator-managed recovery; the stored password hash cannot be converted back into the original password.

If an administrator disables an account, its sessions are revoked. Protected actions re-check account status on subsequent requests/reruns. Re-enabling the account allows a new login but does not restore revoked sessions.

## Security protections in everyday use

- Passwords are hashed with Argon2id before storage. They are never stored as plaintext or reversibly encrypted values.
- Login errors do not disclose whether a username exists. Repeated failed attempts are rate-limited to five attempts per normalized identifier in a 15-minute window.
- Sessions expire after 30 minutes of inactivity or 12 hours maximum. Logging out revokes the current session.
- Session tokens are random and only their SHA-256 digests are stored in SQLite.
- Security events are audited without recording passwords, reset codes, encryption keys, session tokens, or plan/chat plaintext.
- Plans, limitations, confirmed requirement mentions, and full finding payloads are encrypted in SQLite with AES-256-GCM. Each encrypted value has a fresh nonce and key version; tampering causes decryption to fail.
- Encryption keys are held outside the database and source code in private environment configuration or a secrets manager.

Some account and record metadata remains visible in the database and administrator dashboard. For the precise encrypted-field list, migration behavior, key backup and rotation instructions, and Streamlit session limitations, consult [SECURITY.md](SECURITY.md).

## Existing records from before accounts

Records created before authentication do not have a trustworthy owner. They remain encrypted and unassigned; the app does not silently give them to the administrator or the first person who registers. The administrator can assign an individual legacy record only after confirming its owner from an independent source. That assignment is audited. Until assigned, legacy records are unavailable in user workspaces.

## Security boundary and deployment notes

Database encryption helps protect a copied database when the matching encryption key is kept separate. It does not protect plaintext from an operator who controls the server, application source, process environment, or runtime; that operator could change the software to capture plaintext or access the key. Application-level encryption does not provide protection against a hostile server administrator.

Streamlit uses its own browser/websocket session behavior. This app enables Streamlit's XSRF and CORS protections, but does not implement custom `HttpOnly`, `Secure`, or `SameSite` authentication cookies or a conventional form-token CSRF mechanism. Use HTTPS, keep the host and reverse proxy updated, restrict allowed origins, and do not expose a development server directly to the public internet for production use.

## Quick troubleshooting

| Problem | What to check |
| --- | --- |
| Login failed | Confirm the login name, password case, account status, and that the account is not rate-limited. Ask the operator to check admin provisioning without sending them your password. |
| Registration rejected | Check username rules, email format, password strength, matching confirmation, and whether the username/email is already registered. |
| Password reset unavailable | Reset email requires operator-configured SMTP. Ask the administrator to initiate the reset and confirm the registered email address is current. |
| Administrator dashboard is not available at first sign-in | A weak bootstrap password may require an immediate strong-password change. Follow the secure setup prompt. |
| Encrypted history cannot be opened | The matching key version may be missing or invalid, or ciphertext may have been tampered with. Stop and ask the operator to check the protected key backup; do not generate a replacement key with the same version. |
| Public link is unavailable | The local host or temporary tunnel may have stopped. Start the app and tunnel again and use the new tunnel URL if one is issued. |

