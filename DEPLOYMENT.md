# BlindSpot AI — Deployment Guide (Streamlit Community Cloud)

This guide covers preparing, testing, and deploying **BlindSpot AI** on **Streamlit Community Cloud** while keeping existing authentication, encryption, and access-control protections intact.

---

## 1. Verified Architecture & Entry Point

- **Streamlit entry point:** `app.py`
- **Core modules:** `analyzer.py`, `domain_detector.py`, `risk_engine.py`, `dependency_engine.py`, `database.py`, `auth.py`, `security.py`, `mail_delivery.py`, `report_generator.py`, `rotate_encryption.py`
- **UI components (`components/`):** `__init__.py`, `dashboard.py`, `risk_cards.py`, `visualizations.py`
- **Knowledge bases (`knowledge_base/`):** `website_deployment.json`, `college_project.json`, `event_planning.json`
- **Automated tests (`tests/`):** `conftest.py`, `test_analyzer.py`, `test_auth_security.py`, `test_database.py`, `test_reports.py`, `test_risk_engine.py`, `test_visualizations.py`
- **Storage engine:** Local SQLite (`data/blindspot_ai.db`), initialized automatically on startup via `initialize_database()` and `bootstrap_admin()`.

> **Storage scope note:** BlindSpot AI uses **local SQLite only**. It does **not** include Azure SQL, Azure Blob Storage, or Power BI integrations.

---

## 2. Exact Dependencies (`requirements.txt`)

All imports across the codebase map to the Python standard library plus these packages in `requirements.txt`:

- `streamlit>=1.39,<2` — web dashboard & `st.secrets` runtime
- `pandas>=2.1,<3` — CSV export and chart aggregation
- `plotly>=5.24,<7` — risk distribution and dependency graph figures
- `networkx>=3.2,<4` — requirement dependency DAG construction
- `argon2-cffi>=23.1,<26` — Argon2id password hashing
- `cryptography>=42,<47` — AES-256-GCM authenticated encryption
- `python-dotenv>=1.0,<2` — local `.env` loading
- `pytest>=8.0,<9` — automated test runner for `tests/`

---

## 3. Required Environment Variables & Secrets

Never hardcode secrets or commit `.env` or `.streamlit/secrets.toml` to Git.

### Required for startup
| Variable | Purpose | Notes |
| --- | --- | --- |
| `ADMIN_NAME` | Display name for the initial private `admin` account | Used only when no admin exists yet in SQLite |
| `ADMIN_PASSWORD` | Initial password for login username `admin` | Must be 12–256 chars with upper, lower, digit, and symbol (or forced change on first login) |
| `BLINDSPOT_ENCRYPTION_KEYS` | JSON object of `{version: base64_32_byte_key}` | Used for AES-256-GCM encryption of plans, confirmed mentions, limitations, and finding payloads |
| `BLINDSPOT_ACTIVE_KEY_VERSION` | Active key version identifier (e.g., `v1`) | Must exist in `BLINDSPOT_ENCRYPTION_KEYS` |

### Optional (password reset email delivery)
| Variable | Purpose |
| --- | --- |
| `SMTP_HOST` | Authenticated SMTP server hostname |
| `SMTP_PORT` | SMTP port (`587` STARTTLS default, or `465` SSL) |
| `SMTP_USERNAME` | SMTP login username |
| `SMTP_PASSWORD` | SMTP login password |
| `SMTP_FROM` | Sender address shown in reset emails |

### Generate a fresh 32-byte encryption key locally

```powershell
python -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

---

## 4. Test Locally Before Pushing

1. Copy `.env.example` to `.env` and fill in your private values (`.env` is gitignored).
2. Run the automated test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

3. Start the app locally:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

4. Open `http://localhost:8501`, verify sign-in/registration and plan analysis work, then stop the server.

---

## 5. Upload Safely to GitHub

1. **Initialize Git inside the project folder** (do not initialize in a parent user directory):

```powershell
cd "C:\Users\sujal\Downloads\project blindfold ai"
git init -b main
```

2. **Verify ignored files before staging** (`.env`, `.streamlit/secrets.toml`, `data/*.db`, `.venv/`, logs, and caches must NOT appear):

```powershell
git status
```

3. **Confirm required folders are included** (`app.py`, `requirements.txt`, `.streamlit/config.toml`, `.env.example`, `.gitignore`, `components/`, `knowledge_base/`, `tests/`, and `*.py`/`*.md`):

```powershell
git add .
git status
```

4. **Commit and push to a new GitHub repository**:

```powershell
git commit -m "Prepare BlindSpot AI for Streamlit Community Cloud deployment"
git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_REPO>.git
git push -u origin main
```

---

## 6. Deploy on Streamlit Community Cloud

1. Sign in to [share.streamlit.io](https://share.streamlit.io) with your GitHub account.
2. Click **Create app** (or **New app**).
3. Select your repository, branch (`main`), and main file path: **`app.py`**.
4. Open **Advanced settings -> Secrets** and paste your private TOML configuration (replace placeholders with newly generated values):

```toml
ADMIN_NAME = "Site Administrator"
ADMIN_PASSWORD = "ReplaceWithStrongAdminPassword9!"
BLINDSPOT_ENCRYPTION_KEYS = '{"v1":"REPLACE_WITH_BASE64_32_BYTE_KEY"}'
BLINDSPOT_ACTIVE_KEY_VERSION = "v1"

# Optional SMTP settings for admin password-reset emails:
# SMTP_HOST = "smtp.example.com"
# SMTP_PORT = "587"
# SMTP_USERNAME = "mailer@example.com"
# SMTP_PASSWORD = "ReplaceWithSmtpPassword"
# SMTP_FROM = "BlindSpot AI <no-reply@example.com>"
```

5. Click **Deploy**. On first boot, `app.py` loads `st.secrets`, initializes `data/blindspot_ai.db`, provisions the `admin` account, and serves the login dashboard over HTTPS.

---

## 7. Persistence & Security Limitations on Streamlit Community Cloud

1. **Ephemeral SQLite storage (Important):** Streamlit Community Cloud runs apps in ephemeral Linux containers. Whenever the app sleeps due to inactivity, restarts, redeploys, or receives a new Git commit, the local filesystem—including `data/blindspot_ai.db`—is **reset**. Registered user accounts, saved analyses, finding statuses, and audit logs will not survive container resets unless migrated to an external managed database.
2. **Single-node SQLite concurrency:** SQLite with WAL mode handles light demo/team traffic on one container, but it is not shared across multiple horizontal replicas and is not suited for heavy concurrent writes.
3. **Key continuity:** Because plans and findings are encrypted with AES-256-GCM (`BLINDSPOT_ENCRYPTION_KEYS`), changing or losing the encryption key without rotating records first makes existing ciphertext unreadable (the app fails closed to protect data integrity).
4. **Platform-level trust boundary:** As documented in `SECURITY.md`, application-level encryption protects database files copied out-of-band, but cannot protect plaintext from an operator with direct control over the hosting runtime and Secrets dashboard.
