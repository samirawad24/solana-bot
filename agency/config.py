"""Central configuration for the AI Agency system."""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

ROOT = Path(__file__).parent


@dataclass
class NicheConfig:
    name: str
    search_terms: List[str]
    pain_points: List[str]
    avg_setup_fee: float
    avg_mrr: float
    close_rate: float      # estimated % of reached leads that convert
    automation_score: int  # 1-10, how automatable delivery is


@dataclass
class AgencyConfig:
    # Business identity
    agency_name: str = os.getenv("AGENCY_NAME", "AutoFlow AI Agency")
    owner_name: str = os.getenv("OWNER_NAME", "Alex")
    owner_email: str = os.getenv("OWNER_EMAIL", "")
    owner_phone: str = os.getenv("OWNER_PHONE", "")
    website: str = os.getenv("AGENCY_WEBSITE", "https://autoflowagency.com")

    # API keys
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    google_places_api_key: str = os.getenv("GOOGLE_PLACES_API_KEY", "")
    sendgrid_api_key: str = os.getenv("SENDGRID_API_KEY", "")
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    hunter_api_key: str = os.getenv("HUNTER_API_KEY", "")  # email finder

    # Email settings
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_pass: str = os.getenv("SMTP_PASS", "")

    # Lead gen settings
    leads_per_run: int = int(os.getenv("LEADS_PER_RUN", "20"))
    target_cities: List[str] = field(default_factory=lambda: [
        "Austin TX", "Phoenix AZ", "Nashville TN", "Charlotte NC",
        "Tampa FL", "Denver CO", "Las Vegas NV", "Raleigh NC",
        "Jacksonville FL", "Columbus OH"
    ])
    outreach_daily_limit: int = int(os.getenv("OUTREACH_DAILY_LIMIT", "15"))
    followup_days: List[int] = field(default_factory=lambda: [3, 7, 14])

    # Revenue targets
    weekly_revenue_target: float = float(os.getenv("WEEKLY_REVENUE_TARGET", "1000.0"))

    # Scheduling (hours, 24h)
    lead_gen_hour: int = 7
    outreach_hour: int = 9
    service_delivery_hour: int = 11
    reporting_hour: int = 16


# ── Top 5 validated niches (based on 2026 research) ──────────────────────────
NICHES: List[NicheConfig] = [
    NicheConfig(
        name="medspa",
        search_terms=["med spa", "medspa", "botox clinic", "laser aesthetics"],
        pain_points=[
            "missing appointment bookings after hours",
            "spending hours on manual follow-up texts",
            "no automated review collection",
            "losing leads that never get called back",
        ],
        avg_setup_fee=800.0,
        avg_mrr=350.0,
        close_rate=0.12,
        automation_score=9,
    ),
    NicheConfig(
        name="hvac",
        search_terms=["HVAC contractor", "heating and cooling", "AC repair", "furnace repair"],
        pain_points=[
            "missing 30-40% of calls during peak season",
            "no 24/7 booking system",
            "manual quote follow-ups eating hours each week",
            "no automated customer win-back sequences",
        ],
        avg_setup_fee=600.0,
        avg_mrr=300.0,
        close_rate=0.10,
        automation_score=9,
    ),
    NicheConfig(
        name="real_estate",
        search_terms=["real estate agent", "realtor", "real estate broker", "property management"],
        pain_points=[
            "leads going cold before first contact",
            "manually sending listing updates to hundreds of contacts",
            "no automated drip campaigns for past clients",
            "hours lost to copy-pasting leads into CRM",
        ],
        avg_setup_fee=700.0,
        avg_mrr=400.0,
        close_rate=0.08,
        automation_score=8,
    ),
    NicheConfig(
        name="dental",
        search_terms=["dentist", "dental clinic", "orthodontist", "dental office"],
        pain_points=[
            "appointment no-shows costing $200-500 per slot",
            "no automated recall for overdue patients",
            "manual insurance verification wasting front-desk time",
            "no online booking or after-hours chatbot",
        ],
        avg_setup_fee=750.0,
        avg_mrr=350.0,
        close_rate=0.11,
        automation_score=9,
    ),
    NicheConfig(
        name="ecommerce",
        search_terms=["ecommerce store", "online shop", "Shopify store", "Amazon seller"],
        pain_points=[
            "abandoned cart recovery not set up",
            "product listings not optimized for search",
            "no automated post-purchase email sequence",
            "customer support overwhelmed with repetitive questions",
        ],
        avg_setup_fee=500.0,
        avg_mrr=500.0,
        close_rate=0.09,
        automation_score=10,
    ),
]

NICHE_MAP = {n.name: n for n in NICHES}

# ── Service packages ──────────────────────────────────────────────────────────
PACKAGES = {
    "starter": {
        "name": "Starter Automation",
        "setup_fee": 497,
        "mrr": 197,
        "deliverables": [
            "AI chatbot on website (FAQ + booking)",
            "Automated review request sequence (3 emails/SMS)",
            "Monthly performance report",
        ],
    },
    "growth": {
        "name": "Growth Engine",
        "setup_fee": 797,
        "mrr": 397,
        "deliverables": [
            "AI chatbot on website + WhatsApp",
            "Full drip email sequence (6-touch, 30 days)",
            "Automated lead follow-up (3-day SMS + email)",
            "Review request sequence",
            "Bi-weekly performance report",
        ],
    },
    "pro": {
        "name": "Pro Agency",
        "setup_fee": 1297,
        "mrr": 697,
        "deliverables": [
            "Everything in Growth",
            "Automated appointment reminders",
            "AI-powered monthly SEO blog post",
            "Abandoned lead win-back campaign",
            "Weekly KPI dashboard",
            "Priority support",
        ],
    },
}

cfg = AgencyConfig()
