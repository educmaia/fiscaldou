from search import find_matches
from summarize import summarize_matches
from notify import send_notifications
from datetime import datetime
import os
from logging_config import setup_logger

logger = setup_logger('run_once')


def main():
    """Run the daily DOU check once and exit."""
    try:
        logger.info(f"Starting one-time DOU check at {datetime.now()}")
        matches = find_matches()
        if matches:
            summarized = summarize_matches(matches)
            send_notifications(summarized)
            logger.info(f"Processed {len(matches)} matches.")
        else:
            logger.info("No matches found.")
    except Exception as e:
        logger.error(f"Error in one-time check: {e}")


if __name__ == '__main__':
    main()
