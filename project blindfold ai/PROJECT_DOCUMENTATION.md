# BlindSpot AI — Project Documentation

## 1. Project overview

BlindSpot AI is a local-first planning support dashboard built with Python and Streamlit. It reviews a written plan against a set of domain-specific requirements and brings attention to requirements that the plan does not clearly evidence. The goal is to help a person prepare, review, and improve a plan before a deployment, academic or software project, or event.

The app currently includes three checklist domains:

- **Website Deployment** — operational readiness, deployment configuration, data protection, recovery, testing, and monitoring.
- **College / Software Project** — requirements for preparing and delivering a student or software project.
- **Event Planning** — requirements for planning and running an event.

The analysis is a text and checklist coverage review. It does not inspect a real website, repository, event venue, database, or project. A finding means that the requirement was not adequately evidenced in the text provided, not that the task is definitely incomplete. A low-risk result or an empty finding list is not a certification that a plan is safe, complete, compliant, or ready to launch.

## 2. Main capabilities

- Analyze a plan against a selected domain or choose a domain automatically from keywords in the plan.
- Match plan text with requirement evidence phrases stored in editable JSON knowledge bases.
- Distinguish confirmed, partially addressed, explicitly missing or untested, and unmentioned requirements.
- Show a supporting sentence or explain that no supporting phrase was found.
- Prioritize potential gaps with a transparent heuristic score and a risk category.
- Filter findings by risk category and evidence status.
- Visualize the risk distribution and dependencies between unresolved requirements.
- Explore a hypothetical consequence for a selected finding with a what-if explanation.
- Save reports to a local SQLite database, update finding status, reopen or delete reports, and export reports as JSON, CSV, or HTML.

## 3. Starting and using the application

### Requirements

The project needs Python and the packages listed in `requirements.txt`. The Windows launcher `run.bat` creates a `.venv` virtual environment when needed, installs those packages, and starts Streamlit.

### Start on Windows

From the project folder, double-click `run.bat` or run it from PowerShell:

```powershell
.\run.bat
```

The first launch can take longer because dependencies are installed. Streamlit prints a local URL in the terminal, usually `http://localhost:8501`. Open that address in a browser on the same computer. Keep the terminal window open while using the app; closing it stops the local server.

Alternatively, activate the environment and run Streamlit directly:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

### Analyze a plan

1. Open **Analyze plan** from the sidebar.
2. Optionally select a sample plan as a starting point, or choose **Custom plan**.
3. Enter at least 10 characters describing the plan. Mention what is planned, what has already been done, and what remains uncertain when that context is useful.
4. Select a domain or leave **Auto-detect** selected.
5. Click **Analyze plan**.
6. Review the findings, evidence status, score rationale, charts, dependency relationships, and suggested actions.
7. Update a finding's status to **Open**, **In Progress**, or **Resolved** when appropriate. The change is saved locally.
8. Download a JSON, CSV, or HTML report if you need a copy outside the app.

### Review saved analyses

Open **History** in the sidebar to see saved reports. Each entry shows its identifier, domain, creation time, and a shortened version of the plan. **Open report** loads a report back into the dashboard. **Delete** removes that analysis and its associated findings from the local database.

## 4. How analysis works

### 4.1 Input cleanup and domain selection

The analyzer collapses repeated whitespace in the plan and rejects text shorter than 10 characters. If the user selected **Auto-detect**, `domain_detector.py` counts occurrences of configured keywords for each domain and chooses the domain with the greatest count. It also returns a simple detection-confidence value based on the number of matched keywords relative to that domain's keyword list.

Automatic detection is a lightweight keyword heuristic; it does not understand the plan like a language model. A tie or a plan with few matching keywords can lead to a poor suggestion. Users can choose a domain explicitly at any time. The selected domain determines which JSON knowledge base the analyzer loads.

### 4.2 Checklist and applicability

Each domain's JSON file contains a domain name, description, and a list of requirements. A requirement can define:

- A stable identifier and title.
- A short description of the expected outcome.
- Why it matters and a possible consequence if it is not addressed.
- A recommended action.
- Base impact and likelihood values from 1 to 5, plus an impact rationale.
- Phrases that count as full evidence, partial evidence, or explicit negative evidence.
- Optional context terms used to interpret a negative statement.
- Optional applicability phrases and dependencies on other requirements.

If a requirement has `applies_when_any` phrases and none of them appears in the plan, the requirement is recorded as not applicable to the supplied description and is not scored as a finding. This is a text-based applicability shortcut, so omitted context can affect the result.

### 4.3 Evidence classification

The analyzer splits the plan into sentences and compares each sentence with the requirement's configured phrases. It checks negative evidence first so that a sentence such as “we have not tested backups” is not accidentally treated as confirmation simply because it contains the word “backups.” The classification is:

| Status | Meaning in the report |
| --- | --- |
| **Confirmed addressed** | A configured full-evidence phrase appears without a detected negative qualification. The requirement is listed under confirmed mentions and does not become a blind-spot finding. |
| **Partially addressed** | A configured partial-evidence phrase appears, but full confirmation was not found. It remains a potential finding for follow-up. |
| **Explicitly untested or missing** | A configured negative-evidence phrase or a negative statement in relevant context indicates that the plan says the requirement is not ready, checked, or complete. |
| **Not mentioned** | The plan does not match full, partial, or explicit-negative evidence. The report may include a related context sentence, or state that no supporting phrase was found. |

For potential findings, the app displays the matching original sentence where available. This is a clue showing how the text was classified, not an independent verification of the claim. For “Not mentioned,” a context sentence can be shown if it includes a configured risk-context phrase; otherwise the report says no supporting phrase was found.

Only unconfirmed requirements appear in the findings list. The report separately includes confirmed mentions and requirements deemed not applicable. A checklist can miss a real issue, and exact phrase rules can miss paraphrases or misunderstand wording, negation, sarcasm, or context.

### 4.4 Risk scoring

`risk_engine.py` calculates a heuristic score in Python. Each requirement starts with an impact and likelihood from its knowledge-base entry, each on a 1–5 scale. For an explicitly untested or missing requirement, likelihood is increased by one, up to a maximum of 4. A partially addressed requirement keeps its base likelihood and receives an explanation that related work is present but verification is not evidenced. A requirement that is simply unmentioned keeps its base likelihood.

The formula is:

```text
risk score = impact × adjusted likelihood
```

The result is between 1 and 25. Categories follow the configured thresholds:

| Score | Category |
| ---: | --- |
| 1–6 | Low |
| 7–12 | Medium |
| 13–19 | High |
| 20–25 | Critical |

An urgent word such as “tomorrow” or “urgent” adds a prioritization note to the score explanation but does not change the numeric score. The score is an initial prioritization heuristic, not a calibrated probability or prediction. It should not be interpreted as a measured chance of failure.

### 4.5 Finding ordering and duplicate handling

Findings are deduplicated by their requirement identifier, then sorted with higher scores first and stronger evidence classification as a secondary ordering. Each finding carries descriptive content, evidence text and status, a confidence label associated with evidence classification, impact, likelihood, score, category, dependencies, and a recommended action.

## 5. Dashboard features

### Filters and summary metrics

The dashboard filters visible findings by **Low**, **Medium**, **High**, or **Critical** risk, and by evidence state. Summary cards show the number of visible potential blind spots, how many visible findings are High or Critical, and how many requirements were evidenced as confirmed.

Filters affect the displayed set and the risk distribution chart. They do not rewrite the saved source report.

### Risk distribution chart

The bar chart counts currently visible findings in each of the four risk categories. It is a visual summary of the rule-based scores, not a separate risk calculation.

### Dependency chart

Requirements can name dependency identifiers in their knowledge-base entries. The chart shows dependency edges only when both related requirements are present in the current findings. Consequently, the graph can omit a dependency if its requirement was already confirmed or is not applicable.

### What-if analysis

Selecting a finding produces a short, rule-based hypothetical scenario based on its possible consequence, score, action, and whether it has dependencies. The scenario is intended to help with prioritization. It is not a forecast that the described outcome will occur.

### Finding status

Each persisted finding can be marked **Open**, **In Progress**, or **Resolved**. This is a user-maintained workflow status; it does not change the evidence classification, score, or knowledge-base result.

## 6. Reports and local storage

Analysis history is stored in `data/blindspot_ai.db`, a SQLite database created automatically when the application starts. The database has an `analyses` table for the original plan, selected domain, creation time, and report limitations, and a `findings` table for each finding's serialized details and current status. Deleting an analysis also deletes its findings through a foreign-key cascade.

The export buttons provide:

- **JSON:** the report data in a structured, machine-readable form.
- **CSV:** one row per finding, including status, evidence, score, rationale, and recommended action.
- **HTML:** a standalone, readable report with the plan and finding table.

The app operates locally by default. The plan and report history are saved on the computer running Streamlit. Anyone with access to that computer account or its project files may be able to access the database. Avoid entering sensitive personal information or secrets unless you have considered the security of the computer and its backups. Database files are excluded from Git by `.gitignore`.

## 7. Project structure

```text
app.py                         Streamlit entry point and user interface flow
analyzer.py                    Checklist matching and evidence classification
domain_detector.py             Keyword-based automatic domain selection
risk_engine.py                 Risk score formula and category thresholds
dependency_engine.py           Dependency graph and what-if narrative
database.py                    SQLite storage and finding status updates
report_generator.py             JSON, CSV, and HTML exports
components/
  dashboard.py                 Shared page styling and dashboard elements
  risk_cards.py                Finding card rendering and status control
  visualizations.py            Risk chart and dependency graph rendering
knowledge_base/
  website_deployment.json      Website deployment requirement checklist
  college_project.json         College/software project checklist
  event_planning.json           Event planning checklist
data/
  blindspot_ai.db              Local analysis history (created at runtime)
tests/                         Regression tests for analysis and app modules
requirements.txt               Python dependencies
run.bat                        Windows setup and launch script
PROJECT_DOCUMENTATION.md       This documentation
```

## 8. Configuration and customization

### Add or edit checklist requirements

Domain checklists are regular JSON files under `knowledge_base/`. To improve a checklist, update its requirement entries while preserving valid JSON and unique requirement IDs. Phrase lists have a direct effect on classification: `evidence` indicates full evidence, `partial_evidence` indicates related but incomplete evidence, and `negative_evidence` identifies explicit gaps. Use specific phrases that are likely to appear in a plan and include negative forms where a positive phrase could otherwise be misleading.

Use impact and likelihood values from 1 to 5. Keep the impact rationale understandable because it is included in the score explanation. Dependencies must refer to requirement IDs in the same checklist if they are to form graph edges. Optional `applies_when_any` and context phrase fields should be used carefully because they influence which checks are surfaced.

### Change risk behavior

The category limits, explicit-gap likelihood adjustment, cap, and urgency behavior are configured in `risk_engine.py` under `RISK_CONFIG`. Any change to these values changes how new analyses are scored. Existing saved findings retain their saved payload until a new analysis is created.

### Add another domain

Adding a domain requires a new knowledge-base JSON file, a domain key and label in `DOMAIN_LABELS` in `domain_detector.py`, relevant keyword entries for automatic detection, and the new key in the analyzer's allowed domain set. The app's domain selector is generated from `DOMAIN_LABELS`, so it will then include the added label. Verify JSON validity and consistency of requirement IDs, evidence phrases, and dependencies.

## 9. Testing

Automated regression tests are in `tests/`. From the project directory with the virtual environment active, run:

```powershell
python -m pytest
```

The tests cover core analysis and evidence classification, risk scoring, database persistence, report generation, and visualizations. Passing tests checks the behaviors represented in those tests; it does not validate every possible plan wording or certify the completeness of the domain checklists.

## 10. Limitations and responsible interpretation

- The analyzer uses configured phrase matching rather than semantic understanding. Similar meanings expressed with different wording may not match.
- Negative-language detection is heuristic. Complex sentences, indirect negation, conditional statements, and ambiguous references can be classified incorrectly.
- Domain auto-detection is based on keyword counts and can choose the wrong domain. Explicit selection is available.
- Knowledge bases are finite and editable. Missing checklist coverage means a risk may not be surfaced.
- Evidence is taken from the user's description. The app does not verify claims against external systems or artifacts.
- Scores depend on human-set impact and likelihood values and simple rules; they are not empirically calibrated risk probabilities.
- A confirmed phrase means that the plan states or mentions something matching the configured phrase, not that the activity was actually completed or effective.
- The report is planning support and should be reviewed by people with relevant domain knowledge before decisions are made.

## 11. Privacy and external services

The current analysis pipeline is rule-based and runs locally. It does not send the plan to Gemini or another AI service. The app saves analyses to a local SQLite database so they can be reopened later. Keep the project directory and database protected according to the sensitivity of the plans you enter.
