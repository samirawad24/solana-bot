"""Lead finder — pulls local businesses via Yelp scraping (free, no API key needed)."""
import itertools
import logging

from agency.config import cfg, NICHE_MAP, NicheConfig
from agency.leads.yelp_scraper import run_yelp_discovery

log = logging.getLogger(__name__)


def discover_leads(niche_name: str, city: str) -> int:
    """Search for leads in a niche + city via Yelp, store new ones. Returns count added."""
    niche: NicheConfig = NICHE_MAP.get(niche_name)
    if not niche:
        log.warning("Unknown niche: %s", niche_name)
        return 0
    return run_yelp_discovery(niche_name, city)


def run_lead_discovery():
    """Main scheduled lead discovery run — cycles through all niches + cities."""
    from agency.config import NICHES

    pairs = list(itertools.product([n.name for n in NICHES], cfg.target_cities))
    total = 0
    for niche_name, city in pairs[:5]:  # 5 pairs per run stays polite
        total += discover_leads(niche_name, city)
    log.info("Lead discovery complete. Total new leads this run: %d", total)
    return total
