import logging
from database import init_db

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    logging.info("Attempting to initialize the database...")
    try:
        init_db()
        logging.info("Database initialization script finished successfully.")
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        # Exit with a non-zero status code to indicate failure
        exit(1)