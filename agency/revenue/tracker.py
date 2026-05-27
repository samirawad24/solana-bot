"""Revenue tracker — MRR, weekly income, forecasting, and alerts."""
import logging
from datetime import datetime, timedelta
from typing import Dict
from agency.db.models import get_conn, get_mrr, get_revenue_this_week
from agency.config import cfg

log = logging.getLogger(__name__)


def get_revenue_summary() -> Dict:
    conn = get_conn()
    c = conn.cursor()

    mrr = get_mrr()
    arr = mrr * 12
    weekly = get_revenue_this_week()

    # Total all-time revenue
    row = c.execute("SELECT SUM(amount) as total FROM revenue_log").fetchone()
    total = row["total"] or 0

    # Active clients
    row2 = c.execute("SELECT COUNT(*) as cnt FROM clients WHERE status='active'").fetchone()
    active_clients = row2["cnt"] or 0

    # Pipeline (onboarding)
    row3 = c.execute("SELECT COUNT(*) as cnt FROM clients WHERE status='onboarding'").fetchone()
    pipeline_clients = row3["cnt"] or 0

    # Leads stats
    row4 = c.execute("SELECT COUNT(*) as cnt FROM leads").fetchone()
    total_leads = row4["cnt"] or 0

    row5 = c.execute("SELECT COUNT(*) as cnt FROM leads WHERE status='contacted'").fetchone()
    contacted_leads = row5["cnt"] or 0

    # Revenue by type
    rows = c.execute(
        "SELECT type, SUM(amount) as total FROM revenue_log GROUP BY type"
    ).fetchall()
    by_type = {r["type"]: r["total"] for r in rows}

    # Last 8 weeks of revenue
    weekly_history = []
    for i in range(7, -1, -1):
        start = (datetime.utcnow() - timedelta(days=(i + 1) * 7)).isoformat()
        end = (datetime.utcnow() - timedelta(days=i * 7)).isoformat()
        row = c.execute(
            "SELECT SUM(amount) as w FROM revenue_log WHERE recorded_at BETWEEN ? AND ?",
            (start, end),
        ).fetchone()
        weekly_history.append({"week": 7 - i, "amount": row["w"] or 0})

    conn.close()

    target = cfg.weekly_revenue_target
    pct_of_target = (weekly / target * 100) if target > 0 else 0

    return {
        "mrr": round(mrr, 2),
        "arr": round(arr, 2),
        "weekly_revenue": round(weekly, 2),
        "weekly_target": target,
        "weekly_pct_of_target": round(pct_of_target, 1),
        "total_revenue": round(total, 2),
        "active_clients": active_clients,
        "pipeline_clients": pipeline_clients,
        "total_leads": total_leads,
        "contacted_leads": contacted_leads,
        "revenue_by_type": by_type,
        "weekly_history": weekly_history,
        "months_to_target": _months_to_weekly_target(mrr, target),
    }


def _months_to_weekly_target(current_mrr: float, weekly_target: float) -> float:
    monthly_target = weekly_target * 4.33
    if current_mrr >= monthly_target:
        return 0.0
    # Assume 1 new client / month at $350 avg MRR
    avg_new_mrr = 350.0
    if avg_new_mrr <= 0:
        return 99.0
    gap = monthly_target - current_mrr
    return round(gap / avg_new_mrr, 1)


def log_manual_revenue(amount: float, rev_type: str, description: str, client_id: int = 0):
    """Helper for manually logging a payment (e.g. from Stripe dashboard)."""
    from agency.db.models import log_revenue
    log_revenue(client_id, amount, rev_type, description)
    log.info("Manual revenue logged: $%.2f (%s)", amount, rev_type)


def check_weekly_alert():
    """Log a warning if weekly revenue is below 50% of target."""
    summary = get_revenue_summary()
    pct = summary["weekly_pct_of_target"]
    if pct < 50:
        log.warning(
            "REVENUE ALERT: Weekly revenue $%.2f is only %.1f%% of $%.2f target.",
            summary["weekly_revenue"],
            pct,
            summary["weekly_target"],
        )
    else:
        log.info(
            "Revenue OK: $%.2f this week (%.1f%% of target)",
            summary["weekly_revenue"],
            pct,
        )
    return summary
