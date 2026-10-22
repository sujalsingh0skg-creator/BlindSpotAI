"""Dependency graph construction and hypothetical failure-chain narratives."""
from __future__ import annotations

from typing import Any

import networkx as nx


def build_dependency_graph(findings: list[dict[str, Any]]) -> nx.DiGraph:
    """Build a graph only between findings included in the current report."""
    graph = nx.DiGraph()
    included = {finding["requirement_id"]: finding for finding in findings}
    for item in findings:
        graph.add_node(item["requirement_id"], label=item["title"], risk=item["risk_category"])
        for dependency in item.get("dependencies", []):
            if dependency in included:
                graph.add_edge(item["requirement_id"], dependency)
    return graph


def what_if_scenario(finding: dict[str, Any]) -> str:
    """Create a clearly hypothetical rule-based scenario for a selected gap."""
    dependency_text = " It may also make related unresolved requirements harder to manage." if finding.get("dependencies") else ""
    return (f"Hypothetical scenario: if '{finding['title']}' remains unaddressed, {finding['consequence'].lower()} "
            f"Because its current heuristic score is {finding['risk_score']}/25, prioritizing '{finding['recommended_action']}' could reduce exposure.{dependency_text} "
            "This is a planning scenario, not a prediction that the failure will occur.")
