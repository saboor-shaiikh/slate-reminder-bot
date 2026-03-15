from ics import Calendar
import logging
import hashlib

logger = logging.getLogger(__name__)


def process_ics_data(raw_text: str):
    """
    Parses ICS content into structured event objects.
    """
    try:
        c = Calendar(raw_text)
    except Exception as e:
        logger.error(f"Failed to parse ICS calendar content: {e}")
        return []

    events = []

    for event in c.events:
        fallback_key = f"{event.name}|{event.begin}|{event.end}|{event.description}"
        event_id = event.uid or hashlib.sha256(fallback_key.encode('utf-8')).hexdigest()
        title = event.name or "Untitled Event"
        description = event.description or ""

        deadline = None
        if event.begin:
            try:
                deadline = event.begin.datetime
            except AttributeError:
                deadline = event.begin

        if not deadline:
            continue

        # Basic keyword check to demarcate quiz format vs normal assignment format
        event_type = "assignment"
        title_lower = title.lower()
        if any(word in title_lower for word in ["quiz", "test", "exam", "midterm", "final"]):
            event_type = "quiz"

        events.append({
            "event_id": event_id,
            "title": title,
            "description": description,
            "deadline": deadline,
            "event_type": event_type
        })

    logger.info(f"Successfully processed {len(events)} valid events.")
    return events
