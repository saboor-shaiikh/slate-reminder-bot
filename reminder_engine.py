import logging
import datetime
import random
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
import database
from calendar_service import fetch_and_parse_calendar
from whatsapp_service import send_message
from intent_detection import generate_quote
from config import TARGET_PHONE_NUMBER, SLATE_CALENDAR_URL

logger = logging.getLogger(__name__)

# ... QUOTES list can remain as a fallback if desired, but we'll prioritize Gemini ...

def send_daily_quote():
    """Sends a dynamic inspirational quote from Gemini to keep the WhatsApp 24h window open."""
    gemini_quote = generate_quote()
    message = f"_{gemini_quote}_"
    logger.info("Sending dynamic daily active-window quote...")
    send_message(TARGET_PHONE_NUMBER, message)

def sync_calendar():
    """
    Legacy sync function. 
    Now primarily used as a manual/startup bootstrap if a URL is provided.
    """
    logger.info("Executing Slate calendar sync...")
    events = fetch_and_parse_calendar()
    # ... rest of the function ...
    new_adds = 0
    for event in events:
        database.insert_event(
            event_id=event['event_id'],
            title=event['title'],
            deadline=event['deadline'],
            event_type=event['event_type']
        )
        new_adds += 1
    logger.info(f"Processed calendar feeds. Found {new_adds} assignments/quizzes.")

def check_reminders():
    # ... existing implementation ...
    """Scheduled heartbeat job to trigger automated messages based on target windows."""
    logger.info("Executing checking mechanism for deadline reminders...")
    events = database.get_pending_events()
    now = datetime.datetime.now()
    
    for event in events:
        try:
            deadline = event['deadline']
            if isinstance(deadline, str):
                deadline = datetime.datetime.fromisoformat(deadline)
        except Exception:
            logger.warning(f"Failed to parse datetime for event deadline: {event.get('deadline')}. Skipping.")
            continue
             
        time_diff = deadline - now
        hours_remaining = time_diff.total_seconds() / 3600
        
        # Omit entirely if event is physically past
        if hours_remaining < 0:
            continue
            
        reminder_text = None
        notification_type = None
        
        # Identify whether event falls strictly into notification windows
        # Job triggers every 30m, checking a slightly broader 1H bracket guarantees capture.
        if 71.5 <= hours_remaining <= 72.5 and not event.get('notified_3d'):
            reminder_text = _format_reminder(event, 72, deadline)
            notification_type = 'notified_3d'
        elif 23.5 <= hours_remaining <= 24.5 and not event.get('notified_24h'):
            reminder_text = _format_reminder(event, 24, deadline)
            notification_type = 'notified_24h'
        elif 7.5 <= hours_remaining <= 8.5 and not event.get('notified_8h'):
            reminder_text = _format_reminder(event, 8, deadline)
            notification_type = 'notified_8h'
        elif 0.5 <= hours_remaining <= 1.5 and not event.get('notified_1h'):
            reminder_text = _format_reminder(event, 1, deadline)
            notification_type = 'notified_1h'
            
        # Send reminder if applicable and mutate DB status safely    
        if reminder_text and notification_type:
            logger.info(f"[{event['title']}] matches {notification_type} timeline. Emitting...")
            success = send_message(TARGET_PHONE_NUMBER, reminder_text)
            if success:
                database.mark_notification_sent(event['id'], notification_type)
                logger.info(f"Marked reminder sent ({notification_type}) internally for event {event['id']}.")

def _format_reminder(event, hours, deadline):
    # ... existing implementation ...
    """Produces the formatted message payload."""
    date_formatted = deadline.strftime('%d %B %Y')
    time_formatted = deadline.strftime('%I:%M %p')
    
    time_str = f"{hours} hours"
    if hours == 72:
        time_str = "3 days"
        
    return f"""Slate Reminder

{event['title']}

Deadline:
{date_formatted}
{time_formatted}

Due in {time_str}.

Calendar Link:
{SLATE_CALENDAR_URL}"""

def start_scheduler():
    """Initializes and runs apscheduler thread to continuously loop backend systems."""
    scheduler = BackgroundScheduler()
    
    # Process potential active deadlines frequently (30 mins)
    scheduler.add_job(check_reminders, 'interval', minutes=30, id='reminder_job_interval')
    
    # Daily quote to keep the 24h window open (8 AM PST)
    pst = pytz.timezone('America/Los_Angeles')
    scheduler.add_job(send_daily_quote, 'cron', hour=8, minute=0, timezone=pst, id='daily_quote_job')
    
    scheduler.start()
    logger.info("Reminder background scheduling engine activated fully.")
    
    # Run immediate bootstraps to populate initial setup logic
    check_reminders()
