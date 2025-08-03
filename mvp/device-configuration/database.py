import psycopg2
import psycopg2.extras
import os
import logging

logger = logging.getLogger(__name__)


DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': os.getenv('DB_PORT', 5432),
    'database': os.getenv('DB_NAME', 'device_config'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                location_id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(255) NOT NULL
            )
        """)
        

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id VARCHAR(36) PRIMARY KEY,
                location_id VARCHAR(36) NOT NULL,
                serial_id VARCHAR(255) NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                type VARCHAR(100) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'active',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (location_id) REFERENCES locations(location_id)
            )
        """)
        

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS location_to_device (
                device_id VARCHAR(36) NOT NULL,
                user_id VARCHAR(36) NOT NULL,
                type VARCHAR(50) NOT NULL DEFAULT 'user',
                PRIMARY KEY (device_id, user_id),
                FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
            )
        """)
        

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_configurations (
                config_id VARCHAR(36) PRIMARY KEY,
                device_id VARCHAR(36) NOT NULL,
                config_name VARCHAR(255) NOT NULL,
                config_value TEXT NOT NULL,
                config_type VARCHAR(50) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
            )
        """)
        

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_devices_location_id ON devices(location_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_devices_serial_id ON devices(serial_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_location_to_device_user_id ON location_to_device(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_configurations_device_id ON device_configurations(device_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_configurations_active ON device_configurations(is_active)")
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise 