"""Zero-cost AI via Groq's free API (14,400 req/day, no credit card required)."""
import logging
import requests
from typing import Optional

from agency.config import cfg

log = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"


def chat(
    prompt: str,
    max_tokens: int = 500,
    system: Optional[str] = None,
) -> Optional[str]:
    """Call Groq; return text or None if key not set / request fails."""
    if not cfg.groq_api_key:
        return None

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        r = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {cfg.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7,
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        log.warning("Groq API call failed: %s", e)
        return None
