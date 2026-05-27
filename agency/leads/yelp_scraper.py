"""Free Yelp business scraper — no API key needed."""
import time
import logging
import re
from typing import List, Dict
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from agency.config import cfg, NICHE_MAP
from agency.db.models import insert_lead

log = logging.getLogger(__name__)

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]
_ua_index = 0


def _headers() -> Dict:
    global _ua_index
    ua = _USER_AGENTS[_ua_index % len(_USER_AGENTS)]
    _ua_index += 1
    return {
        "User-Agent": ua,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def _parse_rating(text: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)", text or "")
    return float(m.group(1)) if m else 0.0


def _parse_review_count(text: str) -> int:
    m = re.search(r"(\d[\d,]*)", text or "")
    return int(m.group(1).replace(",", "")) if m else 0


def scrape_yelp(term: str, location: str, limit: int = 20) -> List[Dict]:
    """Scrape Yelp search results. Returns list of business dicts."""
    results = []
    page = 0
    per_page = 10

    while len(results) < limit:
        url = (
            f"https://www.yelp.com/search"
            f"?find_desc={quote_plus(term)}"
            f"&find_loc={quote_plus(location)}"
            f"&start={page * per_page}"
        )
        try:
            resp = requests.get(url, headers=_headers(), timeout=15)
            if resp.status_code == 429:
                log.warning("Yelp rate-limited; stopping this batch")
                break
            if resp.status_code != 200:
                log.warning("Yelp returned %d for %s", resp.status_code, url)
                break

            soup = BeautifulSoup(resp.text, "lxml")

            # Yelp renders business cards in <li> tags with data-testid or aria-label
            cards = soup.select('li.y-css-29kerx, li[class*="regular-search-result"]')
            if not cards:
                # Fallback: look for any li containing a business name heading
                cards = [li for li in soup.find_all("li") if li.find("h3") or li.find("h4")]

            if not cards:
                log.info("No cards found on page %d — stopping", page)
                break

            for card in cards:
                name_tag = card.find("h3") or card.find("h4") or card.find("a", attrs={"name": True})
                if not name_tag:
                    continue
                name = name_tag.get_text(strip=True)
                if not name or len(name) < 3:
                    continue

                # Rating
                rating_tag = card.find(attrs={"aria-label": re.compile(r"star rating", re.I)})
                rating_text = rating_tag.get("aria-label", "") if rating_tag else ""
                rating = _parse_rating(rating_text)

                # Review count
                review_tag = card.find(string=re.compile(r"\d[\d,]* review", re.I))
                review_count = _parse_review_count(review_tag) if review_tag else 0

                # Phone
                phone_tag = card.find(string=re.compile(r"\(\d{3}\)\s*\d{3}-\d{4}"))
                phone = phone_tag.strip() if phone_tag else ""

                # Address
                addr_tag = card.find("address")
                address = addr_tag.get_text(strip=True) if addr_tag else ""

                # Website (look for external link)
                website = ""
                for a in card.find_all("a", href=True):
                    href = a["href"]
                    if "biz_redir" in href or "redirect_url" in href:
                        m = re.search(r"url=([^&]+)", href)
                        if m:
                            from urllib.parse import unquote
                            website = unquote(m.group(1))
                            break

                results.append({
                    "name": name,
                    "rating": rating,
                    "review_count": review_count,
                    "phone": phone,
                    "address": address,
                    "website": website,
                    "yelp_url": url,
                })

                if len(results) >= limit:
                    break

        except Exception as e:
            log.warning("Yelp scrape error (page %d): %s", page, e)
            break

        page += 1
        time.sleep(2)

    log.info("Yelp scraped %d businesses for '%s' in %s", len(results), term, location)
    return results


def run_yelp_discovery(niche_name: str, city: str) -> int:
    """Scrape Yelp for a niche+city and insert new leads. Returns count added."""
    niche = NICHE_MAP.get(niche_name)
    if not niche:
        log.warning("Unknown niche: %s", niche_name)
        return 0

    added = 0
    for term in niche.search_terms[:2]:
        businesses = scrape_yelp(term, city, limit=cfg.leads_per_run)
        for biz in businesses:
            city_part = city.split(" ")[0]
            parts = (biz.get("address") or "").split(",")
            state = ""
            if len(parts) >= 2:
                state_city = parts[-2].strip().split(" ")
                state = state_city[0] if state_city else ""

            lead = {
                "business_name": biz["name"],
                "niche": niche_name,
                "city": city_part,
                "state": state,
                "phone": biz.get("phone", ""),
                "website": biz.get("website", ""),
                "rating": biz.get("rating", 0),
                "review_count": biz.get("review_count", 0),
                "status": "new",
                "source": "yelp",
            }
            lid = insert_lead(lead)
            if lid:
                added += 1

        time.sleep(1)

    log.info("Yelp discovery: %d new leads for %s in %s", added, niche_name, city)
    return added
