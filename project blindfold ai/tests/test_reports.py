from analyzer import analyze_plan
from report_generator import report_csv, report_html


def test_exports_include_evidence_status_and_supporting_phrase():
    report = analyze_plan("I have not prepared a rollback plan for the deployment.", "website_deployment")
    csv_output = report_csv(report)
    html_output = report_html(report)
    assert "evidence_status" in csv_output
    assert "Explicitly untested or missing" in csv_output
    assert "Supporting phrase" in html_output
    assert "I have not prepared a rollback plan" in html_output


