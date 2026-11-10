"""BlindSpot AI Streamlit app with owner-scoped authentication."""
from __future__ import annotations

import base64
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Load local ignored configuration before importing auth/storage modules.
_env_file = os.environ.get("BLINDSPOT_ENV_FILE")
if not _env_file:
    _project_env = Path(__file__).parent / ".env"
    _local_env = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "BlindSpotAI" / "secrets.env"
    _env_file = str(_project_env if _project_env.exists() else _local_env if _local_env.exists() else _project_env)
load_dotenv(_env_file)

from analyzer import analyze_plan, filter_findings
from auth import (
    ABSOLUTE_TIMEOUT_SECONDS, AuthSetupError, authenticate, bootstrap_admin,
    change_admin_password, complete_password_reset, create_password_reset,
    create_session, logout, register_user, revoke_password_reset,
    set_account_status, validate_session, verify_current_password,
)
from components.dashboard import hero, inject_styles, metric_card, story_sequence
from components.risk_cards import render_risk_card
from components.visualizations import dependency_figure, risk_distribution_chart
from database import (
    AuthorizationError, DATABASE_PATH, admin_encrypted_records,
    admin_user_rows, assign_legacy_analysis, audit_rows, delete_analysis, get_analysis,
    initialize_database, list_analyses, record_audit, save_analysis,
    unassigned_legacy_analyses, update_finding_status,
)
from dependency_engine import what_if_scenario
from domain_detector import DOMAIN_LABELS
from mail_delivery import reset_delivery_configured, send_reset_code
from report_generator import report_csv, report_html, report_json
from security import EncryptedDataError, SecurityConfigurationError

st.set_page_config(page_title="BlindSpot AI", page_icon="◉", layout="wide")
inject_styles()


def _setup_error(error: Exception) -> None:
    st.error(str(error))
    st.info("Set the private administrator and encryption-key configuration described in SECURITY.md, then restart BlindSpot AI.")


try:
    initialize_database()
    bootstrap_admin()
except (AuthSetupError, SecurityConfigurationError, OSError) as error:
    st.title("BlindSpot AI setup required")
    _setup_error(error)
    st.stop()


def _clear_authenticated_state() -> None:
    for key in ("auth_token", "report", "reset_code_sent"):
        st.session_state.pop(key, None)


def _log_export(owner_id: int, analysis_id: int, file_format: str) -> None:
    record_audit("sensitive_export", actor_id=owner_id, target=f"analysis:{analysis_id}:{file_format}")


def _render_auth_form(auth_page: str) -> None:
    if auth_page == "register":
        st.markdown("<div id='register-panel'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.subheader("Create your user account")
            st.caption("Create a regular user account with a username and email address. Administrator accounts are created privately and cannot be registered here.")
            with st.form("registration_form", clear_on_submit=True):
                username = st.text_input("Choose a username", placeholder="e.g. alex.smith", max_chars=32, autocomplete="username", help="3–32 letters, numbers, dots, dashes, or underscores.")
                email = st.text_input("Your email address", placeholder="you@example.com", max_chars=254, autocomplete="email")
                password = st.text_input("Create a password", type="password", placeholder="Enter a strong password", max_chars=256, autocomplete="new-password", help="Use at least 12 characters, including uppercase and lowercase letters, a number, and a symbol.")
                confirmation = st.text_input("Confirm your password", type="password", placeholder="Type the same password again", max_chars=256, autocomplete="new-password")
                submitted = st.form_submit_button("Register", type="primary", use_container_width=True)
            if submitted:
                try:
                    register_user(username, email, password, confirmation)
                    st.session_state.auth_page = "login"
                    st.success("Account created. You can now log in.")
                except ValueError as error:
                    st.error(str(error))
            if st.button("Back to login"):
                st.session_state.auth_page = "login"
                st.rerun()
            st.caption("All public registrations are user accounts. Administrator sign-up is not available.")
        return

    if auth_page == "reset":
        st.markdown("<div id='login-panel'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.subheader("Reset your password")
            st.caption("Use the one-time code delivered to the email address on your account.")
            with st.form("reset_form", clear_on_submit=True):
                code = st.text_input("One-time reset code", type="password", max_chars=128)
                password = st.text_input("New password", type="password", max_chars=256, autocomplete="new-password")
                confirmation = st.text_input("Confirm new password", type="password", max_chars=256, autocomplete="new-password")
                submitted = st.form_submit_button("Reset password", type="primary", use_container_width=True)
            if submitted:
                try:
                    if complete_password_reset(code, password, confirmation):
                        st.session_state.auth_page = "login"
                        st.success("Password updated. Log in with your new password.")
                    else:
                        st.error("The reset code is invalid or expired.")
                except ValueError as error:
                    st.error(str(error))
            if st.button("Back to login"):
                st.session_state.auth_page = "login"
                st.rerun()
        return

    st.markdown("<div id='login-panel'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("<div class='eyebrow'>Secure sign-in</div>", unsafe_allow_html=True)
        st.subheader("Sign in to your workspace")
        st.caption("Users: enter the username or email you registered, then your password.")
        with st.form("login_form", clear_on_submit=True):
            identifier = st.text_input("Username or email", placeholder="Your username or email address", max_chars=254, autocomplete="username", help="For administrator access, enter admin as the username.")
            password = st.text_input("Password", type="password", placeholder="Enter your account password", max_chars=256, autocomplete="current-password", help="Passwords are case-sensitive.")
            submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)
        if submitted:
            user = authenticate(identifier, password)
            if user:
                st.session_state.auth_token = create_session(user["id"])
                st.session_state.pop("auth_page", None)
                st.session_state.report = None
                st.rerun()
            st.error("Login failed. Check your credentials or try again later.")
        register_col, reset_col = st.columns(2)
        if register_col.button("Create user account", use_container_width=True):
            st.session_state.auth_page = "register"
            st.rerun()
        if reset_col.button("Reset password", use_container_width=True):
            st.session_state.auth_page = "reset"
            st.rerun()
        st.markdown("<div class='admin-note'><strong>Administrator access</strong><span>Use this same form with username <code>admin</code> or <code>admin1</code> and your privately configured administrator password. Administrator accounts are never created through public registration.</span></div>", unsafe_allow_html=True)


def _render_login() -> None:
    st.markdown("<div class='brand'><span class='brand-mark'>◉</span><span>BlindSpot AI</span></div>", unsafe_allow_html=True)
    auth_page = st.session_state.get("auth_page", "login")
    target = "register-panel" if auth_page == "register" else "login-panel"
    left, right = st.columns([1.08, .92], gap="large", vertical_alignment="center")
    with left:
        hero(context="auth", target=target)
    with right:
        _render_auth_form(auth_page)
    story_sequence()


def _render_admin(user: dict) -> None:
    st.markdown("<section class='page-banner'><div class='eyebrow'>BlindSpot / operations</div><h1>Oversight, with boundaries.</h1><p>Account metadata, encrypted workspace records, and security events. Plan and finding plaintext is not loaded here.</p></section>", unsafe_allow_html=True)
    search_col, status_col = st.columns([2, 1])
    search = search_col.text_input("Search users", placeholder="Username or email")
    status = status_col.selectbox("Account status", ["all", "active", "disabled"])
    users = admin_user_rows(user["id"], search, status)
    st.dataframe(users, use_container_width=True, hide_index=True)
    if not users:
        st.info("No user accounts match these filters.")
    else:
        st.subheader("User profile and encrypted records")
        selected = st.selectbox("Select user", users, format_func=lambda row: f"{row['username']} · {row['email']} · {row['status']}", key="admin_selected_user")
        target_id = int(selected["id"])
        action_left, action_right = st.columns(2)
        next_status = "disabled" if selected["status"] == "active" else "active"
        if action_left.button("Disable account" if next_status == "disabled" else "Reactivate account", key=f"status_action_{target_id}"):
            set_account_status(user["id"], target_id, next_status)
            st.rerun()
        if action_right.button("Email password reset code", disabled=not reset_delivery_configured(), key=f"reset_action_{target_id}"):
            token = create_password_reset(user["id"], target_id)
            try:
                if token:
                    send_reset_code(selected["email"], token)
                    st.success("A one-time code was sent to the user's registered email address.")
                else:
                    st.error("A reset code could not be issued for this account.")
            except (OSError, RuntimeError, ValueError):
                if token:
                    revoke_password_reset(token)
                record_audit("password_reset_delivery_failed", actor_id=user["id"], target=str(target_id), outcome="failure")
                st.error("Reset delivery failed. Check the private mail configuration; no code was displayed.")
        if not reset_delivery_configured():
            st.caption("Password reset delivery is unavailable until authenticated SMTP settings are configured.")

        records = admin_encrypted_records(user["id"], target_id)
        st.caption(f"{selected['plan_count']} plan(s) · {selected['session_count']} analysis session(s) · Last activity: {selected['last_activity'] or 'Never'}")
        if records:
            for record in records:
                with st.expander(f"Analysis #{record['analysis_id']} · {record['domain_name']} · {record['created_at']}"):
                    st.caption("Encrypted plan record (base64 ciphertext)")
                    plan_ciphertext = record["plan_ciphertext"]
                    st.code(base64.b64encode(plan_ciphertext).decode("ascii") if plan_ciphertext else "No ciphertext", language="text")
                    st.caption(f"Key version: {record['plan_key_version']} · nonce: {base64.b64encode(record['plan_nonce']).decode('ascii') if record['plan_nonce'] else 'n/a'}")
                    st.caption(f"Finding metadata: {record['requirement_id'] or 'none'} · {record['title'] or 'n/a'}")
                    payload = record["payload_ciphertext"]
                    if payload:
                        st.caption("Encrypted finding payload (base64 ciphertext)")
                        st.code(base64.b64encode(payload).decode("ascii"), language="text")
        else:
            st.info("This user has no saved plans. This application has no separate conversation/message store.")

    st.subheader("Security audit log")
    st.dataframe(audit_rows(user["id"], 200), use_container_width=True, hide_index=True)
    legacy = unassigned_legacy_analyses(user["id"])
    if legacy:
        st.subheader("Legacy records awaiting ownership")
        st.caption("These records were saved before accounts existed. They remain encrypted and unavailable to users until you explicitly identify and assign an owner.")
        legacy_choice = st.selectbox("Unassigned record", legacy, format_func=lambda row: f"#{row['id']} · {row['domain_name']} · {row['created_at']}")
        eligible_users = admin_user_rows(user["id"], status="active")
        if eligible_users:
            legacy_owner = st.selectbox("Confirmed owner", eligible_users, format_func=lambda row: f"{row['username']} · {row['email']}")
            if st.button("Assign this record to the confirmed owner"):
                if assign_legacy_analysis(user["id"], int(legacy_choice["id"]), int(legacy_owner["id"])):
                    st.success("Legacy record assigned.")
                    st.rerun()
                else:
                    st.error("Record could not be assigned.")
        else:
            st.info("Create an active user account before assigning legacy records.")
    st.subheader("Administrator password")
    with st.form("admin_password_change", clear_on_submit=True):
        current = st.text_input("Current password", type="password", autocomplete="current-password")
        new_password = st.text_input("New password", type="password", autocomplete="new-password")
        confirmation = st.text_input("Confirm new password", type="password", autocomplete="new-password")
        submitted = st.form_submit_button("Change administrator password")
    if submitted:
        if not verify_current_password(user["id"], current):
            st.error("Current password is incorrect.")
        else:
            try:
                change_admin_password(user["id"], current, new_password, confirmation)
                _clear_authenticated_state()
                st.success("Password changed. Please log in again.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def _render_required_admin_password_change(user: dict) -> None:
    st.title("Secure administrator setup")
    st.warning("Your initial administrator password is below the required strength. Set a strong password before opening the admin dashboard.")
    with st.form("required_admin_password_change", clear_on_submit=True):
        current = st.text_input("Current password", type="password", autocomplete="current-password")
        new_password = st.text_input("New password", type="password", autocomplete="new-password")
        confirmation = st.text_input("Confirm new password", type="password", autocomplete="new-password")
        submitted = st.form_submit_button("Set strong password", type="primary")
    if submitted:
        if not verify_current_password(user["id"], current):
            st.error("Current password is incorrect.")
            return
        try:
            change_admin_password(user["id"], current, new_password, confirmation)
            st.session_state.auth_token = create_session(user["id"])
            st.success("Administrator password updated. Opening the dashboard…")
            st.rerun()
        except ValueError as error:
            st.error(str(error))


def _render_user_workspace(user: dict) -> None:
    with st.container(key="workspace_topbar", border=True):
        brand_col, nav_col, account_col = st.columns([1.15, 2.2, 1.1], vertical_alignment="center")
        with brand_col:
            st.markdown("<div class='brand'><span class='brand-mark'>◉</span><span>BlindSpot AI</span></div>", unsafe_allow_html=True)
        with nav_col:
            page = st.radio("Navigate", ["Analyze plan", "History"], horizontal=True, label_visibility="collapsed", key="workspace_page")
        with account_col:
            st.caption(f"{user['display_name'] or user['username']}")
            if st.button("Log out", use_container_width=True, key="workspace_logout"):
                logout(st.session_state.get("auth_token"))
                _clear_authenticated_state()
                st.rerun()

    hero(context="workspace", target="history-view" if page == "History" else "analysis-input")
    story_sequence()
    if page == "History":
        st.markdown("<div id='history-view'></div>", unsafe_allow_html=True)
        st.markdown("<section class='page-banner'><div class='eyebrow'>Your private workspace</div><h1>Saved signal.</h1><p>Open an analysis to continue reviewing findings, or remove an old record from your own workspace.</p></section>", unsafe_allow_html=True)
        st.subheader("Your analysis history")
        history = list_analyses(owner_id=user["id"])
        if not history:
            st.info("No saved analyses yet. Analyze a plan to create your private history.")
        for item in history:
            with st.container(border=True):
                st.markdown(f"**#{item['id']} · {item['domain_name']}**")
                st.caption(f"{item['created_at']} · {item['plan'][:160]}")
                open_col, delete_col = st.columns(2)
                if open_col.button("Open report", key=f"open_{item['id']}"):
                    report = get_analysis(item["id"], owner_id=user["id"])
                    st.session_state.report = report
                    st.rerun()
                if delete_col.button("Delete", key=f"delete_{item['id']}"):
                    delete_analysis(item["id"], owner_id=user["id"])
                    st.session_state.report = None
                    record_audit("analysis_deleted", actor_id=user["id"], target=str(item["id"]))
                    st.rerun()
    else:
        st.markdown("<div id='analysis-input'></div>", unsafe_allow_html=True)
        st.subheader("Analyze a plan")
        st.caption("Describe what is ready, what is constrained, and what must succeed. BlindSpot checks requirements the plan has not evidenced yet.")
        samples = {
            "Website deployment": "I'm deploying my college project tomorrow. The website is complete, and I have configured the database.",
            "College project": "I need to submit my software project next week. The main features are built and I have a basic interface.",
            "Hackathon planning": "We are organizing a 24-hour student hackathon for 120 people. The venue and judges are confirmed, and teams will need reliable high-speed internet.",
        }
        with st.container(border=True):
            selected_sample = st.selectbox("Start from a sample", ["Custom plan"] + list(samples))
            default_plan = samples.get(selected_sample, "")
            plan = st.text_area("Describe your plan", value=default_plan, placeholder="What are you planning, what is already complete, and what constraints do you have?", height=150)
            choice = st.selectbox("Domain", ["Auto-detect"] + list(DOMAIN_LABELS.values()))
            label_to_key = {value: key for key, value in DOMAIN_LABELS.items()}
            analyze_clicked = st.button("Begin plan analysis  →", type="primary", use_container_width=True)
        if analyze_clicked:
            try:
                with st.status("Tracing requirements and dependencies…", expanded=True) as analysis_status:
                    st.markdown("<div class='scan-progress'><div class='scan-orbit'></div><div><strong>Scanning the plan</strong><small>Comparing your description with the local requirements knowledge base.</small></div></div>", unsafe_allow_html=True)
                    result = analyze_plan(plan, None if choice == "Auto-detect" else label_to_key[choice])
                    result["analysis_id"] = save_analysis(result, owner_id=user["id"])
                    st.session_state.report = result
                    analysis_status.update(label="Analysis ready · saved to your workspace", state="complete", expanded=False)
                st.success("Analysis saved to your private workspace.")
            except (ValueError, OSError, SecurityConfigurationError) as error:
                st.error(f"Unable to analyze this plan: {error}")

    raw_report = st.session_state.get("report")
    if not raw_report or not raw_report.get("analysis_id"):
        return
    # Re-fetch every rerun through the owner-scoped backend before display/export.
    try:
        report = get_analysis(int(raw_report["analysis_id"]), owner_id=user["id"])
    except (SecurityConfigurationError, EncryptedDataError):
        report = None
    if report is None:
        st.session_state.report = None
        st.warning("That report is unavailable in your workspace.")
        return
    st.session_state.report = report
    findings = [finding for finding in report["findings"] if finding["requirement_id"] != "high_speed_connectivity"]
    st.divider()
    st.subheader(f"Risk report · {report['domain']}")
    filter_left, filter_right = st.columns(2)
    with filter_left:
        selected_risks = st.multiselect("Filter by risk", ["Low", "Medium", "High", "Critical"], default=["Low", "Medium", "High", "Critical"])
    with filter_right:
        selected_evidence = st.multiselect("Filter by evidence", ["Explicitly untested or missing", "Partially addressed", "Not mentioned"], default=["Explicitly untested or missing", "Partially addressed", "Not mentioned"])
    visible_findings = filter_findings(findings, set(selected_risks), set(selected_evidence))
    high_priority = sum(item["risk_category"] in {"High", "Critical"} for item in visible_findings)
    cols = st.columns(3)
    with cols[0]: metric_card("Visible blind spots", str(len(visible_findings)))
    with cols[1]: metric_card("High / critical", str(high_priority))
    with cols[2]: metric_card("Requirements evidenced", "—")
    st.info("Findings are requirements not evidenced in the description. They are potential gaps—not verified failures. Coverage depends on the editable local knowledge base.")
    chart_col, graph_col = st.columns(2)
    with chart_col: st.plotly_chart(risk_distribution_chart(visible_findings), use_container_width=True)
    with graph_col:
        graph = dependency_figure(visible_findings)
        if graph: st.plotly_chart(graph, use_container_width=True)
        else: st.info("No dependencies connect the current potential gaps.")
    st.subheader("Priority findings")
    if not visible_findings:
        st.success("Every requirement in this domain knowledge base was mentioned. This does not certify the plan as safe or complete.")
    for finding in visible_findings:
        def persist_status(finding_id: int, status: str) -> None:
            if update_finding_status(finding_id, status, owner_id=user["id"]):
                report = get_analysis(int(st.session_state.report["analysis_id"]), owner_id=user["id"])
                st.session_state.report = report
            else:
                record_audit("unauthorized_access", actor_id=user["id"], target=str(finding_id), outcome="denied")
        render_risk_card(finding, persist_status)
    if visible_findings:
        st.subheader("What-if analysis")
        selected_title = st.selectbox("Explore a potential gap", [item["title"] for item in visible_findings])
        selected = next(item for item in visible_findings if item["title"] == selected_title)
        st.warning(what_if_scenario(selected))
    st.subheader("Export report")
    export_cols = st.columns(3)
    analysis_id = int(report["analysis_id"])
    export_cols[0].download_button("Download JSON", report_json(report), "blindspot-report.json", "application/json", on_click=_log_export, args=(user["id"], analysis_id, "json"))
    export_cols[1].download_button("Download CSV", report_csv(report), "blindspot-report.csv", "text/csv", on_click=_log_export, args=(user["id"], analysis_id, "csv"))
    export_cols[2].download_button("Download HTML", report_html(report), "blindspot-report.html", "text/html", on_click=_log_export, args=(user["id"], analysis_id, "html"))


token = st.session_state.get("auth_token")
current_user = validate_session(token)
if current_user is None:
    if token:
        _clear_authenticated_state()
        st.warning("Your session expired or your account is inactive. Please log in again.")
    _render_login()
else:
    if current_user["role"] == "admin" and current_user.get("must_change_password"):
        with st.sidebar:
            st.markdown("<div class='brand'><span class='brand-mark'>◉</span><span>BlindSpot AI</span></div>", unsafe_allow_html=True)
            st.caption("Administrator setup")
            if st.button("Log out", use_container_width=True):
                logout(token)
                _clear_authenticated_state()
                st.rerun()
        _render_required_admin_password_change(current_user)
    elif current_user["role"] == "admin":
        with st.sidebar:
            st.markdown("<div class='brand'><span class='brand-mark'>◉</span><span>BlindSpot AI</span></div>", unsafe_allow_html=True)
            st.caption(f"Administrator · {current_user['display_name'] or current_user['username']}")
            if st.button("Log out", use_container_width=True):
                logout(token)
                _clear_authenticated_state()
                st.rerun()
        _render_admin(current_user)
    else:
        _render_user_workspace(current_user)
