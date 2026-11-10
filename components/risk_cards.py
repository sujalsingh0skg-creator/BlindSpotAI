"""Finding card UI component."""
from __future__ import annotations

from typing import Any

import streamlit as st


def render_risk_card(finding: dict[str, Any], on_status_change) -> None:
    """Render an actionable, explainable finding with a persisted status control."""
    badge = finding["risk_category"].lower()
    with st.container(border=True):
        st.markdown(f"<div class='risk-title'><span>{finding['title']}</span><span class='badge {badge}'>{finding['risk_category']} · {finding['risk_score']}/25</span></div>", unsafe_allow_html=True)
        st.caption(f"{finding.get('evidence_status', 'Potential gap')} · confidence: {finding['confidence']} · status: {finding['status']}")
        st.write(finding["description"])
        left, right = st.columns(2)
        with left:
            st.markdown(f"**Why it matters:** {finding['why_it_matters']}")
            st.markdown(f"**Possible consequence:** {finding['consequence']}")
        with right:
            st.markdown(f"**Recommended action:** {finding['recommended_action']}")
            st.caption(f"Impact {finding['impact']}/5 · Likelihood {finding['likelihood']}/5")
        st.markdown(f"**Evidence from plan:** {finding.get('supporting_phrase', finding.get('evidence', 'No supporting phrase found.'))}")
        st.caption(finding.get("scoring_note", "Risk score uses impact × likelihood."))
        if finding.get("database_id"):
            choice = st.selectbox("Status", ["Open", "In Progress", "Resolved"], index=["Open", "In Progress", "Resolved"].index(finding["status"]), key=f"status_{finding['database_id']}")
            if choice != finding["status"]:
                on_status_change(finding["database_id"], choice)
