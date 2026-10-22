"""Charts and graph visualizations."""
from __future__ import annotations

from typing import Any

import networkx as nx
import pandas as pd
import plotly.graph_objects as go

from dependency_engine import build_dependency_graph


def risk_distribution_chart(findings: list[dict[str, Any]]) -> go.Figure:
    """Build a dark-compatible chart whose labels equal the active finding count."""
    order = ["Low", "Medium", "High", "Critical"]
    values = pd.DataFrame(findings, columns=["risk_category"])
    values = values.groupby("risk_category").size().reindex(order, fill_value=0).reset_index(name="count")
    colors = {"Low": "#35c49a", "Medium": "#f1c453", "High": "#f28c4b", "Critical": "#ef6275"}
    figure = go.Figure(go.Bar(
        x=values["risk_category"], y=values["count"], marker_color=[colors[level] for level in values["risk_category"]],
        text=values["count"], textposition="outside", cliponaxis=False,
        hovertemplate="%{x}: %{y} finding(s)<extra></extra>",
    ))
    figure.update_layout(
        template="plotly_dark", showlegend=False, height=330, margin={"l":15, "r":15, "t":45, "b":20},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,20,29,.78)", font={"color": "#c7ccda"},
        title={"text": f"Risk distribution · {int(values['count'].sum())} visible finding(s)", "font": {"size": 15}},
        xaxis={"title": None, "showgrid": False, "zerolinecolor": "rgba(160,170,195,.15)"}, yaxis={"title": "Findings", "dtick": 1, "rangemode": "tozero", "gridcolor": "rgba(160,170,195,.12)"},
    )
    return figure


def _short_node_label(title: str) -> str:
    """Keep graph labels readable while exposing the full title on hover."""
    replacements = {
        "Database backup and restoration verification": "Backup & restore",
        "Authentication and role-based authorization testing": "Role authorization",
        "Load, concurrency, and database-capacity testing": "Load & capacity",
        "Server restart and recovery testing": "Restart recovery",
        "Rollback and deployment recovery planning": "Rollback plan",
        "Privacy and protection of student records": "Student privacy",
        "HTTPS and secure session configuration": "HTTPS sessions",
        "Error logging and monitoring": "Error monitoring",
        "Test coverage and input validation": "Test coverage",
    }
    return replacements.get(title, title if len(title) <= 22 else f"{title[:19]}…")


def dependency_figure(findings: list[dict[str, Any]]) -> go.Figure | None:
    """Render supported dependencies using spaced hierarchical ranks and hover details."""
    graph = build_dependency_graph(findings)
    if graph.number_of_edges() == 0:
        return None
    if nx.is_directed_acyclic_graph(graph):
        levels = list(nx.topological_generations(graph))
    else:
        levels = [list(graph.nodes)]
    positions: dict[str, tuple[float, float]] = {}
    for level_index, nodes in enumerate(levels):
        spacing = max(1, len(nodes) - 1)
        for node_index, node in enumerate(sorted(nodes)):
            positions[node] = (float(level_index), -node_index + spacing / 2)
    edge_x, edge_y = [], []
    for source, target in graph.edges:
        edge_x.extend([positions[source][0], positions[target][0], None]); edge_y.extend([positions[source][1], positions[target][1], None])
    nodes = list(graph.nodes)
    node_x = [positions[node][0] for node in nodes]; node_y = [positions[node][1] for node in nodes]
    labels = [_short_node_label(graph.nodes[node]["label"]) for node in nodes]
    colors = {"Low": "#35c49a", "Medium": "#f1c453", "High": "#f28c4b", "Critical": "#ef6275"}
    hover = [f"<b>{graph.nodes[node]['label']}</b><br>Risk: {graph.nodes[node]['risk']}<br>Dependency relationship from the knowledge base" for node in nodes]
    figure = go.Figure([
        go.Scatter(x=edge_x, y=edge_y, mode="lines", hoverinfo="skip", line={"color": "#b5c4ce", "width": 1.5}),
        go.Scatter(x=node_x, y=node_y, mode="markers+text", text=labels, textposition="middle right", hovertext=hover, hovertemplate="%{hovertext}<extra></extra>", marker={"size": 18, "color": [colors[graph.nodes[node]["risk"]] for node in nodes], "line": {"color": "#252a38", "width": 1}}, textfont={"color": "#d7dbea", "size": 11}),
    ])
    figure.update_layout(template="plotly_dark", showlegend=False, margin={"l":25, "r":150, "t":35, "b":20}, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,20,29,.78)", font={"color": "#c7ccda"}, title={"text": "Knowledge-base dependencies", "font": {"size": 15}}, xaxis={"visible": False}, yaxis={"visible": False}, height=max(380, len(nodes) * 62))
    return figure
