"""
Automated monthly client report generator.
Pulls service delivery data and wraps it in a professional summary using Groq AI.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from agency.ai.groq_client import chat
from agency.config import cfg
from agency.db.models import get_clients, get_conn, update_lead
from agency.outreach.email_sender import send_email

log = logging.getLogger(__name__)


def _get_deliveries(client_id: int) -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    rows = c.execute(
        "SELECT * FROM services_delivered WHERE client_id=? ORDER BY delivered_at DESC LIMIT 20",
        (client_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _get_outreach_stats(lead_id: int) -> Dict:
    if not lead_id:
        return {}
    conn = get_conn()
    c = conn.cursor()
    row = c.execute(
        "SELECT COUNT(*) as total, SUM(replied) as replies FROM outreach_log WHERE lead_id=?",
        (lead_id,),
    ).fetchone()
    conn.close()
    return {"emails_sent": row["total"] or 0, "replies": row["replies"] or 0}


def generate_report(client: Dict) -> str:
    business = client.get("business_name", "your business")
    plan = client.get("plan", "starter")
    deliveries = _get_deliveries(client["id"])

    delivery_summary = "\n".join(
        f"- {d['service_type'].replace('_', ' ').title()}: {d['title']} (delivered {d['delivered_at'][:10]})"
        for d in deliveries
    ) or "- No deliveries this period"

    prompt = f"""Write a professional monthly report for {business}.
Agency: {cfg.agency_name}
Plan: {plan.title()}
Reporting period: {(datetime.utcnow() - timedelta(days=30)).strftime('%B %Y')}

Services delivered this month:
{delivery_summary}

Write the report with:
1. Executive Summary (2 sentences)
2. What We Did This Month (expand on each delivery, 1-2 sentences each)
3. What This Means for Your Business (estimated impact — be specific and optimistic but honest)
4. Next Month's Focus (1-2 things we'll work on next)
5. Quick Win Tip (one actionable thing they can do themselves this week)

Tone: professional, confident, results-focused. Use plain language, no jargon.
Under 350 words total."""

    result = chat(prompt, max_tokens=700)
    header = (
        f"MONTHLY REPORT — {business.upper()}\n"
        f"{cfg.agency_name} | {datetime.utcnow().strftime('%B %Y')}\n"
        f"{'='*60}\n\n"
    )

    if result:
        return header + result

    return header + f"""EXECUTIVE SUMMARY
Your automation systems are running and delivering consistent value. Here's a summary of this month's activity.

WHAT WE DID THIS MONTH
{delivery_summary}

WHAT THIS MEANS FOR YOUR BUSINESS
Every automated touchpoint saves you approximately 2-3 hours of manual follow-up work per week. Over a month, that's 8-12 hours back in your calendar.

NEXT MONTH'S FOCUS
We'll review chatbot performance data and optimize the booking flow based on real customer interactions.

QUICK WIN TIP
Ask your next 5 customers directly: "How did you hear about us?" — the answers will sharpen your marketing fast.

— {cfg.owner_name}, {cfg.agency_name}"""


def send_monthly_reports():
    """Send reports to all active clients whose next_report_at has passed."""
    clients = get_clients(status="active")
    now = datetime.utcnow()
    sent = 0

    for client in clients:
        next_report_str = client.get("next_report_at")
        if not next_report_str:
            continue
        try:
            next_report = datetime.fromisoformat(next_report_str)
        except ValueError:
            continue

        if now < next_report:
            continue

        report_text = generate_report(client)
        subject = f"Your {datetime.utcnow().strftime('%B')} Report from {cfg.agency_name}"
        body = (
            f"Hi {client.get('contact_name', 'there')},\n\n"
            f"Here's your monthly performance report:\n\n"
            f"{report_text}\n\n"
            f"Reply to this email anytime — we're here.\n\n"
            f"{cfg.owner_name}"
        )

        ok = send_email(client["email"], subject, body)
        if ok:
            next_dt = (now + timedelta(days=30)).isoformat()
            conn = get_conn()
            c = conn.cursor()
            c.execute(
                "UPDATE clients SET next_report_at=? WHERE id=?",
                (next_dt, client["id"]),
            )
            conn.commit()
            conn.close()
            sent += 1
            log.info("Monthly report sent to %s", client["business_name"])

    log.info("Reports sent: %d", sent)
    return sent
