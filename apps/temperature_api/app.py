from flask import Flask, jsonify, request
from datetime import datetime
import random
import os
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.before_request
def log_request_info():
    """Log information about each incoming request"""
    logger.info(f"REQUEST: {request.method} {request.url} - IP: {request.remote_addr}")
    if request.is_json and request.get_json():
        logger.info(f"REQUEST BODY: {request.get_json()}")

@app.after_request
def log_response_info(response):
    """Log information about each outgoing response"""
    logger.info(f"RESPONSE: {response.status_code} - {request.method} {request.url}")
    return response

def generate_temperature_response(sensor_id=None, location=None, sensor_type="DHT22"):
    """Generate a random temperature response"""
    return {
        'value': round(random.uniform(15.0, 35.0), 2),
        'unit': '°C',
        'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'location': location or f"Location for {sensor_id}",
        'status': 'active',
        'sensor_id': sensor_id or f"sensor_{random.randint(1, 999):03d}",
        'sensor_type': sensor_type,
        'description': f"Temperature reading from {sensor_type} sensor"
    }

# Temperature API endpoints
@app.route('/temperature', methods=['GET'])
def get_temperature_by_location():
    """Get temperature data by location"""
    location = request.args.get('location')
    
    if not location:
        return jsonify({"error": "Location parameter is required"}), 400
    
    # Generate random temperature response for the location
    return jsonify(generate_temperature_response(location=location))

@app.route('/temperature/<sensor_id>', methods=['GET'])
def get_temperature_by_sensor(sensor_id):
    """Get temperature data by sensor ID"""
    # Generate random temperature response for the sensor
    return jsonify(generate_temperature_response(sensor_id=sensor_id))

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')})

@app.route('/debug/routes', methods=['GET'])
def list_routes():
    """Debug endpoint to list all registered routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': str(rule)
        })
    return jsonify(routes)

if __name__ == '__main__':
    print("Starting Flask app...")
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule} -> {rule.endpoint} ({list(rule.methods)})")
    app.run(debug=True, host='0.0.0.0', port=5000) 