#!/bin/bash

# Test script for Device Management Worker
echo "🧪 Testing Device Management Worker"

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 5

# Check RabbitMQ Management UI access
echo "🔍 Checking RabbitMQ..."
curl -s http://guest:guest@localhost:15672/api/overview | grep -q "rabbitmq_version" && echo "✅ RabbitMQ is accessible" || echo "❌ RabbitMQ not accessible"

# Check Redis (via Docker)
echo "🔍 Checking Redis..."
docker exec device-config-redis redis-cli ping 2>/dev/null | grep -q "PONG" && echo "✅ Redis is accessible" || echo "❌ Redis not accessible"

# Function to send a device event to RabbitMQ
send_device_event() {
    local event_type=$1
    local device_id=$2
    local device_name=$3
    
    echo "📤 Sending $event_type event for device: $device_id"
    
    # Create the event JSON
    cat <<EOF | python3 -c "
import json
import pika
import sys
from datetime import datetime

# Read JSON from stdin
event_data = {
    'device_id': '$device_id',
    'event_type': '$event_type',
    'timestamp': datetime.now().isoformat(),
    'device_data': {
        'device_id': '$device_id',
        'serial_id': 'SN-${device_id:0:8}',
        'name': '$device_name',
        'type': 'test_device',
        'status': 'online',
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
}

try:
    # Connect to RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    
    # Declare queue
    channel.queue_declare(queue='devices', durable=True)
    
    # Publish message
    channel.basic_publish(
        exchange='',
        routing_key='devices',
        body=json.dumps(event_data),
        properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
    )
    
    print(f'✅ Sent {event_data[\"event_type\"]} event for device {event_data[\"device_id\"]}')
    connection.close()
    
except Exception as e:
    print(f'❌ Failed to send event: {e}')
    sys.exit(1)
EOF
}

# Test device events
DEVICE_ID=$(python3 -c "import uuid; print(str(uuid.uuid4()))")
echo "🔧 Using test device ID: $DEVICE_ID"

# Send device registered event
send_device_event "registered" "$DEVICE_ID" "Test Smart Thermostat"

echo "⏳ Waiting for worker to process event..."
sleep 3

# Send device updated event
send_device_event "updated" "$DEVICE_ID" "Updated Smart Thermostat"

echo "⏳ Waiting for worker to process update..."
sleep 3

# Check if device was added to database via API
echo "🔍 Checking if device exists in management API..."
DEVICE_RESPONSE=$(curl -s -H "Content-Type: application/json" -H "User-ID: test-user-123" \
  "http://localhost:8082/api/v1/devices/$DEVICE_ID/logic")

if echo "$DEVICE_RESPONSE" | grep -q '\[\]'; then
    echo "✅ Device exists in management system"
else
    echo "❌ Device might not exist in management system"
    echo "Response: $DEVICE_RESPONSE"
fi

# Check Redis cache for device status
echo "🔍 Checking Redis cache for device status..."
CACHE_KEY="device:status:$DEVICE_ID"
CACHED_STATUS=$(docker exec device-config-redis redis-cli get "$CACHE_KEY" 2>/dev/null)

if [ ! -z "$CACHED_STATUS" ] && [ "$CACHED_STATUS" != "\(nil\)" ]; then
    echo "✅ Device status found in Redis cache"
    echo "Cached data: $CACHED_STATUS"
else
    echo "⚠️ No cached status found (expected if IoT Gateway doesn't have the device)"
fi

# Check for telemetry cache
echo "🔍 Checking Redis cache for telemetry..."
TELEMETRY_KEY="device:telemetry:latest:$DEVICE_ID"
CACHED_TELEMETRY=$(docker exec device-config-redis redis-cli get "$TELEMETRY_KEY" 2>/dev/null)

if [ ! -z "$CACHED_TELEMETRY" ] && [ "$CACHED_TELEMETRY" != "\(nil\)" ]; then
    echo "✅ Latest telemetry found in Redis cache"
    echo "Cached telemetry: $CACHED_TELEMETRY"
else
    echo "⚠️ No cached telemetry found (expected if no telemetry data from IoT Gateway)"
fi

# Check worker logs
echo "📋 Recent worker logs:"
docker-compose logs device-management-worker --tail=10 | grep "$DEVICE_ID" || echo "No recent logs found for test device"

echo "🎉 Worker test completed!"
echo ""
echo "📝 Summary:"
echo "- Device events were sent to RabbitMQ"
echo "- Worker should have processed the events"
echo "- Device should be in management database"
echo "- Cache entries depend on IoT Gateway response" 