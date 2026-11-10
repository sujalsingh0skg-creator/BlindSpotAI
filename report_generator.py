"""Export report generation helpers."""
from __future__ import annotations

import html
import json
from typing import Any

import pandas as pd


def report_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False)


def report_csv(report: dict[str, Any]) -> str:
    columns = ["title", "status", "evidence_status", "supporting_phrase", "risk_category", "risk_score", "impact", "likelihood", "scoring_note", "why_it_matters", "consequence", "recommended_action", "evidence"]
    return pd.DataFrame(report["findings"], columns=columns).to_csv(index=False)


def report_html(report: dict[str, Any]) -> str:
    rows = "".join(f"<tr><td>{html.escape(item['title'])}</td><td>{html.escape(item.get('evidence_status', 'Potential gap'))}</td><td>{html.escape(item.get('supporting_phrase', item.get('evidence', 'No supporting phrase found.')))}</td><td>{item['risk_score']}/25 ({html.escape(item['risk_category'])})</td><td>{html.escape(item['status'])}</td><td>{html.escape(item['recommended_action'])}</td></tr>" for item in report["findings"])
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>BlindSpot AI Report</title><style>body{{font-family:Arial;max-width:1100px;margin:40px auto;color:#172033}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #d6dce5;padding:10px;text-align:left;vertical-align:top}}th{{background:#e7f8f5}}</style></head><body><h1>BlindSpot AI report</h1><p><b>Domain:</b> {html.escape(report['domain'])}</p><h2>Plan</h2><p>{html.escape(report['plan'])}</p><h2>Potential blind spots</h2><table><tr><th>Requirement</th><th>Evidence status</th><th>Supporting phrase</th><th>Risk</th><th>Status</th><th>Recommended action</th></tr>{rows}</table><h2>Limitations</h2><p>{html.escape(report['limitations'])}</p></body></html>"""
