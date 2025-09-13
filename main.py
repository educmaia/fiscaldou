from apscheduler.schedulers.background import BackgroundScheduler
from search import find_matches
from summarize import summarize_matches
from notify import send_notifications
from datetime import datetime
import os
from logging_config import setup_logger

logger = setup_logger('main')

def daily_dou_check():
    """Job to run daily: search, summarize, notify."""
    try:
        logger.info(f"Starting daily DOU check at {datetime.now()}")
        matches = find_matches()
        if matches:
            summarized = summarize_matches(matches)
            send_notifications(summarized)
        else:
            logger.info("No matches found today.")
    except Exception as e:
        logger.error(f"Error in daily_dou_check: {e}")

if __name__ == '__main__':
    try:
        # Setup scheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            daily_dou_check,
            'cron',
            hour=8,
            minute=0,
            id='daily_dou_check',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("DOU Notifier Scheduler started. Daily check at 8:00 AM.")
        print("DOU Notifier Scheduler started. Daily check at 8:00 AM.")
        print("Press Ctrl+C to exit.")
        
        # Keep running
        import time
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler.")
        scheduler.shutdown()
    except Exception as e:
        logger.error(f"Error in main: {e}")