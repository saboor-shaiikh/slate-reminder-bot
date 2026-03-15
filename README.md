# Slate Reminder Bot

Slate Reminder Bot is a Telegram assistant for students who want deadline reminders from their LMS calendar.

You send the bot an `.ics` file, it stores events in Supabase Postgres, and then keeps reminding you before each deadline.

## What It Does

- Accepts `.ics` files in Telegram chat
- Extracts events and saves them to PostgreSQL (Supabase)
- Answers deadline questions in Telegram
- Sends automatic reminders at:
  - 72 hours before deadline
  - 24 hours before deadline
  - 8 hours before deadline
  - 1 hour before deadline
- Sends one daily motivational quote at 8:00 AM PST

## Supported Chat Queries

You can ask things like:

- next deadline
- pending assignments
- due today
- due tomorrow
- all deadlines

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

## License

This project is licensed under the terms in `LICENSE`.
