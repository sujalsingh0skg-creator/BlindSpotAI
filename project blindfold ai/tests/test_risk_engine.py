import pytest

from risk_engine import calculate_risk, risk_category


def test_risk_scoring_and_category():
    result = calculate_risk(4, 4)
    assert result["risk_score"] == 16
    assert result["risk_category"] == "High"
    assert risk_category(20) == "Critical"


def test_invalid_risk_values_are_rejected():
    with pytest.raises(ValueError):
        calculate_risk(0, 4)


def test_evidence_status_changes_likelihood_but_deadline_does_not():
    unmentioned = calculate_risk(5, 3, urgency=True, evidence_status="Not mentioned")
    explicit_gap = calculate_risk(5, 3, urgency=True, evidence_status="Explicitly untested or missing")
    assert unmentioned["likelihood"] == 3
    assert unmentioned["risk_score"] == 15
    assert explicit_gap["likelihood"] == 4
    assert explicit_gap["risk_score"] == 20
    assert "does not change likelihood" in explicit_gap["scoring_note"]
