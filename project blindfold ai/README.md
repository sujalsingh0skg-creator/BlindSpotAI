# BlindSpot AI

**Discover What You Might Be Missing.** BlindSpot AI is a local-first decision-support dashboard that compares a natural-language plan with an editable domain checklist. It highlights *potential* missing requirements, explains why each matters, recommends an action, and stores the result locally.

## Who it helps

Students deploying a project, developers preparing a website release, and organizers planning an event can use it to turn an informal plan into an explicit pre-flight checklist. It does not claim to audit, certify, or predict outcomes.

## Features

- Three offline knowledge bases: website deployment, college/software projects, and event planning.
- Automatic domain detection with optional manual override.
- Evidence-aware checks: a requirement that is explicitly mentioned is not returned as a gap.
- Transparent impact × likelihood scoring (1–25), priority sorting, charts, dependency graph, and hypothetical what-if narrative.
- Local SQLite history, finding statuses, deletion, and JSON/CSV/printable-HTML exports.
- Responsive Streamlit dashboard with offline rule-based analysis and local history.

## Architecture and data flow

`app.py` collects a plan → `domain_detector.py` selects a domain → `analyzer.py` loads `knowledge_base/*.json` and checks local evidence → `risk_engine.py` calculates heuristic scores → `database.py` stores results → UI components render cards/charts and `report_generator.py` exports reports.

The knowledge bases are ordinary JSON files. Add or edit requirement objects there to tailor checks without changing dashboard code.

## Installation and run (Windows)

Double-click `run.bat`, or run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local address Streamlit prints (normally `http://localhost:8501`). On systems where `python` is unavailable, install Python 3.10+ and retry.

Before first run, configure `ADMIN_NAME`, a strong `ADMIN_PASSWORD`, `BLINDSPOT_ENCRYPTION_KEYS`, and `BLINDSPOT_ACTIVE_KEY_VERSION` in a private `.env` file (copy `.env.example`) or your secrets manager. The first run securely provisions the private administrator and encrypts any old plaintext analysis records. See [SECURITY.md](SECURITY.md) for key generation, legacy ownership review, reset mail, rotation, and recovery. The administrator login name is `admin`; public users can register only as `user`.

## Sample inputs

- Website: `I'm deploying my college project tomorrow. The website is complete, and I have configured the database.`
- Project: `I need to submit my software project next week. The main features are built and I have a basic interface.`
- Event: `We are organizing a student workshop for 80 people next month. We have confirmed a speaker and drafted an agenda.`

The first example should surface potential gaps such as backups, release testing, monitoring, and rollback unless they are explicitly mentioned.

## Risk scoring

Each knowledge-base requirement has an initial **impact** and **likelihood** score from 1 to 5. `risk score = impact × likelihood`.

| Score | Category |
| --- | --- |
| 1–6 | Low |
| 7–12 | Medium |
| 13–19 | High |
| 20–25 | Critical |

These are configurable heuristics—not statistically calibrated probabilities. An immediate deadline is shown as a prioritization cue and does not by itself increase likelihood.

The current scoring policy is defined in `risk_engine.py` as `RISK_CONFIG`. An explicitly untested or missing safeguard increases its knowledge-base likelihood by one (capped at 4); a merely unmentioned safeguard keeps its base likelihood. An immediate deadline is shown as a prioritization cue, not a probability increase. Evidence status and detection confidence are displayed separately from severity.

## Local database

The SQLite database is created at `data/blindspot_ai.db` and excluded from Git. It contains `analyses` (plan, domain, timestamp, limitations) and `findings` (requirement payload and status). Queries use parameter binding, and only the plan text supplied in the browser is stored.

## Tests

```powershell
python -m pytest -q
```

Tests cover scoring thresholds, evidence detection, auto domain selection, SQLite persistence, status changes, and deletion.

## Limitations and next steps

- Matching is offline phrase/synonym matching rather than semantic model inference, deliberately keeping installation small and reliable.
- A missing mention is not proof a task is missing; it is labelled as a potential gap.
- The supplied knowledge bases are starter checklists and not compliance, security, legal, or safety advice.
- Future enhancements can add optional sentence-transformer embeddings, custom domains, user accounts, and calibrated scores from historical outcomes.
