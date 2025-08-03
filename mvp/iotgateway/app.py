from flask import Flask, request, jsonify
import uuid
import logging
from models import Database, DeviceManager


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


db = Database()
device_manager = DeviceManager(db)

@app.route('/devices', methods=['POST'])
def register_device():
    try:
        data = request.get_json()
        

        if not data or not all(key in data for key in ['device_id', 'name', 'type']):
            return jsonify({'error': 'Missing required fields: device_id, name, type'}), 400
        

        try:
            uuid.UUID(data['device_id'])
        except ValueError:
            return jsonify({'error': 'device_id must be a valid UUID'}), 400
        

        if len(data['name']) > 255:
            return jsonify({'error': 'name must be 255 characters or less'}), 400
        
        if len(data['type']) > 100:
            return jsonify({'error': 'type must be 100 characters or less'}), 400
        

        response = device_manager.register_device(
            device_id=data['device_id'],
            name=data['name'],
            device_type=data['type'],
            serial_id=data.get('serial_id')
        )
        
        logger.info(f"Device registered: {data['device_id']}")
        return jsonify(response), 201
        
    except ValueError as e:
        if "already exists" in str(e):
            return jsonify({'error': 'Device already exists'}), 409
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error registering device: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/devices/<device_id>/commands', methods=['POST'])
def send_command(device_id):
    try:

        try:
            uuid.UUID(device_id)
        except ValueError:
            return jsonify({'error': 'device_id must be a valid UUID'}), 400
        
        data = request.get_json()
        

        if not data or 'command' not in data:
            return jsonify({'error': 'Missing required field: command'}), 400
        

        success = device_manager.send_command(
            device_id=device_id,
            command=data['command'],
            parameters=data.get('parameters')
        )
        
        if not success:
            return jsonify({'error': 'Device not found'}), 404
        
        logger.info(f"Command sent to device {device_id}: {data['command']}")
        return jsonify({'message': 'Command sent successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error sending command to device {device_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/devices/<device_id>/status', methods=['GET'])
def get_device_status(device_id):
    try:

        try:
            uuid.UUID(device_id)
        except ValueError:
            return jsonify({'error': 'device_id must be a valid UUID'}), 400
        
        status = device_manager.get_device_status(device_id)
        
        if not status:
            return jsonify({'error': 'Device not found'}), 404
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Error getting device status {device_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'IoT Gateway'}), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405

if __name__ == '__main__':
    logger.info("Starting IoT Gateway API server...")
    app.run(host='0.0.0.0', port=8080, debug=True) 