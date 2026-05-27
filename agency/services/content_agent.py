"""
Content Agent — auto-generates SEO blog posts, email sequences, and
review-request copy for clients. Pro plan deliverable.
"""
import logging
from typing import Dict, List

from agency.ai.groq_client import chat
from agency.config import cfg, NICHE_MAP
from agency.db.models import log_service_delivery

log = logging.getLogger(__name__)


def generate_seo_blog_post(client: Dict) -> str:
    business = client.get("business_name", "the business")
    niche = client.get("niche", "local service")
    city = client.get("city", "your city")
    niche_obj = NICHE_MAP.get(niche)
    services = niche_obj.search_terms[:2] if niche_obj else [niche]

    prompt = f"""Write a 600-word SEO-optimized blog post for {business}, a {niche.replace('_',' ')} business in {city}.

Topic: "Top 5 Questions to Ask When Choosing a {niche.replace('_',' ').title()} in {city}"

Requirements:
- Target keyword naturally woven in: "{services[0]} in {city}"
- Conversational but authoritative tone
- One H1, three H2 subheadings
- Include a soft CTA at the end pointing to booking
- No fluff, no filler paragraphs
- Use local references where plausible (mention {city} 3-4 times)
- 600-650 words exactly

Output: the blog post only, no commentary."""

    result = chat(prompt, max_tokens=1200)
    if result:
        return result

    return f"""# Top 5 Questions to Ask When Choosing a {niche.replace('_',' ').title()} in {city}

Finding the right {niche.replace('_',' ')} in {city} can feel overwhelming...

[Add GROQ_API_KEY to generate real SEO content]

## What Services Do They Offer?
...

## Are They Licensed and Insured?
...

## What Do Local Reviews Say?
...

**Ready to experience the difference?** Book your appointment with {business} today.
"""


def generate_email_drip_sequence(client: Dict, num_emails: int = 6) -> List[Dict]:
    """Return list of {subject, body} for a full drip sequence."""
    business = client.get("business_name", "the business")
    niche = client.get("niche", "local service")

    sequence_brief = [
        "Welcome + what to expect (warm, personal)",
        "Educational tip relevant to their situation",
        "Social proof / testimonial story",
        "Common mistake to avoid in this niche",
        "Exclusive offer or incentive (10% off next visit)",
        "Re-engagement — ask for a review / referral",
    ]

    emails = []
    for i, brief in enumerate(sequence_brief[:num_emails]):
        prompt = f"""Write email #{i+1} of a {num_emails}-email drip sequence for {business} ({niche.replace('_',' ')}).
Purpose: {brief}
Tone: warm, human, conversational — NOT salesy
Length: 100-150 words
Sign off with first name only.
Return SUBJECT: and BODY: on separate lines."""

        text = chat(prompt, max_tokens=300)
        if text:
            lines = text.strip().split("\n", 2)
            subject = lines[0].replace("SUBJECT:", "").strip()
            body = "\n".join(lines[2:]).strip() if len(lines) > 2 else text
        else:
            subject = f"Email {i+1}: {brief}"
            body = f"[{business} — {brief}]\n\n[Add GROQ_API_KEY to generate real copy]"

        emails.append({"email_num": i + 1, "subject": subject, "body": body})

    return emails


def deliver_content_service(client: Dict) -> bool:
    try:
        blog = generate_seo_blog_post(client)
        log_service_delivery(
            client["id"],
            "seo_blog",
            f"Monthly SEO Post — {client['business_name']}",
            blog,
        )

        drip = generate_email_drip_sequence(client)
        drip_text = "\n\n".join(
            f"EMAIL {e['email_num']}\nSUBJECT: {e['subject']}\n\n{e['body']}"
            for e in drip
        )
        log_service_delivery(
            client["id"],
            "email_sequence",
            f"6-Email Drip Sequence — {client['business_name']}",
            drip_text,
        )
        log.info("Content service delivered for %s", client["business_name"])
        return True
    except Exception as e:
        log.error("Content delivery failed for %s: %s", client.get("business_name"), e)
        return False
