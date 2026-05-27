"""Lead finder — pulls local businesses via Google Places API (or mock data in demo mode)."""
import os
import time
import requests
import logging
from typing import List, Dict

from agency.config import cfg, NICHE_MAP, NicheConfig
from agency.db.models import insert_lead, get_leads

log = logging.getLogger(__name__)

PLACES_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAIL_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def _places_search(query: str, location: str) -> List[Dict]:
    if not cfg.google_places_api_key:
        return _mock_leads(query, location)

    results = []
    params = {
        "query": f"{query} in {location}",
        "key": cfg.google_places_api_key,
    }
    while True:
        r = requests.get(PLACES_URL, params=params, timeout=10)
        data = r.json()
        results.extend(data.get("results", []))
        token = data.get("next_page_token")
        if not token or len(results) >= cfg.leads_per_run:
            break
        params["pagetoken"] = token
        time.sleep(2)
    return results[:cfg.leads_per_run]


def _get_place_details(place_id: str) -> Dict:
    if not cfg.google_places_api_key:
        return {}
    params = {
        "place_id": place_id,
        "fields": "name,formatted_phone_number,website,formatted_address",
        "key": cfg.google_places_api_key,
    }
    r = requests.get(PLACES_DETAIL_URL, params=params, timeout=10)
    return r.json().get("result", {})


def _mock_leads(query: str, location: str) -> List[Dict]:
    """Return plausible demo leads when no API key is configured."""
    templates = [
        {"name": f"Elite {query.title()} - {location}", "rating": 4.2, "user_ratings_total": 47},
        {"name": f"Premier {query.title()} Solutions", "rating": 3.8, "user_ratings_total": 22},
        {"name": f"Downtown {query.title()} {location}", "rating": 4.5, "user_ratings_total": 103},
        {"name": f"{location} {query.title()} Pros", "rating": 4.0, "user_ratings_total": 31},
        {"name": f"Luxury {query.title()} Studio", "rating": 4.7, "user_ratings_total": 156},
    ]
    return templates


def discover_leads(niche_name: str, city: str) -> int:
    """Search for leads in a niche + city, store new ones. Returns count added."""
    niche: NicheConfig = NICHE_MAP.get(niche_name)
    if not niche:
        log.warning("Unknown niche: %s", niche_name)
        return 0

    added = 0
    for term in niche.search_terms[:2]:  # 2 terms per niche per run to stay polite
        raw = _places_search(term, city)
        for item in raw:
            details = {}
            pid = item.get("place_id")
            if pid:
                details = _get_place_details(pid)

            name = item.get("name") or details.get("name", "Unknown")
            phone = details.get("formatted_phone_number", "")
            website = details.get("website", "")
            address = details.get("formatted_address", "")
            parts = address.split(",")
            state = parts[-2].strip().split(" ")[0] if len(parts) >= 2 else ""

            lead = {
                "business_name": name,
                "niche": niche_name,
                "city": city.split(" ")[0],
                "state": state,
                "phone": phone,
                "website": website,
                "rating": item.get("rating", 0),
                "review_count": item.get("user_ratings_total", 0),
                "status": "new",
                "source": "google_places",
            }
            lid = insert_lead(lead)
            if lid:
                added += 1
        time.sleep(1)

    log.info("Discovered %d new leads for %s in %s", added, niche_name, city)
    return added


def run_lead_discovery():
    """Main scheduled lead discovery run — cycles through all niches + cities."""
    from agency.config import NICHES
    import itertools

    pairs = list(itertools.product([n.name for n in NICHES], cfg.target_cities))
    # rotate each run so we don't always hit same niche/city first
    total = 0
    for niche_name, city in pairs[:5]:  # 5 pairs per run keeps API costs low
        total += discover_leads(niche_name, city)
    log.info("Lead discovery complete. Total new leads this run: %d", total)
    return total
