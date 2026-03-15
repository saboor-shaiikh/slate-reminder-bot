# Telegram Migration and Setup Plan

## Goal
Switch the Slate Reminder Bot from WhatsApp to Telegram, while keeping:
- `.ics` ingestion
- Supabase/PostgreSQL persistence
- Gemini intent detection
- Scheduled reminders

## What Has Been Implemented
1. Messaging layer migrated to Telegram API in [telegram_service.py](telegram_service.py).
2. Webhook endpoint migrated from WhatsApp to Telegram updates in [webhook_server.py](webhook_server.py).
3. Reminder delivery migrated to Telegram chat ID in [reminder_engine.py](reminder_engine.py).
4. Config migrated to Telegram variables in [bot_config.py](bot_config.py).
5. Pre-deploy checker migrated to DB + Telegram in [pre_deploy_check.py](pre_deploy_check.py).
6. WhatsApp service removed from runtime code.

## Required Environment Variables
Set these locally and on Render:
- `DATABASE_URL`
- `GEMINI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TARGET_CHAT_ID`
- `TELEGRAM_WEBHOOK_SECRET` (optional but recommended)

## One-Time Telegram Setup
1. Create a bot with BotFather and get `TELEGRAM_BOT_TOKEN`.
2. Find your `TARGET_CHAT_ID` by sending a message to your bot and calling:
   - `https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates`
3. Set webhook URL after deployment using [set_telegram_webhook.py](set_telegram_webhook.py).

## Webhook Route Format
- If `TELEGRAM_WEBHOOK_SECRET` is set:
  - `https://<your-render-domain>/telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>`
- If not set:
  - `https://<your-render-domain>/telegram/webhook`

## Verification Commands
1. Install deps:
   - `./.venv/Scripts/python.exe -m pip install -r requirements.txt`
2. Run integration check:
   - `./.venv/Scripts/python.exe pre_deploy_check.py`
3. Send a live Telegram test message:
   - `./.venv/Scripts/python.exe pre_deploy_check.py --send-test-message`

## Functional Test Flow
1. Send an `.ics` file in Telegram chat with the bot.
2. Bot should reply with sync summary and next reminder.
3. Ask in Telegram:
   - "next deadline"
   - "due today"
   - "due tomorrow"
4. Confirm reminders are sent automatically at 72h/24h/8h/1h.
