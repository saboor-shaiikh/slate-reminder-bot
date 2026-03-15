import logging
import datetime
import os
from flask import Flask, request, jsonify

# Local module imports
import database
from telegram_service import send_message, get_file_path, download_file_content
from intent_detection import detect_intent, generate_quote
from calendar_service import process_ics_data
from bot_config import TARGET_CHAT_ID, TELEGRAM_WEBHOOK_SECRET

logger = logging.getLogger(__name__)


app = Flask(__name__)
UTC = datetime.timezone.utc
PAK_TZ = datetime.timezone(datetime.timedelta(hours=5))


def _parse_deadline(deadline):
    if isinstance(deadline, str):
        deadline = datetime.datetime.fromisoformat(deadline.replace('Z', '+00:00'))
    if not isinstance(deadline, datetime.datetime):
        return None
    if deadline.tzinfo is None:
        return deadline.replace(tzinfo=UTC)
    return deadline.astimezone(UTC)


def _can_process_chat(chat_id) -> bool:
    if chat_id is None:
        return False
    if not TARGET_CHAT_ID:
        return True
    return str(chat_id) == str(TARGET_CHAT_ID)


def _with_quote(message_text: str) -> str:
    quote = generate_quote()
    return f"{message_text}\n\n_{quote}_"

def format_event(event):
    """Helps format individual event payloads into a readable, natural structure."""
    deadline = _parse_deadline(event.get('deadline'))
    if not deadline:
        return f"{event.get('title')}\nDue: {deadline}"

    deadline_local = deadline.astimezone(PAK_TZ)

    # Calculate textual time remaining
    now = datetime.datetime.now(PAK_TZ)
    delta = deadline_local - now
    
    if delta.total_seconds() > 0:
        hours = int(delta.total_seconds() // 3600)
        days = hours // 24
        if days > 0:
            time_remaining = f"{days} days"
        else:
            time_remaining = f"{hours} hours"
    else:
        time_remaining = "Past due"
        
    course_name = (event.get('course') or "").strip()
    course_line = f"\n  Course: {course_name}" if course_name else ""
    return f"• *{event['title']}*{course_line}\n  _{deadline_local.strftime('%d %b, %I:%M %p PKT')}_ ({time_remaining})"

def handle_intent(intent_data: dict, chat_id: str):
    """Processes user intents, interfaces with database and sends appropriate replies."""
    intent = intent_data.get("intent")
    
    if intent == "next_deadline":
        events = database.get_next_deadlines()
        if events:
            rendered = "\n\n".join(format_event(e) for e in events)
            response_text = f"Next Deadline\n\n{rendered}"
        else:
            response_text = "You have no upcoming deadlines!"
            
    elif intent == "pending_assignments":
        events = database.get_pending_events()
        # Filter assignments exactly
        assignments = [e for e in events if e.get("type") == "assignment"]
        if assignments:
            rendered = "\n\n".join(format_event(e) for e in assignments)
            response_text = f"Pending Assignments\n\n{rendered}"
        else:
            response_text = "You have no pending assignments!"
            
    elif intent == "due_today":
        events = database.get_pending_events()
        now_local_date = datetime.datetime.now(PAK_TZ).date()
        today_events = []
        for e in events:
            try:
                 deadline = _parse_deadline(e.get('deadline'))
                 if deadline and deadline.astimezone(PAK_TZ).date() == now_local_date:
                     today_events.append(e)
            except Exception:
                 pass
                 
        if today_events:
            rendered = "\n\n".join(format_event(e) for e in today_events)
            response_text = f"Due Today\n\n{rendered}"
        else:
            response_text = "Nothing due today!"
            
    elif intent == "due_tomorrow":
        events = database.get_pending_events()
        tomorrow = datetime.datetime.now(PAK_TZ).date() + datetime.timedelta(days=1)
        tomorrow_events = []
        for e in events:
             try:
                 deadline = _parse_deadline(e.get('deadline'))
                 if deadline and deadline.astimezone(PAK_TZ).date() == tomorrow:
                     tomorrow_events.append(e)
             except Exception:
                 pass
                 
        if tomorrow_events:
            rendered = "\n\n".join(format_event(e) for e in tomorrow_events)
            response_text = f"Due Tomorrow\n\n{rendered}"
        else:
            response_text = "Nothing due tomorrow!"
            
    elif intent == "all_deadlines":
        events = database.get_pending_events()
        if events:
            rendered = "\n\n".join(format_event(e) for e in events)
            response_text = f"All Deadlines\n\n{rendered}"
        else:
            response_text = "You have no upcoming deadlines!"
            
    else:
        response_text = "I'm sorry, I couldn't understand that. Try asking about your next deadline, pending assignments, or what's due today/tomorrow."
        
    logger.info(f"Replying to chat {chat_id} with intent result.")
    send_message(chat_id, _with_quote(response_text))

@app.route('/telegram/webhook', methods=['GET'])
@app.route('/telegram/webhook/<secret>', methods=['GET'])
def telegram_webhook_health(secret=None):
    if TELEGRAM_WEBHOOK_SECRET and secret != TELEGRAM_WEBHOOK_SECRET:
        return "Forbidden", 403
    return jsonify({"status": "ok"}), 200

@app.route('/telegram/webhook', methods=['POST'])
@app.route('/telegram/webhook/<secret>', methods=['POST'])
def webhook_handler(secret=None):
    """Handles Telegram webhook updates for text and document messages."""
    if TELEGRAM_WEBHOOK_SECRET and secret != TELEGRAM_WEBHOOK_SECRET:
        return jsonify({"status": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    
    try:
        message = payload.get("message") or payload.get("edited_message")
        if not message:
            return jsonify({"status": "ok"}), 200

        chat_id = message.get("chat", {}).get("id")
        if not _can_process_chat(chat_id):
            logger.info(f"Ignoring message from non-target chat {chat_id}.")
            return jsonify({"status": "ok"}), 200

        # Handle documents (ICS files)
        if "document" in message:
            doc = message.get("document", {})
            filename = doc.get("file_name", "")
            if filename.lower().endswith(".ics"):
                file_id = doc.get("file_id")
                logger.info(f"Received ICS document {filename} from chat {chat_id}.")

                file_path = get_file_path(file_id)
                if file_path:
                    content = download_file_content(file_path)
                    if content:
                        try:
                            ics_text = content.decode('utf-8')
                        except UnicodeDecodeError:
                            ics_text = content.decode('latin-1', errors='replace')

                        events = process_ics_data(ics_text)
                        for event in events:
                            database.insert_event(
                                event['event_id'],
                                event['title'],
                                event['deadline'],
                                event['event_type'],
                                event.get('course_name')
                            )

                        total_events = len(events)
                        next_events = database.get_next_deadlines()
                        next_reminder_str = "None"
                        if next_events:
                            next_event = next_events[0]
                            try:
                                dt = _parse_deadline(next_event['deadline'])
                                if dt:
                                    extra = len(next_events) - 1
                                    extra_suffix = f" + {extra} more" if extra > 0 else ""
                                    next_reminder_str = f"{next_event['title']} ({dt.astimezone(PAK_TZ).strftime('%A, %I:%M %p PKT')}){extra_suffix}"
                            except Exception:
                                next_reminder_str = next_event.get('title', 'Unknown')

                        sync_msg = (
                            "System Update: Calendar Synced\n\n"
                            "Your new calendar file has been parsed and saved to the database.\n"
                            f"Total events loaded: {total_events}\n"
                            f"Next scheduled reminder: {next_reminder_str}"
                        )

                        send_message(str(chat_id), _with_quote(sync_msg))
                    else:
                        send_message(str(chat_id), _with_quote("Failed to download the calendar file."))
                else:
                    send_message(str(chat_id), _with_quote("Failed to retrieve the calendar file path."))
            else:
                send_message(str(chat_id), _with_quote("Please send a valid .ics calendar file."))

        elif "text" in message:
            text = message.get("text", "")
            logger.info(f"Received user message from chat {chat_id}.")
            intent_data = detect_intent(text)
            handle_intent(intent_data, str(chat_id))
                                
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.exception(f"Error handling webhook payload stream: {e}")
        return jsonify({"status": "error"}), 500

def start_server(port=None):
    if port is None:
        port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
