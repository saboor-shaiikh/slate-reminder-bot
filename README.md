# Slate Reminder Bot

Owner: Abdul Saboor

Slate Reminder Bot is a Telegram assistant for students who want deadline reminders from their University Of Lahore's LMS calendar.

You send the bot an `.ics` file, it stores events in Supabase Postgres, and then keeps reminding you before each deadline.

## What It Does

- Accepts `.ics` files in Telegram chat
- Extracts events and saves them to PostgreSQL (Supabase)
- Extracts and displays course names when available (for example: `Machine Learning`)
- Answers deadline questions in Telegram
- Returns all tied events for `next deadline` when two or more deadlines are at the same time
- Sends automatic reminders at:
  - 72 hours before deadline
  - 24 hours before deadline
  - 8 hours before deadline
  - 1 hour before deadline
- Sends scheduled quote messages in PKT:
   - 7:00 PM PKT: `Good morning` 
   - 11:00 PM PKT: `Good night`
- Appends a random quote under bot replies and reminder messages
- Uses Pakistan time (PKT) for reminder tracking and user-visible deadline formatting

## Supported Chat Queries

You can ask things like:

- next deadline
- pending assignments
- due today
- due tomorrow
- all deadlines

## Message Templates

These are the message formats used by the bot.

1. All Deadlines response

```text
All Deadlines

• *Assignment 2*
   Course: Machine Learning
   _19 Apr, 07:00 PM PKT_ (35 days)

• *Quiz 1*
   Course: Artificial Intelligence
   _17 Mar, 06:59 PM PKT_ (2 days)

_Stay focused and keep moving._
```

2. Next Deadline response (tied events supported)

```text
Next Deadline

• *Assignment 1*
   Course: Machine Learning
   _17 Mar, 06:59 PM PKT_ (2 days)

• *Quiz 1*
   Course: Machine Learning
   _17 Mar, 06:59 PM PKT_ (2 days)

_One step at a time. You are building momentum._
```

3. Scheduled reminder

```text
⏰ *Slate Reminder*

📝 Assignment 2

📅 Deadline:
19 April 2026
07:00 PM PKT

⏳ Due in 24 hours

_Discipline beats motivation. Show up anyway._
```

4. ICS sync confirmation

```text
System Update: Calendar Synced

Your new calendar file has been parsed and saved to the database.
Total events loaded: 12
Next scheduled reminder: Assignment 1 (Monday, 06:59 PM PKT) + 1 more

_Consistency today creates freedom tomorrow._
```

## Tech Stack

- Python 3
- Flask (webhook server)
- APScheduler (background jobs)
- Supabase Postgres
- Telegram Bot API
- Gemini API (intent + quote generation)

## Project Structure

- `main.py`: starts DB init, scheduler, and Flask server
- `webhook_server.py`: Telegram webhook endpoint and message handling
- `telegram_service.py`: Telegram API calls (send message, file handling)
- `calendar_service.py`: `.ics` parsing
- `database.py`: database access and schema setup
- `reminder_engine.py`: reminder scheduling and delivery
- `intent_detection.py`: intent detection and quote generation
- `pre_deploy_check.py`: local checks for DB and Telegram config
- `set_telegram_webhook.py`: helper to register webhook URL with Telegram

## Environment Variables

Create a `.env` file in project root:

- `GEMINI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TARGET_CHAT_ID`
- `DATABASE_URL`

Optional:

- `TELEGRAM_WEBHOOK_SECRET`

## Local Setup

1. Create virtual environment:

   `py -3 -m venv .venv`

2. Install dependencies:

   `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`

3. Run pre-check:

   `.\.venv\Scripts\python.exe pre_deploy_check.py`

4. Start the app:

   `.\.venv\Scripts\python.exe main.py`

## Render Deployment

1. Push code to GitHub.
2. Create a Render Web Service connected to this repo.
3. Set build command:

   `pip install -r requirements.txt`

4. Set start command:

   `python main.py`

5. Add environment variables in Render dashboard.

## Telegram Webhook Setup

After deploy, set webhook to your Render URL:

`.\.venv\Scripts\python.exe set_telegram_webhook.py --base-url https://slate-reminder-bot.onrender.com`

If your local network blocks `api.telegram.org`, run the same command from a network where Telegram API is reachable.

## First Run Checklist

1. Send `/start` or any text to your bot in Telegram.
2. Send your `.ics` calendar file.
3. Confirm you receive sync summary.
4. Ask:
   - next deadline
   - due today
   - due tomorrow

## Notes

- Deadlines are stored as timezone-aware timestamps in Postgres.
- If an event deadline changes, reminder flags are reset for that event.
- This project is currently designed for one target chat (`TARGET_CHAT_ID`).
- Existing DB rows created before course extraction updates may not include course names until `.ics` is synced again.

## License

This project is licensed under the terms in `LICENSE`.
