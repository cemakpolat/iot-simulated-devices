import os
import psycopg2
from psycopg2 import pool
import logging
from config import Config

logger = logging.getLogger(__name__)

# --- LAZY INITIALIZATION PATTERN ---
db_pool = None
def get_db_pool():
    """Lazily creates and returns a singleton database connection pool."""
    global db_pool
    if db_pool is None:
        try:
            logger.info("Initializing database connection pool...")
            db_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20, dsn=os.getenv("DATABASE_URL")
            )
            logger.info("Database connection pool created successfully.")
        except psycopg2.OperationalError as e:
            logger.error(f"FATAL: Could not connect to database during pool initialization: {e}")
            raise
    return db_pool

def init_db():
    """Initializes the database schema for all tables."""
    conn = get_db_pool().getconn()
    try:
        with conn.cursor() as cur:
            # --- ADD THE NEW 'devices' TABLE ---
            cur.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    is_active BOOLEAN NOT NULL DEFAULT TRUE
                );
            """)

            # Create the main table for readings
            cur.execute("""
                CREATE TABLE IF NOT EXISTS readings (
                    time TIMESTAMPTZ NOT NULL,
                    device_id TEXT NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
                    metric_type TEXT NOT NULL,
                    value DOUBLE PRECISION NOT NULL,
                    result TEXT,
                    confidence DOUBLE PRECISION
                );
            """)
            # Create the TimescaleDB hypertable
            cur.execute("SELECT create_hypertable('readings', 'time', if_not_exists => TRUE);")
            conn.commit()
            logger.info("Database initialized with 'devices' and 'readings' tables.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    finally:
        get_db_pool().putconn(conn)

# --- ADD NEW DEVICE MANAGEMENT FUNCTIONS ---

def register_or_get_device(device_id):
    """
    Checks if a device exists. If not, it creates it.
    Returns True if the device is known (either pre-existing or newly created).
    """
    conn = get_db_pool().getconn()
    try:
        with conn.cursor() as cur:
            # Use INSERT ... ON CONFLICT to atomically create the device if it doesn't exist.
            # This is a robust way to handle concurrent requests.
            cur.execute("""
                INSERT INTO devices (device_id)
                VALUES (%s)
                ON CONFLICT (device_id) DO NOTHING;
            """, (device_id,))
            conn.commit()
            return True # The device is now guaranteed to exist
    except Exception as e:
        logger.error(f"Error registering device {device_id}: {e}")
        return False
    finally:
        get_db_pool().putconn(conn)

def is_device_known(device_id):
    """Checks if a device ID exists in the devices table."""
    conn = get_db_pool().getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT EXISTS(SELECT 1 FROM devices WHERE device_id = %s);", (device_id,))
            return cur.fetchone()[0]
    except Exception as e:
        logger.error(f"Error checking device {device_id}: {e}")
        return False
    finally:
        get_db_pool().putconn(conn)

def insert_reading(timestamp, device_id, metric_type, value, result, confidence):
    conn = get_db_pool().getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO readings (time, device_id, metric_type, value, result, confidence)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (timestamp, device_id, metric_type, value, result, confidence))
            conn.commit()
    finally:
        get_db_pool().putconn(conn)

def get_latest_readings_from_db():
    """Fetches the most recent reading for every *active* device."""
    conn = get_db_pool().getconn()
    try:
        with conn.cursor() as cur:
            query = """
                SELECT DISTINCT ON (device_id, metric_type)
                    device_id, metric_type, value, result, confidence, time
                FROM readings
                WHERE time > NOW() - INTERVAL '%s seconds'
                ORDER BY device_id, metric_type, time DESC;
            """
            # This line will now work because Config is imported
            cur.execute(query, (Config.ACTIVE_DEVICE_TIMEOUT_SECONDS,))
            
            # ... (rest of the function is unchanged) ...
            rows = cur.fetchall()
            devices = {}
            for row in rows:
                device_id, metric_type, value, result, confidence, time = row
                if device_id not in devices:
                    devices[device_id] = {
                        "device_id": device_id, "timestamp": time.isoformat(), "metrics": []
                    }
                devices[device_id]["metrics"].append({
                    "type": metric_type, "value": value, "result": result, "confidence": confidence
                })
            return list(devices.values())
    except Exception as e:
        logger.error(f"Error fetching latest readings: {e}")
        return []
    finally:
        get_db_pool().putconn(conn)

def delete_inactive_devices_from_db():
    """Deletes all readings for devices that are considered inactive."""
    conn = get_db_pool().getconn()
    try:
        with conn.cursor() as cur:
            query = """
                DELETE FROM readings
                WHERE device_id IN (
                    SELECT device_id FROM (
                        SELECT device_id, max(time) AS last_seen
                        FROM readings GROUP BY device_id
                    ) AS last_times
                    WHERE last_seen < NOW() - INTERVAL '%s seconds'
                );
            """
            # This line will now work because Config is imported
            cur.execute(query, (Config.ACTIVE_DEVICE_TIMEOUT_SECONDS,))
            deleted_count = cur.rowcount
            conn.commit()
            return deleted_count
    except Exception as e:
        logger.error(f"Error deleting inactive devices: {e}")
        # Re-raise the exception to make the Celery task fail loudly
        raise
    finally:
        get_db_pool().putconn(conn)