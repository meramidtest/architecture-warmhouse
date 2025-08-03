#!/bin/bash

# Test script for Device Management API integration
echo "🚀 Testing Device Management API integration"

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Test health endpoints
echo "🔍 Testing service health..."

echo "Testing IoT Gateway health:"
curl -s http://localhost:8080/health || echo "❌ IoT Gateway not responding"

echo -e "\nTesting Device Management API health:"
curl -s http://localhost:8082/health || echo "❌ Device Management API not responding"

echo -e "\nTesting Device Configuration API health:"
curl -s http://localhost:8081/health || echo "❌ Device Configuration API not responding"

# Test device management API with a sample device
echo -e "\n📱 Testing Device Management API endpoints..."

# Generate a test device ID
DEVICE_ID=$(python3 -c "import uuid; print(str(uuid.uuid4()))")
echo "Using test device ID: $DEVICE_ID"

# Headers for requests
CONTENT_TYPE="Content-Type: application/json"
USER_ID="User-ID: test-user-123"

echo -e "\n1. Testing GET device logic (should return empty array):"
curl -s -H "$CONTENT_TYPE" -H "$USER_ID" "http://localhost:8082/api/v1/devices/$DEVICE_ID/logic"

echo -e "\n\n2. Testing device telemetry (should return empty array):"
curl -s -H "$CONTENT_TYPE" -H "$USER_ID" "http://localhost:8082/api/v1/devices/$DEVICE_ID/telemetry?limit=5"

echo -e "\n\n3. Testing device command (should attempt to contact IoT Gateway):"
curl -s -H "$CONTENT_TYPE" -H "$USER_ID" -X POST "http://localhost:8082/api/v1/devices/$DEVICE_ID/commands" \
  -d '{"command_type": "set_temperature", "parameters": {"temperature": 23}}'

echo -e "\n\n4. Testing create device logic:"
LOGIC_RESPONSE=$(curl -s -H "$CONTENT_TYPE" -H "$USER_ID" -X POST "http://localhost:8082/api/v1/devices/$DEVICE_ID/logic" \
  -d '{"name": "Test Temperature Control", "value": {"trigger": "temperature < 18", "action": "set_temperature(22)"}, "type": "temperature_control", "is_active": true}')

echo $LOGIC_RESPONSE

# Extract logic ID from response if successful
LOGIC_ID=$(echo $LOGIC_RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('logic_config_id', ''))" 2>/dev/null)

if [ ! -z "$LOGIC_ID" ]; then
    echo -e "\n5. Testing update device logic:"
    curl -s -H "$CONTENT_TYPE" -H "$USER_ID" -X PUT "http://localhost:8082/api/v1/devices/$DEVICE_ID/logic/$LOGIC_ID" \
      -d '{"name": "Updated Test Logic", "is_active": false}'
    
    echo -e "\n\n6. Testing delete device logic:"
    curl -s -H "$CONTENT_TYPE" -H "$USER_ID" -X DELETE "http://localhost:8082/api/v1/devices/$DEVICE_ID/logic/$LOGIC_ID"
    
    echo -e "\n\n7. Verifying logic was deleted:"
    curl -s -H "$CONTENT_TYPE" -H "$USER_ID" "http://localhost:8082/api/v1/devices/$DEVICE_ID/logic"
else
    echo -e "\n❌ Could not create logic config, skipping update/delete tests"
fi

echo -e "\n\n✅ Device Management API tests completed!"
echo "📊 Check the responses above to verify everything is working correctly."

# Test service connectivity
echo -e "\n🔗 Testing service connectivity..."
echo "Device Management API → IoT Gateway communication:"

# Check if device management can reach iot gateway
if docker exec device-management-api python -c "import requests; print('✅ Can reach IoT Gateway' if requests.get('http://iot-gateway:8080/health', timeout=5).status_code == 200 else '❌ Cannot reach IoT Gateway')" 2>/dev/null; then
    echo "Internal network communication working!"
else
    echo "❌ Internal network communication issue"
fi

echo -e "\n🎉 Integration test completed!" 