"""Zero-cost AI — tries Groq first, falls back to Google Gemini."""
import logging
import requests
from typing import Optional

from agency.config import cfg

log = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

GEMINI_MODEL = "gemini-2.0-flash-lite"


def _call_groq(messages: list, max_tokens: int) -> Optional[str]:
    try:
        r = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {cfg.groq_api_key}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        log.warning("Groq call failed: %s", e)
        return None


def _call_gemini(messages: list, max_tokens: int) -> Optional[str]:
    # Convert OpenAI-style messages to Gemini format
    contents = []
    system_text = ""
    for m in messages:
        if m["role"] == "system":
            system_text = m["content"]
        elif m["role"] == "user":
            text = (system_text + "\n\n" + m["content"]).strip() if system_text else m["content"]
            contents.append({"role": "user", "parts": [{"text": text}]})
            system_text = ""
        elif m["role"] == "assistant":
            contents.append({"role": "model", "parts": [{"text": m["content"]}]})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={cfg.gemini_api_key}"
    try:
        r = requests.post(
            url,
            json={
                "contents": contents,
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7},
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        log.warning("Gemini call failed: %s", e)
        return None


def chat(
    prompt: str,
    max_tokens: int = 500,
    system: Optional[str] = None,
) -> Optional[str]:
    """Call Groq or Gemini; return text or None if both unavailable."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    if cfg.groq_api_key:
        result = _call_groq(messages, max_tokens)
        if result:
            return result

    if cfg.gemini_api_key:
        return _call_gemini(messages, max_tokens)

    return None
