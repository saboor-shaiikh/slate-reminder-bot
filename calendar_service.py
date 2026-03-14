import requests
from urllib.parse import quote_plus
from ics import Calendar
import logging
from config import SLATE_CALENDAR_URL, CF_CLEARANCE, CF_USER_AGENT, SCRAPE_DO_TOKEN

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers — each returns a requests.Response or raises an exception
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_direct() -> requests.Response:
    """Strategy 1: Direct requests using the stored cf_clearance cookie."""
    headers = {"User-Agent": CF_USER_AGENT}
    cookies = {"cf_clearance": CF_CLEARANCE} if CF_CLEARANCE else {}
    response = requests.get(SLATE_CALENDAR_URL, headers=headers, cookies=cookies, timeout=15)
    if response.status_code == 403:
        raise PermissionError("Cloudflare blocked direct request (403).")
    response.raise_for_status()
    return response

def _fetch_via_scrape_do() -> requests.Response:
    """Strategy 2: Route through Scrape.do residential proxy — bypasses Cloudflare."""
    if not SCRAPE_DO_TOKEN:
        raise ValueError("SCRAPE_DO_TOKEN is not configured.")
    encoded_url = quote_plus(SLATE_CALENDAR_URL)
    proxy_url = f"https://api.scrape.do/?token={SCRAPE_DO_TOKEN}&url={encoded_url}&super=true"
    response = requests.get(proxy_url, timeout=30)
    if response.status_code == 403:
        raise PermissionError("Scrape.do request was also blocked (403).")
    response.raise_for_status()
    return response

# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def fetch_and_parse_calendar():
    """
    Downloads the ICS calendar feed from Slate, parses all events,
    detects assignments vs quizzes and returns structured event objects.

    Uses a 2-strategy cascade to maximise reliability:
      1. Direct requests + cf_clearance cookie (lightweight, fast)
      2. Scrape.do residential proxy (Cloudflare bypass, used only when needed)
    """
    if not SLATE_CALENDAR_URL:
        logger.error("SLATE_CALENDAR_URL is not configured.")
        return []

    raw_text = None

    # --- Strategy 1: Direct with cookie ---
    try:
        logger.info("Attempting direct calendar fetch (Strategy 1)...")
        response = _fetch_direct()
        raw_text = response.text
        logger.info("Strategy 1 succeeded.")
    except Exception as e:
        logger.warning(f"Strategy 1 failed: {e}. Falling back to Scrape.do (Strategy 2)...")

    # --- Strategy 2: Scrape.do fallback ---
    if raw_text is None:
        try:
            response = _fetch_via_scrape_do()
            raw_text = response.text
            logger.info("Strategy 2 (Scrape.do) succeeded.")
        except Exception as e:
            logger.error(f"Strategy 2 also failed: {e}. Calendar sync aborted.")
            return []

        
    try:
        # Load the whole ICS file into Calendar parser 
        c = Calendar(raw_text)
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
