import logging
import os
from logging.handlers import RotatingFileHandler
import appdirs


def setup_logger():
    # Create logs directory if it doesn't exist
    appname = "Digico-Reaper Link"
    appauthor = "Justin Stasiw"
    log_dir = appdirs.user_log_dir(appname, appauthor)
    if os.path.isdir(log_dir):
        pass
    else:
        os.makedirs(log_dir)

    # Create logger
    logger = logging.getLogger('Digico-Reaper-Link')
    logger.setLevel(logging.DEBUG)

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    # File handler (rotating log files)
    file_handler = RotatingFileHandler(
        log_dir + "/" + "digico_reaper_link.log",
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Create and configure logger
logger = setup_logger()
