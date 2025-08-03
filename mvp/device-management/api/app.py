from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
import requests
import os
import json
import redis
from sqlalchemy.dialects.postgresql import UUID, JSON
from config import config

app = Flask(__name__)


config_name = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[config_name])


IOT_GATEWAY_URL = app.config['IOT_GATEWAY_URL']


redis_client = redis.from_url(app.config['REDIS_URL'])

db = SQLAlchemy(app)


class Device(db.Model):
    __tablename__ = 'devices'
    
    device_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    serial_id = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    

    logic_configs = db.relationship('DeviceCustomLogic', backref='device', lazy=True, cascade='all, delete-orphan')
    telemetry = db.relationship('Telemetry', backref='device', lazy=True, cascade='all, delete-orphan')

class DeviceCustomLogic(db.Model):
    __tablename__ = 'device_custom_logic'
    
    logic_config_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.device_id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    value = db.Column(JSON, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class Telemetry(db.Model):
    __tablename__ = 'telemetry'
    
    telemetry_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = db.Column(UUID(as_uuid=True), db.ForeignKey('devices.device_id'), nullable=False)
    value = db.Column(JSON, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


def get_user_id():
    return request.headers.get('User-ID')

def device_to_dict(device):
    return {
        'device_id': str(device.device_id),
        'serial_id': device.serial_id,
        'name': device.name,
        'type': device.type,
        'created_at': device.created_at.isoformat(),
        'updated_at': device.updated_at.isoformat()
    }

def logic_to_dict(logic):
    return {
        'logic_config_id': str(logic.logic_config_id),
        'device_id': str(logic.device_id),
        'name': logic.name,
        'value': logic.value,
        'type': logic.type,
        'is_active': logic.is_active,
        'created_at': logic.created_at.isoformat(),
        'updated_at': logic.updated_at.isoformat()
    }

def telemetry_to_dict(telemetry):
    return {
        'telemetry_id': str(telemetry.telemetry_id),
        'device_id': str(telemetry.device_id),
        'value': telemetry.value,
        'type': telemetry.type,
        'created_at': telemetry.created_at.isoformat()
    }

def send_command_to_iot_gateway(device_id, command_data):
    try:
        response = requests.post(
            f"{IOT_GATEWAY_URL}/devices/{device_id}/commands",
            json=command_data,
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        app.logger.error(f"Failed to send command to IoT Gateway: {e}")
        return False

def get_cached_telemetry(device_id):
    try:
        cache_key = f"device:telemetry:latest:{device_id}"
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
        return None
    except Exception as e:
        app.logger.error(f"Failed to get cached telemetry: {e}")
        return None


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'NOT_FOUND',
        'message': 'Запрашиваемый ресурс не найден'
    }), 404

@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        'error': 'INVALID_REQUEST',
        'message': 'Переданы некорректные параметры'
    }), 400

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'INTERNAL_ERROR',
        'message': 'Произошла внутренняя ошибка сервера'
    }), 500


@app.route('/api/v1/devices', methods=['GET'])
def get_all_devices():
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        

        if limit < 1 or limit > 100:
            limit = 20
        if offset < 0:
            offset = 0
        

        devices_query = Device.query.order_by(Device.created_at.desc())
        total_count = devices_query.count()
        
        devices = devices_query.offset(offset).limit(limit).all()
        

        devices_data = [device_to_dict(device) for device in devices]
        
        return jsonify({
            'devices': devices_data,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + limit) < total_count
        })
        
    except Exception as e:
        app.logger.error(f"Error getting all devices: {e}")
        return internal_error(e)

@app.route('/api/v1/devices/<device_id>', methods=['GET'])
def get_device(device_id):
    try:
        device = Device.query.get_or_404(device_id)
        return jsonify(device_to_dict(device))
        
    except Exception as e:
        app.logger.error(f"Error getting device {device_id}: {e}")
        return internal_error(e)


@app.route('/api/v1/devices/<device_id>/logic', methods=['GET'])
def get_device_logic(device_id):
    try:

        logic_configs = DeviceCustomLogic.query.filter_by(device_id=device_id).all()
        return jsonify([logic_to_dict(logic) for logic in logic_configs])
    except Exception as e:
        app.logger.error(f"Error getting device logic: {e}")
        return internal_error(e)

@app.route('/api/v1/devices/<device_id>/logic', methods=['POST'])
def create_device_logic(device_id):
    try:
        data = request.get_json()
        
        if not data or not all(key in data for key in ['name', 'value', 'type']):
            return bad_request('Missing required fields')
        

        device = Device.query.get(device_id)
        if not device:
            device = Device(
                device_id=device_id,
                serial_id=f"auto-{device_id[:8]}",
                name=f"Device {device_id[:8]}",
                type="unknown"
            )
            db.session.add(device)
        
        logic = DeviceCustomLogic(
            device_id=device_id,
            name=data['name'],
            value=data['value'],
            type=data['type'],
            is_active=data.get('is_active', True)
        )
        
        db.session.add(logic)
        db.session.commit()
        
        return jsonify(logic_to_dict(logic)), 201
    except Exception as e:
        app.logger.error(f"Error creating device logic: {e}")
        db.session.rollback()
        return internal_error(e)

@app.route('/api/v1/devices/<device_id>/logic/<logic_id>', methods=['PUT'])
def update_device_logic(device_id, logic_id):
    try:
        logic = DeviceCustomLogic.query.filter_by(
            logic_config_id=logic_id, 
            device_id=device_id
        ).first_or_404()
        
        data = request.get_json()
        if not data:
            return bad_request('No data provided')
        
        if 'name' in data:
            logic.name = data['name']
        if 'value' in data:
            logic.value = data['value']
        if 'type' in data:
            logic.type = data['type']
        if 'is_active' in data:
            logic.is_active = data['is_active']
        
        logic.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify(logic_to_dict(logic))
    except Exception as e:
        app.logger.error(f"Error updating device logic: {e}")
        db.session.rollback()
        return internal_error(e)

@app.route('/api/v1/devices/<device_id>/logic/<logic_id>', methods=['DELETE'])
def delete_device_logic(device_id, logic_id):
    try:
        logic = DeviceCustomLogic.query.filter_by(
            logic_config_id=logic_id, 
            device_id=device_id
        ).first_or_404()
        
        db.session.delete(logic)
        db.session.commit()
        
        return '', 204
    except Exception as e:
        app.logger.error(f"Error deleting device logic: {e}")
        db.session.rollback()
        return internal_error(e)


@app.route('/api/v1/devices/<device_id>/telemetry', methods=['GET'])
def get_device_telemetry(device_id):
    try:
        limit = request.args.get('limit', 20, type=int)
        
        if limit < 1 or limit > 100:
            limit = 20
        
        telemetry_list = []
        

        cached_telemetry = get_cached_telemetry(device_id)
        if cached_telemetry:
            telemetry_list.append(cached_telemetry)
            limit -= 1
        

        if limit > 0:
            telemetry_data = Telemetry.query.filter_by(device_id=device_id)\
                .order_by(Telemetry.created_at.desc())\
                .limit(limit)\
                .all()
            
            telemetry_list.extend([telemetry_to_dict(t) for t in telemetry_data])
        
        return jsonify(telemetry_list)
    except Exception as e:
        app.logger.error(f"Error getting device telemetry: {e}")
        return internal_error(e)


@app.route('/api/v1/devices/<device_id>/commands', methods=['POST'])
def send_device_command(device_id):
    try:
        data = request.get_json()
        
        if not data or not all(key in data for key in ['command_type', 'parameters']):
            return bad_request('Missing required fields: command_type, parameters')
        

        iot_command = {
            'command': data['command_type'],
            'parameters': data['parameters']
        }
        

        success = send_command_to_iot_gateway(device_id, iot_command)
        
        if success:
            command_id = str(uuid.uuid4())
            return jsonify({
                'command_id': command_id,
                'status': 'accepted'
            }), 202
        else:
            return jsonify({
                'error': 'GATEWAY_ERROR',
                'message': 'Не удалось отправить команду на IoT Gateway'
            }), 500
            
    except Exception as e:
        app.logger.error(f"Error sending device command: {e}")
        return internal_error(e)


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'device-management-api'})


def init_db():
    with app.app_context():
        db.create_all()


init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, debug=app.config['DEBUG']) 