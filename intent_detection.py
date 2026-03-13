import json
import logging
from google import genai
from google.genai import types
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

def detect_intent(message_text: str) -> dict:
    """
    Passes a natural language human query to the Gemini API and detects the semantic intent.
    Returns a standardized JSON dict corresponding to known commands.
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not configured.")
        return {"intent": "unknown"}
        
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
        You are an intelligent intent detection engine for a university reminder bot.
        Extract the core user intent from the following message.
        Valid intents are exclusively: "next_deadline", "pending_assignments", "due_today", "due_tomorrow", "all_deadlines".
        If the intent is not clear or doesn't match any of the valid intents, return "unknown".
        Return ONLY valid JSON format representing the intent. Do NOT add markdown blocks, formatting, or conversational text.
        
        Example outputs:
        {{"intent": "next_deadline"}}
        {{"intent": "pending_assignments"}}
        {{"intent": "due_today"}}
        
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
        logger.info(f"Intent detected for message: {message_text} -> {data.get('intent')}")
        return data
        
    except Exception as e:
        logger.error(f"Failed to detect intent properly: {e}")
        return {"intent": "error"}
