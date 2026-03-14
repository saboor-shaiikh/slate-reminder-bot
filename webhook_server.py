import logging
import datetime
from flask import Flask, request, jsonify
from whatsapp_service import send_message
from intent_detection import detect_intent
import database
from reminder_engine import start_scheduler

logger = logging.getLogger(__name__)


app = Flask(__name__)

# Initialize database and background schedulers on startup
database.initialize_database()
start_scheduler()

def format_event(event):
    """Helps format individual event payloads into a readable, natural structure."""
    deadline_str = event['deadline']
    try:
        deadline = datetime.datetime.fromisoformat(deadline_str)
    except Exception:
        # Fallback if unparsable
        return f"{event['title']}\nDue: {deadline_str}"
        
    # Calculate textual time remaining
    now = datetime.datetime.now()
    delta = deadline - now
    
    if delta.total_seconds() > 0:
        hours = int(delta.total_seconds() // 3600)
        days = hours // 24
        if days > 0:
            time_remaining = f"{days} days"
        else:
            time_remaining = f"{hours} hours"
    else:
        time_remaining = "Past due"
        
    return f"""
{event['title']}
Due: {deadline.strftime('%d %B %Y')}
Time Remaining: {time_remaining}
""".strip()

def handle_intent(intent_data: dict, phone_number: str):
    """Processes user intents, interfaces with database and sends appropriate replies."""
    intent = intent_data.get("intent")
    
    if intent == "next_deadline":
        event = database.get_next_deadline()
        if event:
            response_text = f"Next Deadline\n\n{format_event(event)}"
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
        now = datetime.datetime.now()
        today_events = []
        for e in events:
            try:
                 if datetime.datetime.fromisoformat(e['deadline']).date() == now.date():
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
        tomorrow = datetime.datetime.now().date() + datetime.timedelta(days=1)
        tomorrow_events = []
        for e in events:
             try:
                 if datetime.datetime.fromisoformat(e['deadline']).date() == tomorrow:
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
        
    logger.info(f"Replying to {phone_number} with intent result.")
    send_message(phone_number, response_text)

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Handles webhook verification challenges from Meta API."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    # Usually one validates hub.verify_token matches your preset config
    if mode and challenge:
        if mode == "subscribe":
            return challenge, 200
            
    return "Forbidden", 403

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Listens to real-time events posted by WhatsApp / Meta API."""
    payload = request.get_json()
    
    try:
        # Verify it's coming from WA Cloud Account APIs
        if "object" in payload and payload["object"] == "whatsapp_business_account":
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    # Is this a new message event?
                    if "messages" in value:
                        for message in value["messages"]:
                            sender_number = message.get("from")
                            
                            # Only parse explicit standard texts
                            if message.get("type") == "text":
                                text = message.get("text", {}).get("body", "")
                                logger.info(f"Received user message from {sender_number}.")
                                
                                # Gemini evaluates meaning
                                intent_data = detect_intent(text)
                                
                                # Backend formulates reply and sends directly
                                handle_intent(intent_data, sender_number)
                                
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"Error handling webhook payload stream: {e}")
        return jsonify({"status": "error"}), 500

def start_server(port=None):
    import os
    if port is None:
        port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
