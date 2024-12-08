import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR)

# Create a file handler that logs error messages to a file
file_handler = logging.FileHandler('error_logs.log')
file_handler.setLevel(logging.ERROR)

# Create a formatter for more readable logs
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)