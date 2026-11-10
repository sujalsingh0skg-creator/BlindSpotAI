"""Transparent heuristic risk scoring for BlindSpot AI."""
from __future__ import annotations

from typing import Any

RISK_CONFIG = {
    "thresholds": ((6, "Low"), (12, "Medium"), (19, "High"), (25, "Critical")),
    "explicit_gap_likelihood_increase": 1,
    "max_explicit_gap_likelihood": 4,
    "urgent_deadlines_change_likelihood": False,
}
RISK_THRESHOLDS = RISK_CONFIG["thresholds"]


def risk_category(score: int) -> str:
    """Return the configured category for a 1–25 risk score."""
    for upper_bound, category in RISK_THRESHOLDS:
        if score <= upper_bound:
            return category
    raise ValueError("Risk score must be between 1 and 25.")


def calculate_risk(
    impact: int,
    likelihood: int,
    urgency: bool = False,
    evidence_status: str = "Not mentioned",
    impact_rationale: str | None = None,
) -> dict[str, Any]:
    """Calculate configurable heuristic risk without conflating it with confidence."""
    if not 1 <= impact <= 5 or not 1 <= likelihood <= 5:
        raise ValueError("Impact and likelihood must be whole numbers from 1 to 5.")
    adjusted_likelihood = likelihood
    likelihood_explanation = "No direct evidence changes the knowledge-base likelihood estimate."
    if evidence_status == "Explicitly untested or missing":
        adjusted_likelihood = min(
            RISK_CONFIG["max_explicit_gap_likelihood"],
            likelihood + RISK_CONFIG["explicit_gap_likelihood_increase"],
        )
        likelihood_explanation = "The plan explicitly says this safeguard is untested, missing, or unprepared, so the base likelihood increases by one."
    elif evidence_status == "Partially addressed":
        likelihood_explanation = "A related step is complete, but the required verification is not evidenced."
    score = impact * adjusted_likelihood
    deadline_note = " The immediate deadline is a prioritization cue; it does not change likelihood." if urgency else ""
    return {
        "impact": impact,
        "likelihood": adjusted_likelihood,
        "risk_score": score,
        "risk_category": risk_category(score),
        "scoring_note": f"Heuristic estimate — Impact {impact}/5: {impact_rationale or 'this requirement protects a critical deployment outcome.'} Likelihood {adjusted_likelihood}/5: {likelihood_explanation}{deadline_note}",
    }
