"""
Review Agent — generates automated review-request SMS + email copy
and a 3-touch review sequence for clients.
"""
import logging
from typing import Dict, List

from agency.ai.groq_client import chat
from agency.config import cfg
from agency.db.models import log_service_delivery

log = logging.getLogger(__name__)


def generate_review_sequence(client: Dict) -> List[Dict]:
    """3-touch review request sequence: post-visit day 1, day 3 reminder, day 7 final."""
    business = client.get("business_name", "our business")
    niche = client.get("niche", "local service")

    touches = [
        {"day": 1, "channel": "SMS", "tone": "fresh and grateful, right after the visit"},
        {"day": 3, "channel": "Email", "tone": "gentle reminder, mention it only takes 60 seconds"},
        {"day": 7, "channel": "SMS", "tone": "final ask, personal and low-pressure"},
    ]

    sequence = []
    for touch in touches:
        if touch["channel"] == "SMS":
            prompt = f"""Write a review-request SMS for {business} ({niche.replace('_',' ')}).
Send timing: Day {touch['day']} after visit.
Tone: {touch['tone']}
- Under 160 characters (one SMS)
- Include {{first_name}} and {{review_link}} placeholders
- No emojis unless it feels natural for the niche
- DO NOT start with "Hi" + full business name — keep it personal"""
        else:
            prompt = f"""Write a review-request email for {business} ({niche.replace('_',' ')}).
Send timing: Day {touch['day']} after visit.
Tone: {touch['tone']}
- Subject line + body
- Body under 80 words
- Include {{first_name}} and {{review_link}} placeholders
- Warm, human sign-off
Return SUBJECT: then BODY: on separate lines."""

        text = chat(prompt, max_tokens=250)
        if text:
            message = text.strip()
        else:
            if touch["channel"] == "SMS":
                message = (
                    f"Hi {{first_name}}! Thanks for visiting {business}. "
                    f"If you have a moment, we'd love a Google review: {{review_link}} — means the world to us!"
                )
            else:
                message = (
                    f"Subject: Your experience at {business}\n\n"
                    f"Hi {{first_name}},\n\nWe hope your visit was everything you expected! "
                    f"If you have 60 seconds, a quick Google review helps our small business enormously.\n\n"
                    f"{{review_link}}\n\nThank you!"
                )

        sequence.append({
            "day": touch["day"],
            "channel": touch["channel"],
            "message": message,
        })

    return sequence


def generate_win_back_campaign(client: Dict) -> List[Dict]:
    """3-email win-back campaign for lapsed customers (no visit in 90+ days)."""
    business = client.get("business_name", "us")
    niche = client.get("niche", "local service")

    prompts = [
        "We miss you — friendly check-in, no offer yet",
        "Exclusive comeback offer (10-15% off)",
        "Final gentle nudge with urgency (offer expires in 48hrs)",
    ]

    result = []
    for i, p in enumerate(prompts):
        prompt = f"""Write win-back email #{i+1} for {business} ({niche.replace('_',' ')}).
Angle: {p}
- Under 100 words
- Use {{first_name}} placeholder
- Natural sign-off
Return SUBJECT: then BODY:"""

        text = chat(prompt, max_tokens=200)
        if text:
            lines = text.strip().split("\n", 2)
            subject = lines[0].replace("SUBJECT:", "").strip()
            body = "\n".join(lines[2:]).strip() if len(lines) > 2 else text
        else:
            subject = f"Win-back email {i+1}"
            body = f"[{business} — {p}]\n\n[Add GROQ_API_KEY for real copy]"

        result.append({"email_num": i + 1, "subject": subject, "body": body})

    return result


def deliver_review_service(client: Dict) -> bool:
    try:
        seq = generate_review_sequence(client)
        seq_text = "\n\n".join(
            f"DAY {s['day']} — {s['channel'].upper()}\n{s['message']}" for s in seq
        )
        log_service_delivery(
            client["id"],
            "review_sequence",
            f"Review Request Sequence — {client['business_name']}",
            seq_text,
        )

        wb = generate_win_back_campaign(client)
        wb_text = "\n\n".join(
            f"EMAIL {e['email_num']}\nSUBJECT: {e['subject']}\n\n{e['body']}" for e in wb
        )
        log_service_delivery(
            client["id"],
            "win_back",
            f"Win-Back Campaign — {client['business_name']}",
            wb_text,
        )
        log.info("Review service delivered for %s", client["business_name"])
        return True
    except Exception as e:
        log.error("Review delivery failed for %s: %s", client.get("business_name"), e)
        return False
