# Software Requirements Specification (SRS): Slate Reminder Bot

## 1. Introduction
The **Slate Reminder Bot** is an automated assistant designed for university students to manage academic deadlines. It integrates a university Slate LMS calendar (via `.ics` files) with WhatsApp, providing proactive notifications and natural language interaction using Google Gemini LLM.

## 2. System Overview
- **Platform**: WhatsApp (Meta Cloud API).
- **Backend**: Python (Flask).
- **Database**: PostgreSQL (Supabase).
- **Intelligence**: Google Gemini (Intent Detection & Content Generation).
- **Scheduling**: APScheduler (Background orchestration).

## 3. Functional Requirements

### 3.1. Calendar Synchronization
- **Input**: User sends a standard `.ics` (iCalendar) file via WhatsApp.
- **Parsing**: The system extracts event IDs, titles, types (assignments/quizzes), and deadlines.
- **Persistence**: Events are stored in a PostgreSQL table with conflict resolution (updates existing events if the ID matches).
- **Feedback**: Sends a confirmation message with a summary of loaded events and the next upcoming reminder.

### 3.2. Automated Reminder System
The system periodically scans the database and sends proactive reminders at the following milestones:
- **3 Days (72 Hours)** before the deadline.
- **1 Day (24 Hours)** before the deadline.
- **8 Hours** before the deadline.
- **1 Hour** before the deadline.
*Note: Includes logic to prevent duplicate notifications for the same window.*

### 3.3. Natural Language Interaction (Chat)
Users can query the bot using natural language. The Gemini LLM detects the following intents:
- **Next Deadline**: Retrieve the single closest upcoming event.
- **Pending Assignments**: List all upcoming tasks of type "assignment".
- **Due Today**: List all events with a deadline within the current date.
- **Due Tomorrow**: List all events with a deadline on the following day.
- **All Deadlines**: List every upcoming event stored in the system.

### 3.4. Engagement & Window Maintenance
- **Daily Inspiration**: Sends an AI-generated motivational quote every morning (8:00 AM PST).
- **Purpose**: Primarily keeps the WhatsApp "24-hour customer service window" open, allowing the bot to send session messages throughout the day.

## 4. Non-Functional Requirements
- **Performance**: Asynchronous startup ensures the web server is live within seconds, even if the database or initial sync checks are pending.
- **Reliability**: Uses PostgreSQL Connection Pooling for stable connectivity in cloud environments (Render).
- **Security**: Mandatory SSL encryption for database connections (`sslmode=require`).
- **Scalability**: Stateless webhook handling allows for horizontal scaling.

## 5. User Interface (WhatsApp)
- **Formatting**: Uses Markdown (Bold/Italic) and Emojis for high readability of deadlines.
- **Timeframes**: Calculates and displays relative time (e.g., "Due in 2 days" or "Due in 5 hours").
