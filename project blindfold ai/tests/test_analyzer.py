from analyzer import analyze_plan, filter_findings


WEBSITE_DEPLOYMENT_SCENARIO = (
    "I have developed a student attendance management web application using React, Python Flask, and MySQL. "
    "The login system and attendance marking features are working, and I have tested them manually with five students. "
    "I have deployed the frontend to a free hosting platform and configured the database connection. "
    "My environment variables are set, and I have created a GitHub repository. "
    "I am planning to demonstrate the application to 150 students and two faculty members tomorrow. "
    "I have not tested the application with many simultaneous users yet. "
    "I also haven't checked whether database backups are working, whether all user roles have the correct permissions, "
    "or whether the application recovers properly after a server restart. "
    "The demo data includes student names, roll numbers, and attendance records. "
    "I have not prepared a rollback plan, but I think the application is ready."
)


def test_mentioned_requirement_is_not_reported_as_gap():
    result = analyze_plan("I will deploy tomorrow with a tested database backup and HTTPS certificate.", "website_deployment")
    ids = {finding["requirement_id"] for finding in result["findings"]}
    assert "database_backup" not in ids
    assert "https" not in ids


def test_auto_detects_event_domain():
    result = analyze_plan("Our event venue has a speaker and attendees are invited.")
    assert result["domain_key"] == "event_planning"


def test_event_analyses_do_not_include_removed_hackathon_connectivity_check():
    report = analyze_plan("We are hosting a public fitness awareness camp with trainers and a venue.", "event_planning")
    assert "high_speed_connectivity" not in {finding["requirement_id"] for finding in report["findings"]}


def test_deployment_regression_detects_disclosed_and_unverified_safeguards():
    report = analyze_plan(WEBSITE_DEPLOYMENT_SCENARIO, "website_deployment")
    findings = {finding["requirement_id"]: finding for finding in report["findings"]}
    assert len(findings) == 9

    required_explicit_gaps = {
        "load_concurrency_testing",
        "database_backup_restore",
        "role_authorization",
        "server_restart_recovery",
        "rollback_recovery",
    }
    assert required_explicit_gaps <= findings.keys()
    for requirement_id in required_explicit_gaps:
        assert findings[requirement_id]["evidence_status"] == "Explicitly untested or missing"
        assert findings[requirement_id]["confidence"] == "High"
        assert findings[requirement_id]["supporting_phrase"] != "No supporting phrase was found in the supplied plan."

    assert findings["student_data_privacy"]["evidence_status"] == "Not mentioned"
    assert "student names" in findings["student_data_privacy"]["supporting_phrase"].lower()
    assert findings["https_secure_session"]["evidence_status"] == "Not mentioned"
    assert findings["error_monitoring"]["evidence_status"] == "Not mentioned"
    assert findings["test_coverage_validation"]["evidence_status"] == "Partially addressed"
    assert findings["database_backup_restore"]["risk_score"] == 20
    assert findings["role_authorization"]["risk_score"] == 20
    assert findings["load_concurrency_testing"]["risk_score"] == 16

    reported_ids = set(findings)
    assert not {"frontend_deployment", "database_connection", "environment_secrets", "source_control"} & reported_ids
    assert {"Frontend deployment verification", "Database connection configuration", "Environment variables and secrets", "Source control and release version"} <= set(report["confirmed_mentions"])


def test_finding_filters_apply_risk_and_evidence_without_dropping_defaults():
    report = analyze_plan(WEBSITE_DEPLOYMENT_SCENARIO, "website_deployment")
    critical_explicit = filter_findings(report["findings"], {"Critical"}, {"Explicitly untested or missing"})
    assert {item["requirement_id"] for item in critical_explicit} == {"database_backup_restore", "role_authorization"}
    assert filter_findings(report["findings"], set(), set()) == []
