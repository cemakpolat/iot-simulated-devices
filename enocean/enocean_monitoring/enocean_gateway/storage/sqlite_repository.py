# storage/sqlite_repository.py
import sqlite3
import json
import threading
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from pathlib import Path
import time

from ..domain.models import DeviceConfig, DeviceId, EEPProfile
from .repositories import DeviceRepository
from ..utils.logger import Logger


class SQLiteDeviceRepository(DeviceRepository):
    """SQLite-implementation of DeviceRepository with connection pooling and migrations"""

    def __init__(self, db_path: str, logger: Logger):
        self.db_path = Path(db_path)
        self.logger = logger
        self._local = threading.local()
        self._ensure_database_exists()
        self._run_migrations()

    def _ensure_database_exists(self):
        """Create database file and directory if they don't exist"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _get_connection(self):
        """Get thread-local database connection with proper cleanup"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA foreign_keys=ON")

        try:
            yield self._local.connection
        except Exception as e:
            self._local.connection.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        else:
            self._local.connection.commit()

    def _run_migrations(self):
        """Run database schema migrations"""
        with self._get_connection() as conn:
            # Check current schema version
            try:
                cursor = conn.execute("SELECT version FROM schema_version ORDER BY id DESC LIMIT 1")
                current_version = cursor.fetchone()
                current_version = current_version[0] if current_version else 0
            except sqlite3.OperationalError:
                current_version = 0

            # Apply migrations
            migrations = [
                self._migration_001_initial_schema,
                self._migration_002_add_indices,
                self._migration_003_add_timestamps
            ]

            for version, migration in enumerate(migrations, 1):
                if current_version < version:
                    self.logger.info(f"Applying migration {version}")
                    migration(conn)
                    conn.execute(
                        "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)",
                        (version, int(time.time()))
                    )

    def _migration_001_initial_schema(self, conn: sqlite3.Connection):
        """Create initial database schema"""
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                applied_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                eep_profile TEXT NOT NULL,
                location TEXT,
                description TEXT,
                capabilities TEXT, -- JSON array
                last_seen INTEGER,
                is_active BOOLEAN DEFAULT 1,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS device_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                raw_data BLOB,
                decoded_data TEXT, -- JSON
                signal_strength INTEGER,
                FOREIGN KEY (device_id) REFERENCES devices (device_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS unknown_devices (
                device_id TEXT PRIMARY KEY,
                first_seen INTEGER NOT NULL,
                last_seen INTEGER NOT NULL,
                packet_count INTEGER DEFAULT 1,
                suggested_profiles TEXT, -- JSON array
                analysis_data TEXT -- JSON
            );
        """)

    def _migration_002_add_indices(self, conn: sqlite3.Connection):
        """Add performance indices"""
        conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_devices_active ON devices (is_active);
            CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices (last_seen);
            CREATE INDEX IF NOT EXISTS idx_device_data_timestamp ON device_data (timestamp);
            CREATE INDEX IF NOT EXISTS idx_device_data_device_timestamp ON device_data (device_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_unknown_devices_last_seen ON unknown_devices (last_seen);
        """)

    def _migration_003_add_timestamps(self, conn: sqlite3.Connection):
        """Add additional timestamp tracking"""
        conn.executescript("""
            ALTER TABLE devices ADD COLUMN last_data_received INTEGER DEFAULT 0;
            CREATE INDEX IF NOT EXISTS idx_devices_last_data ON devices (last_data_received);
        """)

    def get_device(self, device_id: DeviceId) -> Optional[DeviceConfig]:
        """Retrieve device configuration by ID"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM devices WHERE device_id = ? AND is_active = 1",
                (device_id.value,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_device_config(row)

    def save_device(self, device: DeviceConfig) -> bool:
        """Save or update device configuration"""
        try:
            with self._get_connection() as conn:
                now = int(time.time())

                # Check if device exists
                cursor = conn.execute(
                    "SELECT device_id FROM devices WHERE device_id = ?",
                    (device.device_id.value,)
                )
                exists = cursor.fetchone() is not None

                if exists:
                    # Update existing device
                    conn.execute("""
                        UPDATE devices SET 
                            name = ?, eep_profile = ?, location = ?, description = ?,
                            capabilities = ?, updated_at = ?, is_active = 1
                        WHERE device_id = ?
                    """, (
                        device.name,
                        device.eep_profile.profile_id,
                        device.location or "",
                        device.description or "",
                        json.dumps(device.capabilities),
                        now,
                        device.device_id.value
                    ))
                else:
                    # Insert new device
                    conn.execute("""
                        INSERT INTO devices 
                        (device_id, name, eep_profile, location, description, capabilities, 
                         created_at, updated_at, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """, (
                        device.device_id.value,
                        device.name,
                        device.eep_profile.profile_id,
                        device.location or "",
                        device.description or "",
                        json.dumps(device.capabilities),
                        now,
                        now
                    ))

                self.logger.info(f"{'Updated' if exists else 'Created'} device {device.device_id.value}")
                return True

        except Exception as e:
            self.logger.error(f"Failed to save device {device.device_id.value}: {e}")
            return False

    def delete_device(self, device_id: DeviceId) -> bool:
        """Soft delete device (mark as inactive)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "UPDATE devices SET is_active = 0, updated_at = ? WHERE device_id = ?",
                    (int(time.time()), device_id.value)
                )

                if cursor.rowcount > 0:
                    self.logger.info(f"Deleted device {device_id.value}")
                    return True
                else:
                    self.logger.warning(f"Device {device_id.value} not found for deletion")
                    return False

        except Exception as e:
            self.logger.error(f"Failed to delete device {device_id.value}: {e}")
            return False

    def get_all_devices(self) -> List[DeviceConfig]:
        """Get all active devices"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM devices WHERE is_active = 1 ORDER BY name"
            )

            return [self._row_to_device_config(row) for row in cursor.fetchall()]

    def device_exists(self, device_id: DeviceId) -> bool:
        """Check if device exists and is active"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM devices WHERE device_id = ? AND is_active = 1",
                (device_id.value,)
            )
            return cursor.fetchone() is not None

    def update_device_activity(self, device_id: DeviceId) -> bool:
        """Update last seen timestamp for device"""
        try:
            with self._get_connection() as conn:
                now = int(time.time())
                cursor = conn.execute(
                    "UPDATE devices SET last_seen = ?, last_data_received = ? WHERE device_id = ? AND is_active = 1",
                    (now, now, device_id.value)
                )
                return cursor.rowcount > 0

        except Exception as e:
            self.logger.error(f"Failed to update activity for device {device_id.value}: {e}")
            return False

    def store_device_data(self, device_id: DeviceId, raw_data: bytes,
                          decoded_data: Dict[str, Any], signal_strength: Optional[int] = None):
        """Store device sensor data"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO device_data 
                    (device_id, timestamp, raw_data, decoded_data, signal_strength)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    device_id.value,
                    int(time.time()),
                    raw_data,
                    json.dumps(decoded_data),
                    signal_strength
                ))

                # Update device activity
                self.update_device_activity(device_id)

        except Exception as e:
            self.logger.error(f"Failed to store data for device {device_id.value}: {e}")

    def get_device_history(self, device_id: DeviceId, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent device data history"""
        with self._get_connection() as conn:
            since_timestamp = int(time.time()) - (hours * 3600)

            cursor = conn.execute("""
                SELECT timestamp, decoded_data, signal_strength 
                FROM device_data 
                WHERE device_id = ? AND timestamp > ?
                ORDER BY timestamp DESC
            """, (device_id.value, since_timestamp))

            return [
                {
                    "timestamp": row[0],
                    "data": json.loads(row[1]) if row[1] else {},
                    "signal_strength": row[2]
                }
                for row in cursor.fetchall()
            ]

    def cleanup_old_data(self, days: int = 30):
        """Clean up old device data"""
        try:
            with self._get_connection() as conn:
                cutoff_timestamp = int(time.time()) - (days * 24 * 3600)

                cursor = conn.execute(
                    "DELETE FROM device_data WHERE timestamp < ?",
                    (cutoff_timestamp,)
                )

                self.logger.info(f"Cleaned up {cursor.rowcount} old data records")

        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get repository statistics"""
        with self._get_connection() as conn:
            stats = {}

            # Device counts
            cursor = conn.execute("SELECT COUNT(*) FROM devices WHERE is_active = 1")
            stats['active_devices'] = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM devices WHERE is_active = 0")
            stats['inactive_devices'] = cursor.fetchone()[0]

            # Data points
            cursor = conn.execute("SELECT COUNT(*) FROM device_data")
            stats['total_data_points'] = cursor.fetchone()[0]

            # Recent activity (last 24 hours)
            recent_timestamp = int(time.time()) - (24 * 3600)
            cursor = conn.execute(
                "SELECT COUNT(*) FROM device_data WHERE timestamp > ?",
                (recent_timestamp,)
            )
            stats['recent_data_points'] = cursor.fetchone()[0]

            # Database size
            cursor = conn.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            stats['database_size_bytes'] = cursor.fetchone()[0]

            return stats

    def _row_to_device_config(self, row: sqlite3.Row) -> DeviceConfig:
        """Convert database row to DeviceConfig object"""
        capabilities = json.loads(row['capabilities']) if row['capabilities'] else []

        # Create EEP profile (you'd need to load this from your EEP registry)
        eep_profile = EEPProfile(
            profile_id=row['eep_profile'],
            description=f"EEP Profile {row['eep_profile']}",
            capabilities=capabilities
        )

        return DeviceConfig(
            device_id=DeviceId(row['device_id']),
            name=row['name'],
            eep_profile=eep_profile,
            location=row['location'] or "",
            description=row['description'] or "",
            capabilities=capabilities
        )

    def health_check(self) -> Dict[str, Any]:
        """Check repository health"""
        try:
            with self._get_connection() as conn:
                # Test basic connectivity
                cursor = conn.execute("SELECT 1")
                cursor.fetchone()

                # Check database integrity
                cursor = conn.execute("PRAGMA integrity_check")
                integrity = cursor.fetchone()[0]

                return {
                    "status": "healthy",
                    "database_path": str(self.db_path),
                    "integrity_check": integrity,
                    "statistics": self.get_statistics()
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "database_path": str(self.db_path)
            }