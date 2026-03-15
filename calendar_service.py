from ics import Calendar
import logging
import hashlib
import re

logger = logging.getLogger(__name__)


def _clean_title(raw_title: str) -> str:
    title = (raw_title or "Untitled Event").strip()
    title = re.sub(r"^\d{1,2}-\d{1,2}-\d{2,4}\s*:\s*", "", title)
    title = re.sub(r"\s*Due on:\s*\d{1,2}-\d{1,2}-\d{2,4}\.?\s*$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title)
    return title


def _extract_course_name(title: str, description: str) -> str:
    text_sources = [description or "", title or ""]

    # Preferred explicit labels from LMS payloads
    for text in text_sources:
        for pattern in [
            r"(?:course|subject|class)\s*[:\-]\s*([^\n\r,;]+)",
            r"\b([A-Za-z]+(?:[- ][A-Za-z]+){1,4})\b",
        ]:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            candidate = re.sub(r"\s+", " ", match.group(1)).strip(" .:-")
            if candidate and len(candidate) >= 4:
                lower = candidate.lower()
                if all(skip not in lower for skip in ["assignment", "quiz", "due", "resume", "cover letter"]):
                    return candidate

    return ""


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
        raw_title = event.name or "Untitled Event"
        title = _clean_title(raw_title)
        description = event.description or ""
        course_name = _extract_course_name(raw_title, description)

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
            "course_name": course_name,
            "description": description,
            "deadline": deadline,
            "event_type": event_type
        })

    logger.info(f"Successfully processed {len(events)} valid events.")
    return events
