"""Generate hyper-personalized cold email copy with Groq AI (free)."""
import logging
from typing import Dict, Tuple

from agency.ai.groq_client import chat
from agency.config import cfg, NICHE_MAP, PACKAGES

log = logging.getLogger(__name__)


def _niche_context(niche_name: str) -> str:
    niche = NICHE_MAP.get(niche_name)
    if not niche:
        return ""
    pains = "\n".join(f"- {p}" for p in niche.pain_points)
    return f"Common pain points for {niche_name} businesses:\n{pains}"


def write_initial_email(lead: Dict) -> Tuple[str, str]:
    """Return (subject, body) for the first cold email."""
    niche_name = lead.get("niche", "local business")
    business = lead.get("business_name", "your business")
    city = lead.get("city", "")
    rating = lead.get("rating", 0)
    reviews = lead.get("review_count", 0)
    package = PACKAGES["starter"]

    context = _niche_context(niche_name)

    prompt = f"""You are writing a brief, human-sounding cold email for {cfg.agency_name}.
The owner's name is {cfg.owner_name}.

Target business:
- Name: {business}
- Type: {niche_name.replace('_', ' ')}
- City: {city}
- Rating: {rating} ({reviews} reviews)

{context}

Agency offers: AI chatbots, automated follow-up sequences, appointment reminders, review
generation — all hands-free for the business owner. Starting package: ${package['setup_fee']} setup
+ ${package['mrr']}/month.

Write a cold email that:
1. Is under 120 words
2. Opens with a specific observation about their business (use rating/reviews for personalization)
3. Mentions ONE specific pain point relevant to their niche
4. Makes a single clear offer: a free 15-minute demo
5. Closes with just first name — NO corporate sign-offs
6. Sounds like it was written by a real person, NOT a marketing template
7. NO emojis, NO bullet points in the email body

Return ONLY:
SUBJECT: <subject line>
BODY:
<email body>"""

    text = chat(prompt, max_tokens=400)
    if text:
        lines = text.strip().split("\n", 2)
        subject = lines[0].replace("SUBJECT:", "").strip() if lines else "Quick question"
        body = "\n".join(lines[2:]).strip() if len(lines) > 2 else text
        return subject, body

    # Fallback template
    subject = f"Quick question about {business}'s booking system"
    body = (
        f"Hi,\n\nI noticed {business} has {reviews} Google reviews — "
        f"strong presence in {city}.\n\n"
        f"Most {niche_name.replace('_', ' ')} owners I talk to lose 20-30% of potential "
        f"bookings simply because there's no one answering after hours.\n\n"
        f"I help businesses like yours set up an AI system that handles bookings, "
        f"follow-ups, and review requests automatically — no tech skills needed.\n\n"
        f"Would a 15-minute call this week make sense? Happy to show you exactly "
        f"how it works for free.\n\n{cfg.owner_name}"
    )
    return subject, body


def write_followup_email(lead: Dict, followup_num: int) -> Tuple[str, str]:
    """Return (subject, body) for follow-up #N."""
    business = lead.get("business_name", "your business")
    niche_name = lead.get("niche", "local business")

    angles = [
        "shorter bump — acknowledge they're busy, offer the same free demo",
        "share a one-line result (e.g. 'helped a similar business recover 12 missed bookings last month')",
        "final follow-up — give them an easy out but leave the door open",
    ]
    angle = angles[min(followup_num - 1, 2)]

    prompt = f"""Write follow-up email #{followup_num} to {business} (a {niche_name.replace('_',' ')} business).
This is after no response to prior email(s).
Angle: {angle}

Rules:
- Under 60 words
- No desperate tone
- No "just checking in"
- First-name sign-off only: {cfg.owner_name}
- Natural, direct, human

Return ONLY:
SUBJECT: <subject>
BODY:
<body>"""

    text = chat(prompt, max_tokens=200)
    if text:
        lines = text.strip().split("\n", 2)
        subject = lines[0].replace("SUBJECT:", "").strip()
        body = "\n".join(lines[2:]).strip() if len(lines) > 2 else text
        return subject, body

    # Fallback template
    subject = f"Re: {business} automation"
    body = (
        f"Hi,\n\nJust wanted to resurface this — I know things get busy.\n\n"
        f"If automating your booking follow-ups isn't a priority right now, totally understand. "
        f"If it is, I can show you the whole system in 15 minutes.\n\n"
        f"Worth a look?\n\n{cfg.owner_name}"
    )
    return subject, body
