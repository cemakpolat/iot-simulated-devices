# client/app/utils/logger.py
import logging
import os

def setup_logger(name, level=logging.INFO):
    """Sets up a standardized logger for the client application."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent adding multiple handlers if logger is already configured
    if not logger.handlers:
        # Console Handler
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File Handler
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_dir, "client.log"))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger