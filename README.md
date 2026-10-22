# 🛡️ BlindSpot AI — Intelligent Plan Review & Risk Analysis Dashboard

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Framework-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/Database-SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Security-AES--256--GCM-green?style=for-the-badge" alt="AES-256-GCM">
</p>

<p align="center">
  <strong>Find the gaps in your plan before they become real-world problems.</strong>
</p>

<p align="center">
  Rule-Based Analysis • Evidence Classification • Risk Prioritization • Interactive Visualizations • Secure Workspace
</p>

---

## 📌 Overview

**BlindSpot AI** is a Python-based, local-first planning support dashboard that analyzes written plans against domain-specific checklists to identify requirements that may be missing, partially addressed, explicitly untested, or insufficiently evidenced.

Whether you are preparing a website deployment, a college project, a software application, or an event, BlindSpot AI helps you review your plan, understand potential gaps, prioritize important requirements, and identify practical next steps.

The application combines a configurable rule-based analysis engine, heuristic risk scoring, dependency visualization, what-if explanations, report generation, and account-based workspaces in one dashboard.

> **Important:** BlindSpot AI evaluates the evidence present in a written plan. It does not independently verify real-world completion, guarantee safety, or certify that a project is ready for deployment.

---

## ✨ Key Features

### 🔍 1. Intelligent Plan Analysis

- Analyze custom plans or start with sample plans.
- Select a domain manually or use keyword-based auto-detection.
- Compare plan descriptions against editable JSON checklists.
- Identify potentially overlooked or insufficiently documented requirements.
- Display supporting text where available.

### 🧾 2. Evidence Classification

BlindSpot AI classifies requirement evidence into four categories:

| Classification | Meaning |
|---|---|
| ✅ Confirmed addressed | The plan contains a configured phrase indicating that the requirement is addressed. |
| 🟡 Partially addressed | Some related work is mentioned, but complete evidence was not found. |
| 🔴 Explicitly untested or missing | The plan indicates that the requirement has not been completed, verified, or tested. |
| ⚪ Not mentioned | No matching evidence was found in the supplied plan. |

These classifications are based on configured phrases and rules, not independent verification.

### ⚠️ 3. Heuristic Risk Scoring

- Calculate a risk score using impact and adjusted likelihood.
- Assign Low, Medium, High, or Critical risk categories.
- Explain why a potential gap received its score.
- Prioritize findings for human review.
- Apply additional likelihood adjustment to explicitly untested or missing requirements.

**Risk formula:**

```text
Risk Score = Impact × Adjusted Likelihood
```

Scores range from 1 to 25. They are prioritization heuristics, not calibrated probabilities of failure.

| Score | Risk Category |
|---:|---|
| 1–6 | 🟢 Low |
| 7–12 | 🟡 Medium |
| 13–19 | 🟠 High |
| 20–25 | 🔴 Critical |

### 📊 4. Interactive Analytics Dashboard

- View summary metrics for potential blind spots.
- Filter findings by risk category and evidence status.
- Explore risk distribution charts.
- Visualize dependencies between unresolved requirements.
- Review suggested actions and supporting evidence.

### 🔗 5. Dependency Analysis

- Represent relationships between checklist requirements.
- Highlight dependencies between findings when both are present in the current findings list.
- Help users understand which potential gaps may be related.
- Support structured review and prioritization.

### 🧪 6. What-If Analysis

- Explore hypothetical consequences associated with selected findings.
- Understand why a requirement may deserve attention.
- Use recommendations to guide further review.

What-if explanations are illustrative scenarios, not predictions of actual outcomes.

### 🗂️ 7. Report History & Export

- Save analyses in a local SQLite database.
- Reopen previous reports.
- Update finding status: Open, In Progress, or Resolved.
- Delete saved analyses.
- Export reports in JSON, CSV, and HTML formats.

### 🔐 8. Authentication & Security

The current application includes account-based workspaces and security controls, including:

- User registration and sign-in.
- Separate user and administrator workspaces.
- Argon2id password hashing.
- Session expiration and revocation.
- Rate limiting for repeated failed login attempts.
- Account ownership checks for workspace records.
- AES-256-GCM encryption for designated sensitive record fields.
- Security audit logging.
- Administrator controls for account management and supported account recovery workflows.

Security depends on correct configuration and deployment. See [LOGIN_AND_SECURITY.md](LOGIN_AND_SECURITY.md) and [SECURITY.md](SECURITY.md) for details.

---

## 🌐 Supported Domains

BlindSpot AI currently provides three domain-specific checklists.

| Domain | Example Areas Reviewed |
|---|---|
| 🌍 Website Deployment | Deployment configuration, testing, monitoring, data protection, recovery, and operational readiness |
| 🎓 College / Software Project | Planning and delivery requirements for student and software projects |
| 🎪 Event Planning | Requirements for organizing and running an event |

The checklists are editable, allowing requirements, evidence phrases, impact, likelihood, and dependencies to be customized.

---

## ⚙️ How It Works

```text
        User enters a written plan
                   |
                   v
       Select domain or auto-detect
                   |
                   v
       Load domain-specific checklist
                   |
                   v
       Match evidence and plan text
                   |
                   v
       Classify requirement evidence
                   |
                   v
        Calculate heuristic risk
                   |
                   v
     Generate findings and suggestions
                   |
                   v
    Visualize risks and dependencies
                   |
                   v
       Save history and export report
```

### Analysis Pipeline

1. **Input processing:** Normalize whitespace and validate the plan length.
2. **Domain selection:** Use the selected domain or a keyword-based detection heuristic.
3. **Checklist loading:** Read requirements from the relevant JSON knowledge base.
4. **Evidence matching:** Compare plan sentences with configured full, partial, and negative evidence phrases.
5. **Classification:** Determine which requirements are confirmed, partially addressed, explicitly missing or untested, or not mentioned.
6. **Risk calculation:** Apply the configured impact and likelihood rules.
7. **Prioritization:** Deduplicate findings by requirement ID and sort them by risk.
8. **Visualization and reporting:** Display findings, charts, dependencies, recommendations, and exportable reports.

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python | Core application and analysis logic |
| Streamlit | Interactive web dashboard and application interface |
| SQLite | Local persistence for account and analysis data |
| JSON | Domain checklists and structured configuration |
| Pandas | Data processing and report-related operations, where used |
| Plotly / visualization libraries | Interactive charts and dependency visualizations, as configured in the project |
| Argon2id | Password hashing |
| AES-256-GCM | Encryption of designated sensitive fields |
| Pytest | Automated regression testing |

The exact installed dependencies are defined in `requirements.txt`.

---

## 🏗️ Project Architecture

BlindSpot AI separates analysis, risk calculation, storage, reporting, and dashboard presentation into dedicated modules.

```text
BlindSpot-AI/
│
├── app.py
├── analyzer.py
├── domain_detector.py
├── risk_engine.py
├── dependency_engine.py
├── database.py
├── report_generator.py
│
├── components/
│   ├── dashboard.py
│   ├── risk_cards.py
│   └── visualizations.py
│
├── knowledge_base/
│   ├── website_deployment.json
│   ├── college_project.json
│   └── event_planning.json
│
├── data/
│   └── blindspot_ai.db
│
├── tests/
├── requirements.txt
├── run.bat
├── PROJECT_DOCUMENTATION.md
├── LOGIN_AND_SECURITY.md
└── SECURITY.md
```

The SQLite database is created at runtime. Do not commit a database containing real user data or sensitive analysis history.

---

## 🚀 Installation & Setup

### 1. Clone the Repository

Replace the placeholder URL with your actual GitHub repository URL.

```bash
git clone https://github.com/YOUR_USERNAME/BlindSpot-AI.git
cd BlindSpot-AI
```

### 2. Create a Virtual Environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the project launcher or consult your Python environment setup.

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Security

Follow the operator setup instructions in `SECURITY.md` before using administrator features or deploying the application.

Keep encryption keys, administrator credentials, and other secrets outside the repository. Never publish real passwords, API keys, private configuration files, or production database contents.

### 5. Run the Application

```bash
streamlit run app.py
```

Open the local URL printed in the terminal, usually:

```text
http://localhost:8501
```

Keep the terminal and Streamlit process running while using the application.

---

## 🧪 Running Tests

Activate the project's virtual environment and run:

```bash
python -m pytest
```

The regression tests cover areas such as analysis, evidence classification, risk scoring, database persistence, report generation, and visualizations.

Passing tests verifies only the behaviors covered by the test suite. It does not prove that every possible plan will be classified correctly or that every security configuration is safe.

---

## 🔐 Security & Privacy

Security is an important part of BlindSpot AI because plans and reports may contain sensitive project information.

Current application protections include:

- **Password protection:** Passwords are hashed with Argon2id rather than stored as plaintext.
- **Session security:** Sessions have inactivity and maximum-lifetime limits, with logout and revocation support.
- **Access control:** Workspace database operations check record ownership.
- **Data encryption:** Designated sensitive fields are encrypted using AES-256-GCM.
- **Rate limiting:** Repeated failed login attempts are limited.
- **Auditability:** Security events are recorded without intentionally logging passwords, session tokens, reset codes, or encryption keys.
- **Account administration:** Administrators can manage account status and review supported security events.

### Security Considerations

- Use HTTPS when deploying beyond localhost.
- Keep encryption keys separate from the database and source code.
- Protect database files, exported reports, and backups.
- Configure administrator access and password recovery securely.
- Review `SECURITY.md` for key management, rotation, backups, migrations, and deployment limitations.
- Do not expose a development server directly to the public internet as a production deployment.

No application-level encryption protects plaintext from an operator who controls the running server, application code, or runtime environment.

---

## ☁️ Cloud Security & DP-900 Learning Roadmap

BlindSpot AI can be extended to demonstrate Microsoft Azure data and security concepts. The following items are **proposed enhancements**, not claims that the current local-first application already uses Azure.

| Area | Potential Implementation |
|---|---|
| DP-900 — Relational data | Migrate analysis and finding records to Azure SQL Database |
| DP-900 — Non-relational/object data | Store exported JSON, CSV, and HTML reports in Azure Blob Storage |
| DP-900 — Analytics | Use Power BI to visualize aggregated analysis trends |
| Cloud Security | Apply Microsoft Entra ID or another suitable identity integration |
| Cloud Security | Enforce least-privilege access and role-based permissions |
| Cloud Security | Use Azure Key Vault for supported secrets and key-management workflows |
| Monitoring | Add Azure Monitor or Application Insights for operational monitoring |

These enhancements would need to be implemented, configured, tested, and documented before being presented as completed functionality.

---

## 📈 Learning Outcomes

BlindSpot AI demonstrates practical experience with:

- Full-stack application design using Python and Streamlit.
- Modular software architecture.
- Rule-based text analysis and evidence classification.
- Risk scoring and prioritization algorithms.
- Relational database design and persistent storage.
- JSON-based configuration and extensible checklists.
- Interactive dashboard design and data visualization.
- Report generation in multiple formats.
- Authentication, authorization, and session management.
- Password hashing, application-level encryption, and audit logging.
- Automated regression testing and responsible interpretation of analytical results.

---

## 🔮 Future Enhancements

Potential improvements include:

- ☁️ Azure SQL Database integration.
- 📦 Azure Blob Storage for report management.
- 📊 Power BI analytics dashboards.
- 🧠 Optional semantic matching to complement phrase-based analysis.
- 📄 Support for extracting plans from uploaded documents.
- 🔔 Notifications for unresolved high-priority findings.
- 📋 Custom checklist creation through the dashboard.
- 📈 Historical risk trend analysis.
- 🚀 Production deployment with HTTPS, managed secrets, and monitoring.

These are roadmap ideas; their presence here does not mean they are already implemented.

---

## ⚠️ Limitations

BlindSpot AI is a planning support tool, not a compliance or safety certification system.

- Analysis relies on configured phrase matching.
- Domain auto-detection uses keyword counts.
- Negative statements and paraphrases can be misclassified.
- Checklist coverage may be incomplete.
- Risk scores use human-configured impact and likelihood values.
- Findings reflect the supplied text rather than independently verified facts.
- A confirmed phrase does not prove that a task was actually completed.

Users should review findings with appropriate domain knowledge before making consequential decisions.

---

## 📚 Documentation

- [Project Documentation](PROJECT_DOCUMENTATION.md) — architecture, analysis pipeline, risk scoring, and configuration.
- [Login & Security Guide](LOGIN_AND_SECURITY.md) — registration, sign-in, user workspace, and security behavior.
- [Security Operations Guide](SECURITY.md) — operator setup, key management, migration, rotation, backups, and deployment.

---

## 👨‍💻 Authors

### Vishesh Yadav

GitHub: [@vishesh99yadav](https://github.com/vishesh99yadav)

### Sujal Singh

GitHub: [@sujalsingh0skg-creator](https://github.com/sujalsingh0skg-creator)

---

## ⭐ Project Vision

BlindSpot AI aims to make planning more evidence-driven by helping people identify what their plans explain clearly, what needs further attention, and which potential gaps deserve review first.

**Better planning starts with asking what might have been overlooked.**
