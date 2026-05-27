"""
Client onboarding pipeline — triggered when a new client pays.
Automatically:
1. Creates client record
2. Generates welcome email
3. Queues service delivery
4. Schedules first report
"""
import logging
from datetime import datetime, timedelta
from typing import Dict

from agency.ai.groq_client import chat
from agency.config import cfg, PACKAGES
from agency.db.models import insert_client, log_revenue, log_service_delivery, update_lead
from agency.outreach.email_sender import send_email

log = logging.getLogger(__name__)


def generate_welcome_email(client: Dict, package: Dict) -> tuple:
    business = client.get("business_name", "your business")
    contact = client.get("contact_name", "there")
    deliverables = "\n".join(f"• {d}" for d in package["deliverables"])

    prompt = f"""Write a warm onboarding welcome email from {cfg.agency_name} to {business}.

Client contact: {contact}
Package: {package['name']}
What they get:
{deliverables}

Email should:
- Confirm their setup is in progress
- Tell them what to expect in the next 48 hours
- List their deliverables clearly
- Invite them to reply with any questions
- Be warm, professional, confident
- Under 200 words
- Sign off: {cfg.owner_name}, {cfg.agency_name}

Return SUBJECT: then BODY:"""

    text = chat(prompt, max_tokens=400)
    if text:
        lines = text.strip().split("\n", 2)
        subject = lines[0].replace("SUBJECT:", "").strip()
        body = "\n".join(lines[2:]).strip() if len(lines) > 2 else text
        return subject, body

    # Fallback
    subject = f"Welcome to {cfg.agency_name} — You're all set!"
    body = f"""Hi {contact},

Welcome aboard! We're thrilled to have {business} as a client.

Your {package['name']} is now in progress. Here's what you'll receive:

{deliverables}

You'll hear from us within 48 hours with your first deliverables.

In the meantime, feel free to reply to this email with any questions.

{cfg.owner_name}
{cfg.agency_name}"""
    return subject, body


def onboard_client(
    lead_id: int,
    business_name: str,
    contact_name: str,
    email: str,
    phone: str,
    niche: str,
    plan: str,
    city: str = "",
) -> int:
    """Full onboarding flow. Returns client_id."""
    package = PACKAGES.get(plan, PACKAGES["starter"])
    mrr = package["mrr"]
    setup_fee = package["setup_fee"]

    next_report = (datetime.utcnow() + timedelta(days=30)).isoformat()

    client_id = insert_client({
        "lead_id": lead_id,
        "business_name": business_name,
        "contact_name": contact_name,
        "email": email,
        "phone": phone,
        "niche": niche,
        "service": package["name"],
        "plan": plan,
        "mrr": mrr,
        "setup_fee": setup_fee,
        "status": "onboarding",
        "onboarded_at": datetime.utcnow().isoformat(),
        "next_report_at": next_report,
    })

    log_revenue(client_id, setup_fee, "setup_fee", f"Setup fee — {package['name']}")
    log_revenue(client_id, mrr, "mrr_month1", f"Month 1 retainer — {package['name']}")

    if lead_id:
        update_lead(lead_id, {"status": "client"})

    client = {
        "id": client_id,
        "business_name": business_name,
        "contact_name": contact_name,
        "email": email,
        "niche": niche,
        "city": city,
        "plan": plan,
    }

    subject, body = generate_welcome_email(client, package)
    send_email(email, subject, body)

    _queue_services(client, plan)

    log.info(
        "Client onboarded: %s | Plan: %s | MRR: $%.2f | Setup: $%.2f",
        business_name, plan, mrr, setup_fee,
    )
    return client_id


def _queue_services(client: Dict, plan: str):
    """Trigger immediate service delivery based on plan."""
    from agency.services.chatbot_builder import deliver_chatbot_service
    from agency.services.review_agent import deliver_review_service
    from agency.services.content_agent import deliver_content_service

    deliver_chatbot_service(client)
    deliver_review_service(client)

    if plan == "pro":
        deliver_content_service(client)

    log.info("Services queued for %s (plan: %s)", client["business_name"], plan)
