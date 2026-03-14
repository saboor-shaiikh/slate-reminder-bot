import logging
import database
from reminder_engine import start_scheduler
from webhook_server import start_server

# Build the global standardized logging implementation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """
    Kicks off startup procedures sequentially.
    Init DB -> Launch Timers/Crons -> Surface the Webhook layer.
    """
    logger.info("Initializing Slate Reminder Bot platform components...")
    
    # 1. Initialize DB / Setup table states properly
    database.initialize_database()
    logger.info("SQLite Database successfully mapped across logic layer.")
    
    # 2. Launch Background Processes
    start_scheduler()
    logger.info("Reminders orchestration routing online.")
    
    # 3. Mount REST Server for webhook event listeners
    import os
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Flask application core webhook server on port {port}...")
    start_server(port=port)

if __name__ == "__main__":
    main()
