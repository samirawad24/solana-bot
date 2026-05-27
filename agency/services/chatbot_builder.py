"""
AI Chatbot Builder — generates a ready-to-deploy chatbot configuration
and embeddable script for a client's website.
"""
import logging
from typing import Dict

from agency.ai.groq_client import chat
from agency.config import cfg, NICHE_MAP, PACKAGES
from agency.db.models import log_service_delivery

log = logging.getLogger(__name__)


def generate_chatbot_config(client: Dict) -> Dict:
    """Build a complete chatbot configuration. Returns dict with config + embed snippet."""
    niche_name = client.get("niche", "local business")
    business_name = client.get("business_name", "Your Business")
    niche = NICHE_MAP.get(niche_name)
    pain_points = niche.pain_points if niche else []

    prompt = f"""You are an expert chatbot designer. Create a complete chatbot configuration for:

Business: {business_name}
Type: {niche_name.replace('_', ' ')}
Key pain points we're solving: {', '.join(pain_points[:2])}

Generate:

1. FAQ_PAIRS (10 Q&A pairs the chatbot should handle — specific to this niche)
   Format: Q: ... / A: ...

2. BOOKING_FLOW (step-by-step conversational booking script, 5-7 steps)
   Format: STEP N: [bot message] → [user options/input]

3. HANDOFF_MESSAGE (what the bot says when escalating to a human)

4. WELCOME_MESSAGE (opening message when chat widget loads)

5. OFFLINE_MESSAGE (what to show outside business hours)

Keep all messages warm, concise, professional. Use the business name {business_name}."""

    raw = chat(prompt, max_tokens=2000)
    if not raw:
        return _demo_config(business_name, niche_name)

    embed_snippet = f"""<!-- {business_name} AI Chat Widget -->
<script>
  window.chatbotConfig = {{
    businessName: "{business_name}",
    welcomeMessage: "Hi! How can we help you today?",
    primaryColor: "#0066CC",
    position: "bottom-right",
    agentName: "{business_name} Assistant"
  }};
</script>
<script src="https://cdn.botpress.cloud/webchat/v2/inject.js" async></script>"""

    return {
        "raw_config": raw,
        "embed_snippet": embed_snippet,
        "business_name": business_name,
        "niche": niche_name,
    }


def _demo_config(business_name: str, niche: str) -> Dict:
    return {
        "raw_config": f"""FAQ_PAIRS for {business_name}:
Q: What are your hours? / A: We're open Monday-Friday 9am-6pm and Saturday 10am-4pm.
Q: How do I book an appointment? / A: You can book directly through this chat or call us!
Q: What services do you offer? / A: We offer a full range of {niche.replace('_',' ')} services.
Q: Do you accept insurance? / A: Please chat with us and we'll verify your coverage.
Q: Where are you located? / A: Click here for our address and directions.

BOOKING_FLOW:
STEP 1: "What service are you looking for today?" → [List top services]
STEP 2: "What date works best for you?" → [Date picker]
STEP 3: "Morning or afternoon?" → [Morning / Afternoon]
STEP 4: "Your name?" → [Text input]
STEP 5: "Best phone number?" → [Phone input]
STEP 6: "Confirming your appointment — we'll send a reminder the day before!"

HANDOFF_MESSAGE: "Let me connect you with our team right now! Please hold for just a moment."
WELCOME_MESSAGE: "Hi! Welcome to {business_name}. How can I help you today?"
OFFLINE_MESSAGE: "We're currently closed but leave your info and we'll reach out first thing tomorrow!"
""",
        "embed_snippet": f'<script src="https://widget.example.com/chat.js" data-business="{business_name}"></script>',
        "business_name": business_name,
        "niche": niche,
    }


def deliver_chatbot_service(client: Dict) -> bool:
    """Generate + log chatbot delivery for a client."""
    try:
        config = generate_chatbot_config(client)
        content = (
            f"CHATBOT CONFIGURATION FOR {client['business_name'].upper()}\n"
            f"{'='*60}\n\n"
            f"{config['raw_config']}\n\n"
            f"EMBED SNIPPET\n{'='*60}\n"
            f"{config['embed_snippet']}\n"
        )
        log_service_delivery(
            client["id"],
            "chatbot",
            f"AI Chatbot Config — {client['business_name']}",
            content,
        )
        log.info("Chatbot service delivered for client %s", client["business_name"])
        return True
    except Exception as e:
        log.error("Chatbot delivery failed for %s: %s", client.get("business_name"), e)
        return False
