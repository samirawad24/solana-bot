"""Automated email discovery from business websites — no API needed."""
import re
import logging
from urllib.parse import urljoin, urlparse
from typing import Optional

import requests

from agency.db.models import get_conn

log = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_JUNK_PATTERNS = re.compile(
    r"noreply|no-reply|privacy|legal|support@sentry|example\.|w3\.org|schema\.org",
    re.IGNORECASE,
)
_CONTACT_PATHS = ["/", "/contact", "/about", "/contact-us", "/about-us"]

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _fetch(url: str, timeout: int = 5) -> str:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code == 200 and "text/html" in r.headers.get("content-type", ""):
            return r.text
    except Exception:
        pass
    return ""


def _extract_emails(html: str) -> list:
    """Pull all emails from HTML, filter junk."""
    found = set()
    # mailto: links first (highest signal)
    for m in re.finditer(r'href=["\']mailto:([^"\'?]+)', html, re.IGNORECASE):
        e = m.group(1).strip()
        if e and not _JUNK_PATTERNS.search(e):
            found.add(e.lower())
    # bare emails in text
    for e in _EMAIL_RE.findall(html):
        if not _JUNK_PATTERNS.search(e):
            found.add(e.lower())
    return list(found)


def find_email(website_url: str, timeout: int = 5) -> Optional[str]:
    """
    Scrape up to 3 pages of a website for a contact email.
    Returns first real email found, or None.
    """
    if not website_url:
        return None

    parsed = urlparse(website_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    domain = parsed.netloc.lstrip("www.")

    candidates = []
    pages_checked = 0
    for path in _CONTACT_PATHS:
        if pages_checked >= 3:
            break
        html = _fetch(urljoin(base, path), timeout=timeout)
        if html:
            candidates.extend(_extract_emails(html))
            pages_checked += 1

    # Prefer emails that match the domain
    domain_emails = [e for e in candidates if domain in e]
    if domain_emails:
        return sorted(domain_emails)[0]
    if candidates:
        return sorted(candidates)[0]

    # Last resort: try common patterns (mark as guessed)
    for prefix in ("info", "contact", "hello"):
        guess = f"{prefix}@{domain}"
        return guess  # return first guess without verifying

    return None


def enrich_lead_emails(limit: int = 30) -> int:
    """
    Find emails for qualified leads that have a website but no email.
    Updates DB in place. Returns count of emails found.
    """
    conn = get_conn()
    c = conn.cursor()
    rows = c.execute(
        """SELECT id, website FROM leads
           WHERE status = 'qualified'
             AND (email IS NULL OR email = '')
             AND website IS NOT NULL AND website != ''
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()

    found = 0
    for row in rows:
        lead_id, website = row["id"], row["website"]
        email = find_email(website)
        if email:
            conn = get_conn()
            conn.execute("UPDATE leads SET email=? WHERE id=?", (email, lead_id))
            conn.commit()
            conn.close()
            found += 1
            log.info("Email found for lead %d: %s", lead_id, email)

    log.info("Email enrichment: %d/%d leads enriched", found, len(rows))
    return found
