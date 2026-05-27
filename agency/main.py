"""
AI Agency Orchestrator — the always-on engine that runs all automation tasks.

Schedule (all UTC):
  07:00 — Lead discovery (Google Places)
  07:30 — Lead scoring & qualification
  09:00 — Outreach (initial emails + follow-ups)
  10:00 — Niche opportunity research (Upwork)
  11:00 — Service delivery for new clients
  16:00 — Monthly report dispatch
  Every hour — Revenue health check

Run with:  python -m agency.main
Or as a background service.
"""
import os
import sys
import logging
import time
import schedule
from datetime import datetime
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agency.db.models import init_db
from agency.config import cfg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            Path(__file__).parent.parent / "data" / "agency.log",
            mode="a",
        ),
    ],
)
log = logging.getLogger("agency.main")


# ── Task wrappers ─────────────────────────────────────────────────────────────

def task_lead_discovery():
    log.info("=== TASK: Lead Discovery ===")
    try:
        from agency.leads.finder import run_lead_discovery
        n = run_lead_discovery()
        log.info("Lead discovery complete — %d new leads", n)
    except Exception as e:
        log.error("Lead discovery failed: %s", e, exc_info=True)


def task_qualify_leads():
    log.info("=== TASK: Lead Qualification ===")
    try:
        from agency.leads.scorer import qualify_leads
        n = qualify_leads()
        log.info("Qualification complete — %d leads promoted", n)
    except Exception as e:
        log.error("Lead qualification failed: %s", e, exc_info=True)


def task_outreach():
    log.info("=== TASK: Outreach ===")
    try:
        from agency.outreach.email_sender import run_outreach
        n = run_outreach()
        log.info("Outreach complete — %d emails sent", n)
    except Exception as e:
        log.error("Outreach failed: %s", e, exc_info=True)


def task_niche_research():
    log.info("=== TASK: Niche Research ===")
    try:
        from agency.niches.researcher import run_niche_research
        opps = run_niche_research()
        log.info("Niche research complete — %d opportunities found", len(opps))
    except Exception as e:
        log.error("Niche research failed: %s", e, exc_info=True)


def task_service_delivery():
    log.info("=== TASK: Service Delivery ===")
    try:
        from agency.db.models import get_clients
        from agency.services.chatbot_builder import deliver_chatbot_service
        from agency.services.review_agent import deliver_review_service

        clients = get_clients(status="onboarding")
        for client in clients:
            deliver_chatbot_service(client)
            deliver_review_service(client)
            # Move to active
            from agency.db.models import get_conn
            conn = get_conn()
            conn.execute(
                "UPDATE clients SET status='active' WHERE id=?",
                (client["id"],),
            )
            conn.commit()
            conn.close()
            log.info("Client activated: %s", client["business_name"])
    except Exception as e:
        log.error("Service delivery failed: %s", e, exc_info=True)


def task_send_reports():
    log.info("=== TASK: Monthly Reports ===")
    try:
        from agency.reporting.client_report import send_monthly_reports
        n = send_monthly_reports()
        log.info("Reports sent: %d", n)
    except Exception as e:
        log.error("Report dispatch failed: %s", e, exc_info=True)


def task_revenue_check():
    try:
        from agency.revenue.tracker import check_weekly_alert
        check_weekly_alert()
    except Exception as e:
        log.error("Revenue check failed: %s", e)


# ── Scheduler setup ───────────────────────────────────────────────────────────

def setup_schedule():
    schedule.every().day.at("07:00").do(task_lead_discovery)
    schedule.every().day.at("07:30").do(task_qualify_leads)
    schedule.every().day.at("09:00").do(task_outreach)
    schedule.every().day.at("10:00").do(task_niche_research)
    schedule.every().day.at("11:00").do(task_service_delivery)
    schedule.every().day.at("16:00").do(task_send_reports)
    schedule.every(1).hours.do(task_revenue_check)
    log.info("Scheduler configured with %d jobs", len(schedule.jobs))


def run_all_now():
    """Run every task immediately — useful for testing / first-time setup."""
    log.info("Running all tasks immediately (test/setup mode)")
    task_lead_discovery()
    task_qualify_leads()
    task_niche_research()
    task_service_delivery()
    task_send_reports()
    task_revenue_check()
    log.info("All tasks complete.")


def main():
    log.info("=" * 60)
    log.info("%s — Agent Starting", cfg.agency_name)
    log.info("Weekly target: $%.2f", cfg.weekly_revenue_target)
    log.info("=" * 60)

    # Ensure DB and data dir exist
    Path("data").mkdir(exist_ok=True)
    init_db()
    log.info("Database initialized.")

    # Check for --now flag (run immediately then exit)
    if "--now" in sys.argv:
        run_all_now()
        return

    setup_schedule()

    # Run once immediately on start
    task_lead_discovery()
    task_qualify_leads()
    task_niche_research()

    log.info("Entering main loop — agent is running hands-free.")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
