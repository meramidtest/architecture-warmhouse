from flask import Flask, request, jsonify
import os
import logging
from datetime import datetime
import uuid
import requests
import json
import pika
from database import init_db, get_db_connection
from models import Location, Device, DeviceConfiguration, LocationToDevice


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


IOT_GATEWAY_URL = os.getenv('IOT_GATEWAY_URL', 'http://iot-gateway:8080')
RABBITMQ_URL = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@rabbitmq:5672/')

def get_user_id_from_header():
    user_id = request.headers.get('User-ID')
    if not user_id:
        return None
    return user_id

def publish_device_event(device_data, event_type):
    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()
        

        channel.queue_declare(queue='devices', durable=True)
        
        message = {
            'device_id': device_data['device_id'],
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'device_data': device_data
        }
        
        channel.basic_publish(
            exchange='',
            routing_key='devices',
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        connection.close()
        logger.info(f"Published {event_type} event for device {device_data['device_id']}")
    except Exception as e:
        logger.error(f"Failed to publish device event: {e}")

def register_device_with_gateway(device_data):
    try:
        response = requests.post(
            f"{IOT_GATEWAY_URL}/devices",
            json={
                'device_id': device_data['device_id'],
                'name': device_data['name'],
                'type': device_data['type'],
                'serial_id': device_data.get('serial_id')
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to register device with gateway: {e}")
        return None


@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        'error': 'INVALID_REQUEST',
        'message': 'Переданы некорректные параметры'
    }), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'NOT_FOUND',
        'message': 'Запрашиваемый ресурс не найден'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'INTERNAL_ERROR',
        'message': 'Произошла внутренняя ошибка сервера'
    }), 500


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200


@app.route('/api/v1/locations', methods=['GET'])
def get_locations():
    try:
        user_id = get_user_id_from_header()
        if not user_id:
            return jsonify({'error': 'UNAUTHORIZED', 'message': 'User-ID header required'}), 401
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT location_id, name FROM locations")
        rows = cursor.fetchall()
        
        locations = []
        for row in rows:
            locations.append({
                'location_id': row[0],
                'name': row[1]
            })
        
        conn.close()
        return jsonify(locations), 200
    except Exception as e:
        logger.error(f"Error getting locations: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': str(e)}), 500

@app.route('/api/v1/locations', methods=['POST'])
def create_location():
    try:
        user_id = get_user_id_from_header()
        if not user_id:
            return jsonify({'error': 'UNAUTHORIZED', 'message': 'User-ID header required'}), 401
        
        data = request.get_json()
        if not data or 'name' not in data:
            return bad_request(None)
        
        location_id = str(uuid.uuid4())
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO locations (location_id, name) VALUES (%s, %s)",
            (location_id, data['name'])
        )
        conn.commit()
        
        location = {
            'location_id': location_id,
            'name': data['name']
        }
        
        conn.close()
        return jsonify(location), 201
    except Exception as e:
        logger.error(f"Error creating location: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': str(e)}), 500


@app.route('/api/v1/devices', methods=['GET'])
def get_devices():
    try:
        user_id = get_user_id_from_header()
        if not user_id:
            return jsonify({'error': 'UNAUTHORIZED', 'message': 'User-ID header required'}), 401
        
        conn = get_db_connection()
        cursor = conn.cursor()
        

        cursor.execute("""
            SELECT d.device_id, d.location_id, d.serial_id, d.name, d.type, d.status, 
                   d.created_at, d.updated_at
            FROM devices d
            JOIN location_to_device ltd ON d.device_id = ltd.device_id
            WHERE ltd.user_id = %s
        """, (user_id,))
        
        rows = cursor.fetchall()
        
        devices = []
        for row in rows:
            devices.append({
                'device_id': row[0],
                'location_id': row[1],
                'serial_id': row[2],
                'name': row[3],
                'type': row[4],
                'status': row[5],
                'created_at': row[6].isoformat() if row[6] else None,
                'updated_at': row[7].isoformat() if row[7] else None
            })
        
        conn.close()
        return jsonify(devices), 200
    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': str(e)}), 500

@app.route('/api/v1/devices', methods=['POST'])
def create_device():
    try:
        user_id = get_user_id_from_header()
        if not user_id:
            return jsonify({'error': 'UNAUTHORIZED', 'message': 'User-ID header required'}), 401
        
        data = request.get_json()
        required_fields = ['location_id', 'serial_id', 'name', 'type']
        
        if not data or not all(field in data for field in required_fields):
            return bad_request(None)
        
        device_id = str(uuid.uuid4())
        status = data.get('status', 'active')
        now = datetime.utcnow()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        

        cursor.execute("SELECT location_id FROM locations WHERE location_id = %s", (data['location_id'],))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'NOT_FOUND', 'message': 'Location not found'}), 404
        

        cursor.execute("""
            INSERT INTO devices (device_id, location_id, serial_id, name, type, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (device_id, data['location_id'], data['serial_id'], data['name'], data['type'], status, now, now))
        

        cursor.execute("""
            INSERT INTO location_to_device (device_id, user_id, type)
            VALUES (%s, %s, %s)
        """, (device_id, user_id, 'owner'))
        
        conn.commit()
        
        device = {
            'device_id': device_id,
            'location_id': data['location_id'],
            'serial_id': data['serial_id'],
            'name': data['name'],
            'type': data['type'],
            'status': status,
            'created_at': now.isoformat() + 'Z',
            'updated_at': now.isoformat() + 'Z'
        }
        

        gateway_response = register_device_with_gateway(device)
        

        publish_device_event(device, 'registered')
        
        conn.close()
        return jsonify(device), 201
    except Exception as e:
        logger.error(f"Error creating device: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': str(e)}), 500


@app.route('/api/v1/devices/<device_id>/configurations', methods=['GET'])
def get_device_configurations(device_id):
    try:
        user_id = get_user_id_from_header()
        if not user_id:
            return jsonify({'error': 'UNAUTHORIZED', 'message': 'User-ID header required'}), 401
        
        conn = get_db_connection()
        cursor = conn.cursor()
        

        cursor.execute("""
            SELECT device_id FROM location_to_device 
            WHERE device_id = %s AND user_id = %s
        """, (device_id, user_id))
        
        if not cursor.fetchone():
            conn.close()
            return not_found(None)
        

        cursor.execute("""
            SELECT config_id, device_id, config_name, config_value, config_type, 
                   is_active, created_at, updated_at
            FROM device_configurations
            WHERE device_id = %s
        """, (device_id,))
        
        rows = cursor.fetchall()
        
        configurations = []
        for row in rows:
            configurations.append({
                'config_id': row[0],
                'device_id': row[1],
                'config_name': row[2],
                'config_value': row[3],
                'config_type': row[4],
                'is_active': row[5],
                'created_at': row[6].isoformat() if row[6] else None,
                'updated_at': row[7].isoformat() if row[7] else None
            })
        
        conn.close()
        return jsonify(configurations), 200
    except Exception as e:
        logger.error(f"Error getting device configurations: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': str(e)}), 500

@app.route('/api/v1/devices/<device_id>/configurations', methods=['POST'])
def create_device_configuration(device_id):
    try:
        user_id = get_user_id_from_header()
        if not user_id:
            return jsonify({'error': 'UNAUTHORIZED', 'message': 'User-ID header required'}), 401
        
        data = request.get_json()
        required_fields = ['config_name', 'config_value', 'config_type']
        
        if not data or not all(field in data for field in required_fields):
            return bad_request(None)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        

        cursor.execute("""
            SELECT device_id FROM location_to_device 
            WHERE device_id = %s AND user_id = %s
        """, (device_id, user_id))
        
        if not cursor.fetchone():
            conn.close()
            return not_found(None)
        
        config_id = str(uuid.uuid4())
        is_active = data.get('is_active', True)
        now = datetime.utcnow()
        
        cursor.execute("""
            INSERT INTO device_configurations 
            (config_id, device_id, config_name, config_value, config_type, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (config_id, device_id, data['config_name'], data['config_value'], 
              data['config_type'], is_active, now, now))
        
        conn.commit()
        
        configuration = {
            'config_id': config_id,
            'device_id': device_id,
            'config_name': data['config_name'],
            'config_value': data['config_value'],
            'config_type': data['config_type'],
            'is_active': is_active,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat()
        }
        
        conn.close()
        return jsonify(configuration), 201
    except Exception as e:
        logger.error(f"Error creating device configuration: {e}")
        return jsonify({'error': 'INTERNAL_ERROR', 'message': str(e)}), 500


try:
    init_db()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    raise

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, debug=True) 