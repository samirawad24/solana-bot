"""Generate copy-paste-ready Fiverr gig listings for all 5 niches."""
import logging
from pathlib import Path
from typing import Dict

from agency.ai.groq_client import chat
from agency.config import NICHES, cfg

log = logging.getLogger(__name__)

_FALLBACKS = {
    "medspa": {
        "title": "I will set up an AI chatbot and booking automation for your med spa",
        "description": (
            "Transform your med spa's client experience with a 24/7 AI chatbot that handles "
            "appointment bookings, answers FAQs, and sends automated review requests — while you "
            "focus on delivering results. I'll set up the full system in 48 hours, customized to "
            "your services (Botox, fillers, laser, etc.), with a professional welcome flow and "
            "after-hours booking capture. No tech skills needed — I handle everything."
        ),
        "tags": ["chatbot", "med spa automation", "booking system", "AI assistant", "appointment booking"],
    },
    "hvac": {
        "title": "I will automate your HVAC business with AI booking and follow-up sequences",
        "description": (
            "Stop missing calls during peak season. I'll set up an AI chatbot that books service "
            "calls, captures emergency requests, and sends automated quote follow-ups — all on "
            "autopilot. Your customers get instant responses 24/7; you get more booked jobs without "
            "extra staff. Includes seasonal tune-up reminder sequences and a customer win-back campaign."
        ),
        "tags": ["HVAC automation", "booking chatbot", "service business", "lead follow-up", "AI assistant"],
    },
    "real_estate": {
        "title": "I will build AI lead follow-up and drip sequences for real estate agents",
        "description": (
            "Never let a lead go cold again. I'll set up automated email drip sequences, an AI "
            "chatbot for your listings page, and instant lead follow-up — all customized for your "
            "market. Buyers and sellers get immediate responses; you get more appointments. Includes "
            "a 6-email nurture sequence and a past-client referral campaign."
        ),
        "tags": ["real estate automation", "lead follow-up", "email drip", "chatbot", "realtor tools"],
    },
    "dental": {
        "title": "I will set up AI appointment reminders and a chatbot for your dental office",
        "description": (
            "Reduce no-shows and fill your schedule automatically. I'll set up an AI system that "
            "sends appointment reminders, handles booking requests after hours, and follows up on "
            "overdue recall patients — all without your front desk lifting a finger. Includes a "
            "custom chatbot trained on your services, FAQs, and insurance questions."
        ),
        "tags": ["dental automation", "appointment reminder", "patient recall", "chatbot", "dental office"],
    },
    "ecommerce": {
        "title": "I will set up abandoned cart recovery and post-purchase AI email sequences",
        "description": (
            "Recover lost sales and build repeat buyers automatically. I'll set up abandoned cart "
            "emails, a post-purchase thank-you + upsell sequence, and a customer support chatbot — "
            "all connected to your Shopify or WooCommerce store. Most clients recover 10-15% of "
            "abandoned carts within the first 30 days. Setup takes 48 hours."
        ),
        "tags": ["abandoned cart", "email automation", "ecommerce chatbot", "Shopify", "post-purchase email"],
    },
}

_FAQ_TEMPLATE = [
    ("How long does setup take?", "Most setups are live within 48-72 hours. I'll keep you updated at every step."),
    ("Do I need technical skills?", "None. I handle everything — you just review and approve the final setup."),
    ("What platform do you use?", "I use tools that fit your existing website (Tidio, Botpress, or custom embed) — no new software subscriptions required."),
    ("Can I make changes after launch?", "Yes. I'll give you a simple guide and remain available for tweaks during the first 14 days."),
    ("What if I don't get results?", "I offer one free optimization round in the first 30 days if the system isn't performing as expected."),
]


def generate_gig(niche_name: str) -> Dict:
    """Generate a complete Fiverr gig for a niche. Uses Groq if available."""
    niche = next((n for n in NICHES if n.name == niche_name), None)
    if not niche:
        return {}

    prompt = f"""Create a complete Fiverr gig listing for an AI automation service targeting {niche_name.replace('_', ' ')} businesses.

Include:
TITLE: (max 80 chars, starts with "I will")
DESCRIPTION: (max 800 chars, benefit-focused, no fluff)
TAGS: (5 relevant tags, comma-separated)

Key pain points to address: {', '.join(niche.pain_points[:2])}
Price range: ${int(niche.avg_setup_fee * 0.6)} basic / ${int(niche.avg_setup_fee)} standard / ${int(niche.avg_setup_fee * 1.5)} premium

Return exactly:
TITLE: ...
DESCRIPTION: ...
TAGS: ...
BASIC: (price and 1-line description)
STANDARD: (price and 1-line description)
PREMIUM: (price and 1-line description)"""

    result = chat(prompt, max_tokens=600)
    if result:
        lines = result.strip().split("\n")
        parsed = {}
        for line in lines:
            for key in ("TITLE", "DESCRIPTION", "TAGS", "BASIC", "STANDARD", "PREMIUM"):
                if line.startswith(f"{key}:"):
                    parsed[key.lower()] = line[len(key) + 1:].strip()
        if "title" in parsed and "description" in parsed:
            parsed["faq"] = _FAQ_TEMPLATE
            parsed["niche"] = niche_name
            return parsed

    # Fallback
    fb = _FALLBACKS.get(niche_name, _FALLBACKS["hvac"])
    setup = int(niche.avg_setup_fee)
    return {
        "niche": niche_name,
        "title": fb["title"],
        "description": fb["description"],
        "tags": fb["tags"],
        "basic": f"${int(setup * 0.6)} — Chatbot setup + FAQ configuration",
        "standard": f"${setup} — Full automation suite + email sequences",
        "premium": f"${int(setup * 1.5)} — Everything + 30-day optimization + priority support",
        "faq": _FAQ_TEMPLATE,
    }


def generate_all_gigs() -> None:
    """Generate Fiverr gig files for all niches and save to data/fiverr_gigs/."""
    out_dir = Path("data/fiverr_gigs")
    out_dir.mkdir(parents=True, exist_ok=True)

    for niche in NICHES:
        gig = generate_gig(niche.name)
        if not gig:
            continue

        faq_text = "\n\n".join(f"Q: {q}\nA: {a}" for q, a in gig.get("faq", []))
        content = f"""FIVERR GIG — {niche.name.upper().replace('_', ' ')}
{'='*60}

GIG TITLE:
{gig.get('title', '')}

DESCRIPTION:
{gig.get('description', '')}

TAGS (enter each separately on Fiverr):
{', '.join(gig['tags']) if isinstance(gig.get('tags'), list) else gig.get('tags', '')}

PRICING TIERS:
  Basic:    {gig.get('basic', '')}
  Standard: {gig.get('standard', '')}
  Premium:  {gig.get('premium', '')}

FAQ SECTION:
{faq_text}

{'='*60}
Generated by AutoFlow AI Agency — copy-paste each section into Fiverr.
"""
        path = out_dir / f"{niche.name}.txt"
        path.write_text(content)
        print(f"  ✓ {niche.name}: {path}")
        log.info("Fiverr gig saved: %s", path)

    print(f"\nAll gigs saved to {out_dir.resolve()}/")
