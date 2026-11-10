"""Lightweight, offline domain classification."""
from __future__ import annotations

from collections import Counter

DOMAIN_LABELS = {
    "website_deployment": "Website Deployment",
    "college_project": "College / Software Project",
    "event_planning": "Event Planning",
}
DOMAIN_KEYWORDS = {
    "website_deployment": ("deploy", "deployment", "website", "web app", "production", "database", "hosting", "server", "domain", "api"),
    "college_project": ("college", "student", "project", "assignment", "semester", "demo", "submission", "professor", "github"),
    "event_planning": ("event", "venue", "attendees", "speaker", "rsvp", "catering", "volunteer", "workshop", "conference", "hackathon", "technical fest", "fest", "sponsorship", "event schedule"),
}


def detect_domain(plan: str) -> tuple[str, float]:
    """Return the best offline domain key and simple evidence-based confidence."""
    lowered = plan.lower()
    counts = Counter({key: sum(keyword in lowered for keyword in keywords) for key, keywords in DOMAIN_KEYWORDS.items()})
    domain, matches = counts.most_common(1)[0]
    confidence = round(matches / max(1, len(DOMAIN_KEYWORDS[domain])), 2)
    return domain, confidence
