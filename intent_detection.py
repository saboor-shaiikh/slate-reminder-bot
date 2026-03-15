import json
import logging
from google import genai
from bot_config import GEMINI_API_KEY

logger = logging.getLogger(__name__)
VALID_INTENTS = {
    "next_deadline",
    "pending_assignments",
    "due_today",
    "due_tomorrow",
    "all_deadlines",
    "unknown",
}


def _rule_based_intent(message_text: str) -> dict:
    text = (message_text or "").strip().lower()

    if any(token in text for token in ["tomorrow", "due tomorrow"]):
        return {"intent": "due_tomorrow"}
    if any(token in text for token in ["today", "due today"]):
        return {"intent": "due_today"}
    if any(token in text for token in ["assignment", "assignments", "pending"]):
        return {"intent": "pending_assignments"}
    if any(token in text for token in ["all", "everything", "list", "deadlines"]):
        return {"intent": "all_deadlines"}
    if any(token in text for token in ["next", "closest", "soonest"]):
        return {"intent": "next_deadline"}

    return {"intent": "unknown"}


def _normalize_intent_payload(payload: dict, original_message: str) -> dict:
    intent = payload.get("intent") if isinstance(payload, dict) else None
    if intent in VALID_INTENTS:
        return {"intent": intent}
    return _rule_based_intent(original_message)

def detect_intent(message_text: str) -> dict:
    """
    Passes a natural language human query to the Gemini API and detects the semantic intent.
    Returns a standardized JSON dict corresponding to known commands.
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not configured.")
        return _rule_based_intent(message_text)
        
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
        You are an intelligent intent detection engine for a university reminder bot.
        Extract the core user intent from the following message.
        Valid intents are exclusively: "next_deadline", "pending_assignments", "due_today", "due_tomorrow", "all_deadlines".
        If the intent is not clear or doesn't match any of the valid intents, return "unknown".
        Return ONLY valid JSON format representing the intent. Do NOT add markdown blocks, formatting, or conversational text.
        
        Example outputs:
        {{"intent": "next_deadline"}} (User says: "what's next?", "next deadline?")
        {{"intent": "pending_assignments"}} (User says: "any assignments left?", "pending tasks")
        {{"intent": "due_today"}} (User says: "what's due today?", "today's schedule")
        {{"intent": "all_deadlines"}} (User says: "show all events", "list everything", "what are my deadlines?")
        
        User message: "{message_text}"
        """
        
        # Use simple gemini completion 
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        
        response_text = response.text.strip()
        
        # Clean markdown wrappers occasionally outputted by the model
        if response_text.startswith("```json"):
            response_text = response_text[7:].strip()
        elif response_text.startswith("```"):
            response_text = response_text[3:].strip()
            
        if response_text.endswith("```"):
            response_text = response_text[:-3].strip()
            
        data = json.loads(response_text)
        normalized = _normalize_intent_payload(data, message_text)
        logger.info(f"Intent detected for message: {message_text} -> {normalized.get('intent')}")
        return normalized
        
    except Exception as e:
        logger.error(f"Failed to detect intent properly: {e}")
        return _rule_based_intent(message_text)


def generate_quote() -> str:
    """
    Generates a unique, hardcore, gangster-style motivational quote using Gemini.
    Returns only the quote text.
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY for quote generation not configured.")
        return "Keep grinding. Success is the only option."
        
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        system_prompt = "Generate one unique, hardcore, gangster-style motivational quote about hustling, grinding, or success. It should be gritty but inspiring. Do not use quotes that promote actual violence. Return ONLY the quote text itself, without any introductory words, quotation marks, or extra formatting. I will handle the formatting."
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=system_prompt,
        )
        
        quote = response.text.strip().replace('"', '').replace('“', '').replace('”', '')
        return quote
        
    except Exception as e:
        logger.error(f"Failed to generate dynamic quote: {e}")
        return "The hustle never sleeps. Stay focused on the prize."
