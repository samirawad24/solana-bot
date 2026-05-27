"""
Niche Opportunity Researcher — scrapes Upwork RSS and public job boards
for automation opportunities, scores them, and surfaces the best ones.
"""
import re
import logging
import requests
from datetime import datetime
from typing import List, Dict
import anthropic

from agency.config import cfg
from agency.db.models import save_opportunity

log = logging.getLogger(__name__)

# Upwork RSS feeds for relevant categories
UPWORK_FEEDS = [
    "https://www.upwork.com/ab/feed/jobs/rss?q=AI+chatbot+setup&sort=recency",
    "https://www.upwork.com/ab/feed/jobs/rss?q=automation+workflow+local+business&sort=recency",
    "https://www.upwork.com/ab/feed/jobs/rss?q=email+automation+sequence&sort=recency",
    "https://www.upwork.com/ab/feed/jobs/rss?q=n8n+make+automation&sort=recency",
    "https://www.upwork.com/ab/feed/jobs/rss?q=AI+agent+setup&sort=recency",
]

HIGH_VALUE_KEYWORDS = [
    "automation", "chatbot", "AI agent", "n8n", "make.com", "zapier", "workflow",
    "lead generation", "CRM", "email sequence", "drip campaign", "booking system",
    "appointment", "follow-up", "review", "local business",
]

AVOID_KEYWORDS = [
    "trading bot", "crypto", "gambling", "adult", "spam", "scraping competitor",
]


def fetch_upwork_opportunities() -> List[Dict]:
    """Pull latest jobs from Upwork RSS feeds."""
    items = []
    for url in UPWORK_FEEDS:
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                continue
            # Parse RSS manually (lightweight)
            raw = r.text
            titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", raw)
            descs = re.findall(r"<description><!\[CDATA\[(.*?)\]\]></description>", raw, re.DOTALL)
            links = re.findall(r"<link>(https://www\.upwork\.com/jobs/.*?)</link>", raw)

            for i, title in enumerate(titles[1:], 0):  # skip feed title
                desc = descs[i + 1] if i + 1 < len(descs) else ""
                link = links[i] if i < len(links) else ""
                items.append({
                    "platform": "upwork",
                    "title": title,
                    "description": re.sub(r"<[^>]+>", "", desc)[:500],
                    "url": link,
                })
        except Exception as e:
            log.debug("Feed fetch error %s: %s", url, e)

    return items


def score_opportunity(opp: Dict) -> int:
    """Score 0-100 based on keyword match and budget signals."""
    text = (opp.get("title", "") + " " + opp.get("description", "")).lower()

    for kw in AVOID_KEYWORDS:
        if kw.lower() in text:
            return 0

    score = 0
    for kw in HIGH_VALUE_KEYWORDS:
        if kw.lower() in text:
            score += 8

    # Budget signals in description
    budget_match = re.search(r"\$(\d+[\d,]*)", opp.get("description", ""))
    if budget_match:
        budget = int(budget_match.group(1).replace(",", ""))
        if budget >= 500:
            score += 20
        elif budget >= 200:
            score += 10

    return min(score, 100)


def analyze_opportunity_with_ai(opp: Dict) -> str:
    """Use Claude to generate a quick pitch angle for a top opportunity."""
    if not cfg.anthropic_api_key:
        return "Connect ANTHROPIC_API_KEY to get AI-generated pitch angles."

    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    prompt = f"""Job posting on {opp['platform'].title()}:
Title: {opp['title']}
Description: {opp['description'][:300]}

You are {cfg.agency_name}. Write a 3-sentence Upwork proposal opener that:
1. Shows you understand their exact problem
2. Mentions your automation approach (not generic)
3. Ends with a specific question to start dialogue
Do not mention price. Under 80 words."""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def run_niche_research() -> List[Dict]:
    """Full research run — fetch, score, save top opportunities."""
    opps = fetch_upwork_opportunities()
    log.info("Fetched %d raw opportunities", len(opps))

    scored = []
    for opp in opps:
        s = score_opportunity(opp)
        if s >= 30:
            opp["score"] = s
            # Extract budget
            bm = re.search(r"\$(\d+[\d,]*)", opp.get("description", ""))
            opp["budget_min"] = float(bm.group(1).replace(",", "")) if bm else 0
            opp["budget_max"] = opp["budget_min"]
            save_opportunity(opp)
            scored.append(opp)

    scored.sort(key=lambda x: x["score"], reverse=True)
    log.info("Saved %d qualifying opportunities", len(scored))
    return scored[:10]  # return top 10


def get_top_opportunities(limit: int = 10) -> List[Dict]:
    from agency.db.models import get_conn
    conn = get_conn()
    c = conn.cursor()
    rows = c.execute(
        "SELECT * FROM niche_opportunities WHERE acted_on=0 ORDER BY score DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
