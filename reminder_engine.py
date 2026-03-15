import logging
import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
import database
from telegram_service import send_message
from intent_detection import generate_quote
from bot_config import TARGET_CHAT_ID

logger = logging.getLogger(__name__)
UTC = datetime.timezone.utc
LOCAL_TZ = pytz.timezone('America/Los_Angeles')
_scheduler = None


def _to_utc_datetime(value):
    if isinstance(value, str):
        value = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if not isinstance(value, datetime.datetime):
        raise ValueError("deadline is not a datetime")
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _with_quote(message_text: str) -> str:
    quote = generate_quote()
    return f"{message_text}\n\nQuote: {quote}"


def send_daily_quote():
    """Sends a daily motivational quote via Telegram."""
    if not TARGET_CHAT_ID:
        logger.warning("TARGET_CHAT_ID missing. Skipping daily quote send.")
        return

    gemini_quote = generate_quote()
    message = f"_{gemini_quote}_"
    logger.info("Sending dynamic daily active-window quote...")
    send_message(TARGET_CHAT_ID, message)


def check_reminders():
    """Scheduled heartbeat job to trigger automated messages based on target windows."""
    if not TARGET_CHAT_ID:
        logger.warning("TARGET_CHAT_ID missing. Skipping reminder check run.")
        return

    logger.info("Executing checking mechanism for deadline reminders...")
    events = database.get_pending_events()
    now = datetime.datetime.now(UTC)

    for event in events:
        try:
            deadline = _to_utc_datetime(event['deadline'])
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
            success = send_message(TARGET_CHAT_ID, _with_quote(reminder_text))
            if success:
                database.mark_notification_sent(event['id'], notification_type)
                logger.info(f"Marked reminder sent ({notification_type}) internally for event {event['id']}.")


def _format_reminder(event, hours, deadline):
    """Produces the formatted message payload."""
    deadline_local = deadline.astimezone(LOCAL_TZ)
    date_formatted = deadline_local.strftime('%d %B %Y')
    time_formatted = deadline_local.strftime('%I:%M %p %Z')

    time_str = f"{hours} hours"
    if hours == 72:
        time_str = "3 days"

    return f"""⏰ *Slate Reminder*

📝 {event['title']}

📅 Deadline:
{date_formatted}
{time_formatted}

⏳ Due in {time_str}."""


def start_scheduler():
    """Initializes and runs apscheduler thread to continuously loop backend systems."""
    global _scheduler
    if _scheduler and _scheduler.running:
        logger.info("Scheduler already running. Skipping duplicate start.")
        return

    scheduler = BackgroundScheduler()

    # Process potential active deadlines frequently (30 mins)
    scheduler.add_job(check_reminders, 'interval', minutes=30, id='reminder_job_interval')

    # Daily quote to keep the 24h window open (8 AM PST)
    pst = pytz.timezone('America/Los_Angeles')
    scheduler.add_job(send_daily_quote, 'cron', hour=8, minute=0, timezone=pst, id='daily_quote_job')

    scheduler.start()
    _scheduler = scheduler
    logger.info("Reminder background scheduling engine activated fully.")

    # Run immediate bootstrap in a separate thread to avoid blocking server start
    import threading
    threading.Thread(target=check_reminders, daemon=True).start()
