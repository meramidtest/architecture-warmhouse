#!/bin/bash

echo "Testing Device Management Worker"
sleep 5

# Test device events
DEVICE_ID=$(python3 -c "import uuid; print(str(uuid.uuid4()))")
echo "Using test device ID: $DEVICE_ID"

# Send device event
python3 -c "
import json
import pika
import sys
from datetime import datetime

device_id = '$DEVICE_ID'
event_data = {
    'device_id': device_id,
    'event_type': 'registered',
    'timestamp': datetime.now().isoformat(),
    'device_data': {
        'device_id': device_id,
        'serial_id': 'SN-' + device_id[:8],
        'name': 'Test Smart Thermostat',
        'type': 'test_device',
        'status': 'online',
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
}

try:
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='devices', durable=True)
    channel.basic_publish(
        exchange='',
        routing_key='devices',
        body=json.dumps(event_data),
        properties=pika.BasicProperties(delivery_mode=2)
    )
    print('Sent device registered event')
    connection.close()
except Exception as e:
    print(f'Failed to send event: {e}')
"

echo "Waiting for worker to process event..."
sleep 3

# Check if device exists via API
echo "Checking if device exists in management API..."
RESPONSE=$(curl -s -H "Content-Type: application/json" -H "User-ID: test-user-123" \
  "http://localhost:8082/api/v1/devices/$DEVICE_ID/logic")

if echo "$RESPONSE" | grep -q '\[\]'; then
    echo "SUCCESS: Device exists in management system"
else
    echo "FAIL: Device might not exist"
    echo "Response: $RESPONSE"
fi

# Check worker logs
echo ""
echo "Recent worker logs:"
docker-compose logs device-management-worker --tail=5

echo ""
echo "Test completed!" 