
import logging
import os
from datetime import datetime
current_date=datetime.now().strftime('%Y-%m-%d')

# Function to create and configure the logger
def create_logger(project_name):
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '../logs', project_name)
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(project_name)

    # Set up a handler to write logs to a file
    handler = logging.handlers.TimedRotatingFileHandler(
        os.path.join(log_dir, f'{current_date}.log'),
        when="midnight",  # Rotate log files daily
        backupCount=14,   # Keep logs for 14 days
    )

    # Set log format
    formatter = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    # Add handler to the logger
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger
