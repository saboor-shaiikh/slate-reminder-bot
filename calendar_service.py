from ics import Calendar
import logging

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
        event_id = event.uid or str(hash(event.name + str(event.begin)))
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
        if "quiz" in title_lower or "test" in title_lower or "exam" in title_lower:
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
