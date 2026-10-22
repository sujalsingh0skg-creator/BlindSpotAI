"""Knowledge-base backed blind spot analysis."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from domain_detector import detect_domain
from risk_engine import calculate_risk

ROOT = Path(__file__).parent
KB_DIRECTORY = ROOT / "knowledge_base"
URGENT_SIGNALS = ("today", "tomorrow", "tonight", "in an hour", "this evening", "urgent", "immediately")


def load_knowledge_base(domain_key: str) -> dict[str, Any]:
    """Load and validate a domain knowledge base from local JSON."""
    allowed = {"website_deployment", "college_project", "event_planning"}
    if domain_key not in allowed:
        raise ValueError("Unsupported domain selection.")
    with (KB_DIRECTORY / f"{domain_key}.json").open(encoding="utf-8") as source:
        return json.load(source)


def _mentioned(plan: str, phrases: list[str]) -> list[str]:
    lowered = plan.lower()
    return [phrase for phrase in phrases if phrase.lower() in lowered]


def _sentences(plan: str) -> list[str]:
    """Split user input into readable evidence snippets without requiring an NLP model."""
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", plan) if sentence.strip()]


def _supporting_sentence(sentences: list[str], phrases: list[str]) -> str | None:
    """Return the first original input sentence containing a configured phrase."""
    for sentence in sentences:
        lowered = sentence.lower()
        if any(phrase.lower() in lowered for phrase in phrases):
            return sentence
    return None


def _has_negative_scope(sentence: str) -> bool:
    lowered = sentence.lower()
    return any(marker in lowered for marker in ("haven't", "have not", "hasn't", "has not", "not tested", "not prepared", "not checked", "without ", " no ", "explicitly missing", "missing:", "is missing", "are missing", "incomplete"))


def _classify_evidence(requirement: dict[str, Any], sentences: list[str]) -> tuple[str, str]:
    """Classify evidence before scoring so negated mentions never look confirmed."""
    negative_sentence = _supporting_sentence(sentences, requirement.get("negative_evidence", []))
    if negative_sentence:
        return "Explicitly untested or missing", negative_sentence

    context_terms = requirement.get("negative_context_terms", [])
    for sentence in sentences:
        if _has_negative_scope(sentence) and any(term.lower() in sentence.lower() for term in context_terms):
            return "Explicitly untested or missing", sentence

    confirmed_sentence = _supporting_sentence(sentences, requirement.get("evidence", []))
    if confirmed_sentence:
        return "Confirmed addressed", confirmed_sentence

    partial_sentence = _supporting_sentence(sentences, requirement.get("partial_evidence", []))
    if partial_sentence:
        return "Partially addressed", partial_sentence

    context_sentence = _supporting_sentence(sentences, requirement.get("risk_context_evidence", []))
    if context_sentence:
        return "Not mentioned", context_sentence
    return "Not mentioned", "No supporting phrase was found in the supplied plan."


def filter_findings(
    findings: list[dict[str, Any]],
    risk_categories: set[str] | None = None,
    evidence_statuses: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Return findings matching active UI filters without mutating the saved report."""
    allowed_risks = risk_categories if risk_categories is not None else {"Low", "Medium", "High", "Critical"}
    allowed_evidence = evidence_statuses if evidence_statuses is not None else {"Explicitly untested or missing", "Partially addressed", "Not mentioned"}
    return [
        item for item in findings
        if item["risk_category"] in allowed_risks and item.get("evidence_status", "Not mentioned") in allowed_evidence
    ]


def analyze_plan(plan: str, domain_key: str | None = None) -> dict[str, Any]:
    """Compare plan language to requirements, returning only unconfirmed requirements.

    A finding means the requirement was not evidenced in the supplied text; it is not
    proof that the user has failed to address it.
    """
    cleaned_plan = " ".join(plan.split())
    if len(cleaned_plan) < 10:
        raise ValueError("Please provide at least 10 characters describing the plan.")
    detected_domain, detection_confidence = detect_domain(cleaned_plan)
    selected_domain = domain_key or detected_domain
    knowledge_base = load_knowledge_base(selected_domain)
    urgent = any(signal in cleaned_plan.lower() for signal in URGENT_SIGNALS)
    sentences = _sentences(cleaned_plan)
    findings: list[dict[str, Any]] = []
    confirmed: list[str] = []
    not_applicable: list[str] = []
    for requirement in knowledge_base["requirements"]:
        applicability = requirement.get("applies_when_any", [])
        if applicability and not _mentioned(cleaned_plan, applicability):
            not_applicable.append(requirement["title"])
            continue
        evidence_status, supporting_phrase = _classify_evidence(requirement, sentences)
        if evidence_status == "Confirmed addressed":
            confirmed.append(requirement["title"])
            continue
        risk = calculate_risk(
            requirement["impact"], requirement["likelihood"], urgent,
            evidence_status=evidence_status, impact_rationale=requirement.get("impact_rationale"),
        )
        findings.append({
            "requirement_id": requirement["id"], "title": requirement["title"], "description": requirement["description"],
            "why_it_matters": requirement["why_it_matters"], "consequence": requirement["consequence"], "recommended_action": requirement["action"],
            "evidence": supporting_phrase, "supporting_phrase": supporting_phrase, "evidence_status": evidence_status,
            "confidence": {"Explicitly untested or missing": "High", "Partially addressed": "Medium", "Not mentioned": "Low"}[evidence_status],
            "status": "Open", "dependencies": requirement.get("dependencies", []),
            "classification_rank": {"Explicitly untested or missing": 3, "Partially addressed": 2, "Not mentioned": 1}[evidence_status], **risk,
        })
    # Keep one finding per requirement even if a knowledge base or model returns duplicates.
    findings = list({item["requirement_id"]: item for item in findings}.values())
    findings.sort(key=lambda item: (item["risk_score"], item["classification_rank"]), reverse=True)
    return {
        "plan": cleaned_plan, "domain_key": selected_domain, "domain": knowledge_base["domain"], "auto_detected_domain": detected_domain,
        "domain_detection_confidence": detection_confidence, "confirmed_mentions": confirmed, "not_applicable": not_applicable,
        "findings": findings, "limitations": "This is a knowledge-base coverage check, not a security audit or a guarantee of plan safety. Scores are initial heuristics, not calibrated probabilities.",
    }
