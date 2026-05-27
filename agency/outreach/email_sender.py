"""Send emails via SMTP (Gmail / SendGrid) with daily rate limiting."""
import smtplib
import logging
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional

from agency.config import cfg
from agency.db.models import get_leads, update_lead, log_outreach, get_conn

log = logging.getLogger(__name__)


def _emails_sent_today() -> int:
    conn = get_conn()
    c = conn.cursor()
    row = c.execute(
        "SELECT COUNT(*) as cnt FROM outreach_log WHERE sent_at >= date('now')"
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


def send_email(to_email: str, subject: str, body: str, from_name: Optional[str] = None) -> bool:
    """Send a plain-text email. Returns True on success."""
    if not cfg.smtp_user or not cfg.smtp_pass:
        log.warning("SMTP not configured — logging email only")
        log.info("WOULD SEND → %s | %s", to_email, subject)
        return True  # treat as success in demo mode

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{from_name or cfg.owner_name} <{cfg.smtp_user}>"
        msg["To"] = to_email
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg.smtp_user, cfg.smtp_pass)
            server.sendmail(cfg.smtp_user, to_email, msg.as_string())
        return True
    except Exception as e:
        log.error("Email send failed to %s: %s", to_email, e)
        return False


def run_outreach():
    """
    Main outreach loop:
    1. Pull qualified leads with no email yet → send initial email
    2. Pull leads due for follow-up → send follow-up
    """
    from agency.outreach.email_writer import write_initial_email, write_followup_email

    sent_today = _emails_sent_today()
    remaining = cfg.outreach_daily_limit - sent_today
    if remaining <= 0:
        log.info("Daily outreach limit reached (%d). Skipping.", cfg.outreach_daily_limit)
        return 0

    total_sent = 0

    # ── Initial emails ───────────────────────────────────────────────────────
    new_leads = get_leads(status="qualified")
    for lead in new_leads:
        if not lead.get("email"):
            continue
        if total_sent >= remaining:
            break
        subject, body = write_initial_email(lead)
        ok = send_email(lead["email"], subject, body)
        if ok:
            update_lead(lead["id"], {
                "status": "contacted",
                "contacted_at": datetime.utcnow().isoformat(),
            })
            log_outreach(lead["id"], {"type": "email_initial", "subject": subject, "body": body})
            total_sent += 1
            log.info("Initial email sent → %s (%s)", lead["business_name"], lead["email"])

    # ── Follow-ups ────────────────────────────────────────────────────────────
    contacted = get_leads(status="contacted")
    now = datetime.utcnow()
    for lead in contacted:
        if total_sent >= remaining:
            break
        if not lead.get("email"):
            continue

        followup_count = lead.get("followup_count", 0)
        if followup_count >= len(cfg.followup_days):
            update_lead(lead["id"], {"status": "cold"})
            continue

        last_contact_str = lead.get("last_followup_at") or lead.get("contacted_at")
        if not last_contact_str:
            continue
        try:
            last_contact = datetime.fromisoformat(last_contact_str)
        except ValueError:
            continue

        days_due = cfg.followup_days[followup_count]
        if (now - last_contact).days < days_due:
            continue

        subject, body = write_followup_email(lead, followup_count + 1)
        ok = send_email(lead["email"], subject, body)
        if ok:
            update_lead(lead["id"], {
                "followup_count": followup_count + 1,
                "last_followup_at": now.isoformat(),
            })
            log_outreach(lead["id"], {
                "type": f"email_followup_{followup_count + 1}",
                "subject": subject,
                "body": body,
            })
            total_sent += 1
            log.info("Follow-up #%d sent → %s", followup_count + 1, lead["business_name"])

    log.info("Outreach run complete. Emails sent: %d", total_sent)
    return total_sent
