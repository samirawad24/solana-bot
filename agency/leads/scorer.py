"""Score and qualify leads based on conversion likelihood signals."""
import logging
from typing import Dict
from agency.db.models import get_leads, update_lead
from agency.config import NICHE_MAP

log = logging.getLogger(__name__)


def score_lead(lead: Dict) -> int:
    """
    Score 0-100. Higher = warmer lead.
    Signals: review count, rating gap (not too many reviews = less established),
    has website, has phone, niche automation score.
    """
    score = 0

    # Review count sweet spot: 10-100 reviews → established but not huge chain
    rc = lead.get("review_count", 0)
    if 10 <= rc <= 50:
        score += 25
    elif 51 <= rc <= 150:
        score += 15
    elif rc < 10:
        score += 10  # very small — might still convert

    # Rating — 3.5-4.3 is ideal (room for improvement = motivation to invest)
    rating = lead.get("rating", 0)
    if 3.5 <= rating <= 4.3:
        score += 20
    elif rating > 4.3:
        score += 10
    elif 3.0 <= rating < 3.5:
        score += 15  # pain point around reviews

    # Has a phone number — can be reached
    if lead.get("phone"):
        score += 15

    # Has a website — savvy enough for our tools
    if lead.get("website"):
        score += 15

    # Niche automation score bonus
    niche = NICHE_MAP.get(lead.get("niche", ""))
    if niche:
        score += niche.automation_score  # 1-10

    # City tier bonus (high-income cities close faster)
    premium_cities = {"Austin", "Nashville", "Denver", "Phoenix", "Tampa"}
    if lead.get("city", "") in premium_cities:
        score += 5

    return min(score, 100)


def qualify_leads():
    """Score all new leads and mark qualified ones ready for outreach."""
    leads = get_leads(status="new")
    promoted = 0
    for lead in leads:
        s = score_lead(lead)
        updates = {"score": s}
        if s >= 45:
            updates["status"] = "qualified"
            promoted += 1
        else:
            updates["status"] = "low_score"
        update_lead(lead["id"], updates)

    log.info("Qualified %d / %d leads", promoted, len(leads))
    return promoted
