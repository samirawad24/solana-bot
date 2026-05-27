"""Upwork job monitor — generates full copy-paste-ready proposals."""
import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional

import requests

from agency.ai.groq_client import chat
from agency.db.models import get_conn

log = logging.getLogger(__name__)

RSS_FEEDS = [
    "https://www.upwork.com/ab/feed/jobs/rss?q=chatbot+automation&sort=recency&paging=0%3B10",
    "https://www.upwork.com/ab/feed/jobs/rss?q=AI+automation+small+business&sort=recency&paging=0%3B10",
    "https://www.upwork.com/ab/feed/jobs/rss?q=email+automation+CRM&sort=recency&paging=0%3B10",
    "https://www.upwork.com/ab/feed/jobs/rss?q=lead+generation+automation&sort=recency&paging=0%3B10",
    "https://www.upwork.com/ab/feed/jobs/rss?q=local+business+marketing+automation&sort=recency&paging=0%3B10",
]

SCORE_KEYWORDS = {
    "high": ["chatbot", "automation", "AI", "local business", "CRM", "booking", "follow-up",
             "email sequence", "lead generation", "appointment"],
    "low": ["wordpress", "graphic design", "translation", "data entry", "logo"],
}


def _fetch_rss(url: str) -> List[Dict]:
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(r.content)
        items = []
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            desc = (item.findtext("description") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            items.append({"title": title, "description": desc, "link": link, "published": pub})
        return items
    except Exception as e:
        log.warning("RSS fetch failed for %s: %s", url, e)
        return []


def _score(opp: Dict) -> int:
    text = f"{opp['title']} {opp['description']}".lower()
    score = 0
    for kw in SCORE_KEYWORDS["high"]:
        if kw.lower() in text:
            score += 10
    for kw in SCORE_KEYWORDS["low"]:
        if kw.lower() in text:
            score -= 15
    return max(0, min(100, score))


def _ensure_proposal_column():
    conn = get_conn()
    try:
        conn.execute("ALTER TABLE niche_opportunities ADD COLUMN proposal TEXT")
        conn.commit()
    except Exception:
        pass  # column already exists
    conn.close()


def generate_full_proposal(opp: Dict) -> str:
    """Generate a complete ~180-word Upwork proposal using Groq."""
    prompt = f"""Write a complete Upwork proposal (180 words max) for this job posting:

Job Title: {opp['title']}
Job Description: {opp['description'][:600]}

The proposal should:
1. Open with proof you understand their specific need (reference something from the description)
2. Briefly describe your approach (AI chatbots, automation workflows, email sequences)
3. Mention a relevant result (e.g. "helped a similar business reduce missed bookings by 30%")
4. Ask ONE smart clarifying question that shows expertise
5. End with a soft CTA ("Happy to jump on a quick call")

Tone: direct, confident, NOT salesy. No "I hope this finds you well". No bullet points.
Return the proposal text only."""

    result = chat(prompt, max_tokens=300)
    if result:
        return result.strip()

    # Hardcoded fallback
    return (
        f"I've built AI automation systems for local businesses exactly like what you're describing — "
        f"chatbots that handle bookings after hours, email follow-up sequences, and review generation "
        f"that runs without the owner lifting a finger.\n\n"
        f"For a project like this, I'd start by mapping your current workflow gaps, then deploy a "
        f"lightweight automation stack (usually Zapier + a chatbot layer + email sequences) that fits "
        f"your existing tools.\n\n"
        f"One quick question: are you looking for a one-time setup you can manage yourself, or an "
        f"ongoing system where I handle maintenance and optimization?\n\n"
        f"Happy to jump on a quick 15-minute call to scope this out properly."
    )


def run_job_monitor() -> List[Dict]:
    """Fetch Upwork RSS feeds, score jobs, generate proposals for top ones."""
    _ensure_proposal_column()

    seen = set()
    all_opps = []

    for feed_url in RSS_FEEDS:
        items = _fetch_rss(feed_url)
        for item in items:
            key = item["title"][:80]
            if key in seen:
                continue
            seen.add(key)
            score = _score(item)
            item["score"] = score
            all_opps.append(item)

    # Sort by score descending
    all_opps.sort(key=lambda x: x["score"], reverse=True)
    top = all_opps[:10]

    conn = get_conn()
    for opp in top:
        if opp["score"] >= 50:
            proposal = generate_full_proposal(opp)
            opp["proposal"] = proposal
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO niche_opportunities
                       (source, title, description, url, score, proposal)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    ("upwork", opp["title"], opp["description"][:1000],
                     opp["link"], opp["score"], proposal),
                )
            except Exception:
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO niche_opportunities
                           (source, title, description, url, score)
                           VALUES (?, ?, ?, ?, ?)""",
                        ("upwork", opp["title"], opp["description"][:1000],
                         opp["link"], opp["score"]),
                    )
                except Exception as e:
                    log.warning("DB insert failed: %s", e)
        else:
            opp["proposal"] = ""

    conn.commit()
    conn.close()

    log.info("Job monitor: %d opportunities, %d with proposals",
             len(top), sum(1 for o in top if o.get("proposal")))
    return top


def get_proposals_for_review(limit: int = 5) -> List[Dict]:
    """Return highest-scored unacted opportunities with proposals."""
    conn = get_conn()
    try:
        rows = conn.execute(
            """SELECT title, description, url, score, proposal
               FROM niche_opportunities
               WHERE proposal IS NOT NULL AND proposal != ''
               ORDER BY score DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        result = [dict(r) for r in rows]
    except Exception:
        result = []
    conn.close()
    return result
