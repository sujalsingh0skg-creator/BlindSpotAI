<div align="center">

# 🔎 BlindSpot AI
### See what your plan is missing.

**An explainable planning-assurance dashboard that compares a written plan with domain-specific requirements and highlights possible gaps before execution.**

[![Live Demo](https://img.shields.io/badge/🚀_LIVE_DEMO-Open_App-9BFF3B?style=for-the-badge&labelColor=111827)](https://blindspotai-wu8o3hghfgnu8rbb8t3ibt.streamlit.app/)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github)](https://github.com/sujalsingh0skg-creator/BlindSpotAI)
[![Quick Start](https://img.shields.io/badge/⚡_QUICK_START-Setup-2563EB?style=for-the-badge)](#-quick-start)
[![Documentation](https://img.shields.io/badge/📘_DOCUMENTATION-Read-7C3AED?style=for-the-badge)](#-documentation)

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=flat-square&logo=sqlite)
![Reports](https://img.shields.io/badge/Reports-JSON%20%7C%20CSV%20%7C%20HTML-0F766E?style=flat-square)

[Overview](#-overview) · [How It Works](#-how-it-works) · [Features](#-key-features) · [Architecture](#-project-structure) · [Quick Start](#-quick-start) · [Security](#-security) · [Deployment](#-deployment) · [Roadmap](#-roadmap)

</div>

---

## 🎯 Overview

BlindSpot AI helps users inspect a written plan before execution. It compares the plan with an editable, domain-specific checklist and identifies requirements that may be missing, unclear, partly addressed, or not yet tested.

Supported planning areas currently represented in the knowledge base:
- **College / software projects**
- **Website deployment**
- **Event planning**

BlindSpot AI is a decision-support tool, not a guarantee that a plan is complete or risk-free. Review findings and use professional judgement.

## 🧠 How It Works

```text
Enter plan + choose domain
          │
          ▼
Domain detection / manual selection
          │
          ▼
Load domain-specific checklist
          │
          ▼
Match plan wording with requirement evidence
          │
          ▼
Classify requirements + estimate heuristic risk
          │
          ▼
Show findings, recommendations and exportable report
```

### Requirement classifications

| Status | Meaning |
|---|---|
| ✅ Confirmed | The plan appears to contain evidence addressing the requirement. |
| 🟡 Partly addressed | Some evidence exists, but more detail or completion may be needed. |
| 🔴 Missing / untested | The plan indicates that the requirement is missing or has not been tested. |
| ⚪ Unmentioned | The plan does not provide clear evidence for the requirement. |

> **Risk score:** A heuristic estimate based on configured impact and likelihood rules. It is not a certified risk measurement.

## ✨ Key Features

- Domain selection and domain detection.
- Editable JSON-based domain checklists.
- Evidence-based requirement gap identification.
- Requirement status classification.
- Heuristic risk scoring to help prioritize findings.
- Analysis history using the configured local database.
- Downloadable JSON, CSV and HTML reports.
- Login and security-related functionality.

## 🧰 Technology Stack

| Layer | Technology |
|---|---|
| Interface | Streamlit |
| Application logic | Python |
| Analysis | Checklist and evidence matching |
| Domain knowledge | JSON |
| Local data storage | SQLite |
| Reports | JSON, CSV, HTML |
| Testing | pytest |
| Hosting | Streamlit Community Cloud |

## 🗂️ Project Structure

```text
BlindSpotAI/
├── app.py
├── analyzer.py
├── auth.py
├── database.py
├── dependency_engine.py
├── domain_detector.py
├── mail_delivery.py
├── report_generator.py
├── risk_engine.py
├── rotate_encryption.py
├── security.py
├── components/
│   ├── dashboard.py
│   ├── risk_cards.py
│   └── visualizations.py
├── knowledge_base/
│   ├── college_project.json
│   ├── event_planning.json
│   └── website_deployment.json
├── data/
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
├── DEPLOYMENT.md
├── SECURITY.md
├── LOGIN_AND_SECURITY_GUIDE.md
├── PROJECT_DOCUMENTATION.md
└── README.md
```

## ⚡ Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/sujalsingh0skg-creator/BlindSpotAI.git
cd BlindSpotAI
```

### 2. Create a virtual environment

**Windows PowerShell**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure secrets

- Use `.env.example` as a reference for the environment variables your code requires.
- Create a local `.env` file if required by the application.
- Never commit passwords, API keys, tokens or encryption keys.
- On Streamlit Community Cloud, add the required values in **App → Settings → Secrets**, using the exact variable names expected by your code.

Example TOML format only — replace with the actual secret names required by your app:

```toml
APP_SECRET = "replace_with_a_long_random_secret"
```

### 5. Run locally

```bash
streamlit run app.py
```

Open the local URL shown in the terminal, usually `http://localhost:8501`.

## 🔐 Security

The repository includes security-related modules and documentation. Verify each control against the actual code and deployment configuration before describing it as production-ready.

Security practices to maintain:
- Keep secrets outside source code and Git history.
- Use password hashing; never store plain-text passwords.
- Restrict access to user-specific analysis records and reports.
- Validate user input and use safe database operations.
- Use HTTPS for deployed access.
- Avoid logging passwords, tokens or sensitive plan content.

### Security checklist

- [ ] `.env` and private files are excluded by `.gitignore`.
- [ ] No credentials or encryption keys are committed.
- [ ] Production secrets are configured in the hosting platform.
- [ ] Login and role permissions are tested.
- [ ] Users cannot access another user's private records.
- [ ] HTTPS is enabled on the deployed app.
- [ ] Logs and error messages do not reveal secrets.

See [SECURITY.md](SECURITY.md) and [LOGIN_AND_SECURITY_GUIDE.md](LOGIN_AND_SECURITY_GUIDE.md).

## ☁️ Deployment

The Streamlit Community Cloud deployment flow:

1. Push the project to GitHub.
2. Open [Streamlit Community Cloud](https://share.streamlit.io/).
3. Select **Create app**.
4. Choose this repository and the `main` branch.
5. Set **Main file path** to `app.py`.
6. Add required environment values under **Advanced settings → Secrets**.
7. Select a Python version compatible with `requirements.txt`.
8. Click **Deploy** and inspect the app logs if startup fails.

### Live application

🚀 **[Open BlindSpot AI](https://blindspotai-wu8o3hghfgnu8rbb8t3ibt.streamlit.app/)**

> **Storage note:** A local SQLite database on an ephemeral hosting environment should not be treated as durable production storage. For persistent multi-user use, configure a managed database and access controls. Azure SQL, Azure Blob Storage and Power BI are future integration options unless separately implemented and tested.

See [DEPLOYMENT.md](DEPLOYMENT.md) for project-specific details.

## 🧪 Testing

Run the tests from the project root:

```bash
python -m pytest -v
```

Configure any required environment variables or external services before running tests that depend on them.

## 📚 Documentation

| File | Purpose |
|---|---|
| [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) | Project overview and implementation details |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Deployment instructions |
| [SECURITY.md](SECURITY.md) | Security practices and considerations |
| [LOGIN_AND_SECURITY_GUIDE.md](LOGIN_AND_SECURITY_GUIDE.md) | Login and account security |

## 🛣️ Roadmap

Potential future improvements — not claims of already completed functionality:

- [ ] Persistent managed database for production use.
- [ ] Cloud object storage for generated reports.
- [ ] Aggregated analytics dashboard.
- [ ] More domain-specific checklist templates.
- [ ] Better evidence explanations and checklist editing.
- [ ] Expanded automated and deployment testing.

## ⚠️ Limitations

- Analysis depends on the wording and completeness of the submitted plan.
- Checklist coverage is limited to the configured knowledge base.
- Ambiguous wording can lead to incorrect classifications.
- Risk scores are heuristic prioritization hints.
- “Unmentioned” does not prove that a requirement is absent in reality.

## 🤝 Contributing

1. Fork the repository.
2. Create a branch: `git checkout -b feature/your-feature`.
3. Make and test your changes.
4. Commit with a descriptive message.
5. Open a pull request explaining the change.

## 👨‍💻 Author

**Sujal Singh** · B.Tech CSE (AI & ML)

[GitHub Profile](https://github.com/sujalsingh0skg-creator) · [Project Repository](https://github.com/sujalsingh0skg-creator/BlindSpotAI)

---

<div align="center">

### BlindSpot AI — Plan with clarity. Find gaps early.

<sub>Academic project · Findings are decision-support guidance and should be independently reviewed.</sub>

[⬆ Back to Top](#-blindspot-ai)

</div>
