import logging
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import database
from calendar_service import fetch_and_parse_calendar
from whatsapp_service import send_message
from config import TARGET_PHONE_NUMBER

logger = logging.getLogger(__name__)

def sync_calendar():
    """Fetches the latest online calendar and systematically inserts findings into the database."""
    logger.info("Executing periodic Slate calendar sync...")
    events = fetch_and_parse_calendar()
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
    """Scheduled heartbeat job to trigger automated messages based on target windows."""
    logger.info("Executing checking mechanism for deadline reminders...")
    events = database.get_pending_events()
    now = datetime.datetime.now()
    
    for event in events:
        try:
            deadline = datetime.datetime.fromisoformat(event['deadline'])
        except Exception:
            logger.warning(f"Failed to parse datetime for event deadline: {event['deadline']}. Skipping.")
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
        if 23.5 <= hours_remaining <= 24.5 and not event.get('notified_24h'):
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
    """Produces the formatted message payload."""
    date_formatted = deadline.strftime('%d %B %Y')
    time_formatted = deadline.strftime('%I:%M %p')
    
    return f"""Slate Reminder

{event['title']}

Deadline:
{date_formatted}
{time_formatted}

Due in {hours} hours."""

def start_scheduler():
    """Initializes and runs apscheduler thread to continuously loop backend systems."""
    scheduler = BackgroundScheduler()
    
    # Refresh feed from Slate portal periodically (1 hr)
    scheduler.add_job(sync_calendar, 'interval', minutes=60, id='sync_job_interval')
    
    # Process potential active deadlines frequently (30 mins)
    scheduler.add_job(check_reminders, 'interval', minutes=30, id='reminder_job_interval')
    
    scheduler.start()
    logger.info("Reminder background scheduling engine activated fully.")
    
    # Run immediate bootstraps to populate initial setup logic
    sync_calendar()
    check_reminders()
