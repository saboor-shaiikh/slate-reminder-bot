import requests
from ics import Calendar
import logging
from config import SLATE_CALENDAR_URL

logger = logging.getLogger(__name__)

def fetch_and_parse_calendar():
    """
    Downloads the ICS calendar feed from Slate, parses all events,
    detects assignments vs quizzes and returns structured event objects.
    """
    if not SLATE_CALENDAR_URL:
        logger.error("SLATE_CALENDAR_URL is not configured.")
        return []
        
    try:
        logger.info(f"Fetching calendar feed from {SLATE_CALENDAR_URL}")
        response = requests.get(SLATE_CALENDAR_URL)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch calendar from Slate HTTP API: {e}")
        return []
        
    try:
        # Load the whole ICS file into Calendar parser 
        c = Calendar(response.text)
    except Exception as e:
        logger.error(f"Failed to parse ICS calendar content: {e}")
        return []
        
    events = []
    
    # Process each event within the ICS feed
    for event in c.events:
        event_id = event.uid or str(hash(event.name + str(event.begin)))
        title = event.name or "Untitled Event"
        description = event.description or ""
        
        deadline = None
        if event.begin:
            try:
                # Parse depending on the version of `ics` (returns arrow object which has native datetime)
                deadline = event.begin.datetime
            except AttributeError:
                deadline = event.begin
                
        if not deadline:
            continue
            
        # Basic keyword check to demarcate quiz format vs normal assignment format
        event_type = "assignment"
        title_lower = title.lower()
        if "quiz" in title_lower or "test" in title_lower or "exam" in title_lower:
            event_type = "quiz"
            
        events.append({
            "event_id": event_id,
            "title": title,
            "description": description,
            "deadline": deadline,
            "event_type": event_type
        })
        
    logger.info(f"Successfully processed {len(events)} valid events from the calendar.")
    return events
