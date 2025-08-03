import sqlite3
import uuid
import os
from datetime import datetime
from typing import Optional, Dict, Any

class Database:
    def __init__(self, db_path: str = 'iot_gateway.db'):
        self.database_url = os.environ.get('DATABASE_URL')
        self.db_path = db_path
        self.is_postgres = self.database_url and self.database_url.startswith('postgresql')
        self.init_db()
    
    def get_connection(self):
        if self.is_postgres:
            import psycopg2
            return psycopg2.connect(self.database_url)
        else:
            return sqlite3.connect(self.db_path)
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.is_postgres:

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    device_id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    type VARCHAR(100) NOT NULL,
                    serial_id VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'registered',
                    registered_at TIMESTAMPTZ NOT NULL,
                    last_seen TIMESTAMPTZ,
                    telemetry JSONB
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS commands (
                    id SERIAL PRIMARY KEY,
                    device_id VARCHAR(36) NOT NULL,
                    command VARCHAR(255) NOT NULL,
                    parameters JSONB,
                    sent_at TIMESTAMPTZ NOT NULL,
                    FOREIGN KEY (device_id) REFERENCES devices (device_id)
                )
            ''')
        else:

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    serial_id TEXT,
                    status TEXT DEFAULT 'registered',
                    registered_at TEXT NOT NULL,
                    last_seen TEXT,
                    telemetry TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    command TEXT NOT NULL,
                    parameters TEXT,
                    sent_at TEXT NOT NULL,
                    FOREIGN KEY (device_id) REFERENCES devices (device_id)
                )
            ''')
        
        conn.commit()
        conn.close()

class DeviceManager:
    def __init__(self, db: Database):
        self.db = db
    
    def register_device(self, device_id: str, name: str, device_type: str, serial_id: Optional[str] = None) -> Dict[str, Any]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        

        if self.db.is_postgres:
            cursor.execute('SELECT device_id FROM devices WHERE device_id = %s', (device_id,))
        else:
            cursor.execute('SELECT device_id FROM devices WHERE device_id = ?', (device_id,))
        
        if cursor.fetchone():
            conn.close()
            raise ValueError("Device already exists")
        
        registered_at = datetime.utcnow().isoformat() + 'Z'
        
        if self.db.is_postgres:
            cursor.execute('''
                INSERT INTO devices (device_id, name, type, serial_id, status, registered_at)
                VALUES (%s, %s, %s, %s, 'registered', %s)
            ''', (device_id, name, device_type, serial_id, registered_at))
        else:
            cursor.execute('''
                INSERT INTO devices (device_id, name, type, serial_id, status, registered_at)
                VALUES (?, ?, ?, ?, 'registered', ?)
            ''', (device_id, name, device_type, serial_id, registered_at))
        
        conn.commit()
        conn.close()
        
        return {
            'device_id': device_id,
            'status': 'registered',
            'registered_at': registered_at
        }
    
    def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        if self.db.is_postgres:
            cursor.execute('''
                SELECT device_id, status, last_seen, telemetry 
                FROM devices WHERE device_id = %s
            ''', (device_id,))
        else:
            cursor.execute('''
                SELECT device_id, status, last_seen, telemetry 
                FROM devices WHERE device_id = ?
            ''', (device_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        

        telemetry = {}
        if row[3]:
            if self.db.is_postgres:

                telemetry = row[3] if isinstance(row[3], dict) else {}
            else:

                try:
                    import json
                    telemetry = json.loads(row[3])
                except:
                    telemetry = {}
        
        return {
            'device_id': row[0],
            'status': 'online' if row[1] == 'active' else 'offline',
            'last_seen': row[2],
            'telemetry': telemetry
        }
    
    def send_command(self, device_id: str, command: str, parameters: Optional[Dict[str, Any]] = None) -> bool:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        

        if self.db.is_postgres:
            cursor.execute('SELECT device_id FROM devices WHERE device_id = %s', (device_id,))
        else:
            cursor.execute('SELECT device_id FROM devices WHERE device_id = ?', (device_id,))
        
        if not cursor.fetchone():
            conn.close()
            return False
        

        sent_at = datetime.utcnow().isoformat() + 'Z'
        
        if self.db.is_postgres:
            import json
            params_json = json.dumps(parameters) if parameters else None
            cursor.execute('''
                INSERT INTO commands (device_id, command, parameters, sent_at)
                VALUES (%s, %s, %s, %s)
            ''', (device_id, command, params_json, sent_at))
            

            cursor.execute('''
                UPDATE devices SET last_seen = %s, status = 'active' WHERE device_id = %s
            ''', (sent_at, device_id))
        else:
            import json
            params_json = json.dumps(parameters) if parameters else None
            cursor.execute('''
                INSERT INTO commands (device_id, command, parameters, sent_at)
                VALUES (?, ?, ?, ?)
            ''', (device_id, command, params_json, sent_at))
            

            cursor.execute('''
                UPDATE devices SET last_seen = ?, status = 'active' WHERE device_id = ?
            ''', (sent_at, device_id))
        
        conn.commit()
        conn.close()
        
        return True
    
    def update_device_telemetry(self, device_id: str, telemetry_data: Dict[str, Any]):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        last_seen = datetime.utcnow().isoformat() + 'Z'
        
        if self.db.is_postgres:
            import json
            telemetry_json = json.dumps(telemetry_data)
            cursor.execute('''
                UPDATE devices 
                SET telemetry = %s, last_seen = %s, status = 'active'
                WHERE device_id = %s
            ''', (telemetry_json, last_seen, device_id))
        else:
            import json
            telemetry_json = json.dumps(telemetry_data)
            cursor.execute('''
                UPDATE devices 
                SET telemetry = ?, last_seen = ?, status = 'active'
                WHERE device_id = ?
            ''', (telemetry_json, last_seen, device_id))
        
        conn.commit()
        conn.close()
    
    def get_all_devices(self) -> list:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        if self.db.is_postgres:
            cursor.execute('''
                SELECT device_id, name, type, serial_id, status, registered_at, last_seen, telemetry 
                FROM devices
            ''')
        else:
            cursor.execute('''
                SELECT device_id, name, type, serial_id, status, registered_at, last_seen, telemetry 
                FROM devices
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        devices = []
        for row in rows:

            telemetry = {}
            if row[7]:
                if self.db.is_postgres:
                    telemetry = row[7] if isinstance(row[7], dict) else {}
                else:
                    try:
                        import json
                        telemetry = json.loads(row[7])
                    except:
                        telemetry = {}
            
            devices.append({
                'device_id': row[0],
                'name': row[1],
                'type': row[2],
                'serial_id': row[3],
                'status': row[4],
                'registered_at': row[5],
                'last_seen': row[6],
                'telemetry': telemetry
            })
        
        return devices 