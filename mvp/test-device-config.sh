#!/bin/bash

# Test script for device configuration service
set -e

BASE_URL="http://localhost:8081/api/v1"
USER_ID="$(uuidgen)"

echo "🚀 Testing Device Configuration Service"
echo "User ID: $USER_ID"
echo "Base URL: $BASE_URL"
echo ""

# Check health
echo "1️⃣ Checking service health..."
curl -s "http://localhost:8081/health" | jq .
echo ""

# Create a location
echo "2️⃣ Creating a location..."
LOCATION_RESPONSE=$(curl -s -X POST "$BASE_URL/locations" \
  -H "Content-Type: application/json" \
  -H "User-ID: $USER_ID" \
  -d '{"name": "Test Home"}')

echo $LOCATION_RESPONSE | jq .
LOCATION_ID=$(echo $LOCATION_RESPONSE | jq -r '.location_id')
echo "Location ID: $LOCATION_ID"
echo ""

# List locations
echo "3️⃣ Listing locations..."
curl -s -X GET "$BASE_URL/locations" \
  -H "User-ID: $USER_ID" | jq .
echo ""

# Register a device
echo "4️⃣ Registering a device..."
DEVICE_RESPONSE=$(curl -s -X POST "$BASE_URL/devices" \
  -H "Content-Type: application/json" \
  -H "User-ID: $USER_ID" \
  -d "{
    \"location_id\": \"$LOCATION_ID\",
    \"serial_id\": \"TEST-$(date +%s)\",
    \"name\": \"Test Thermostat\",
    \"type\": \"thermostat\"
  }")

echo $DEVICE_RESPONSE | jq .
DEVICE_ID=$(echo $DEVICE_RESPONSE | jq -r '.device_id')
echo "Device ID: $DEVICE_ID"
echo ""

# List devices
echo "5️⃣ Listing devices..."
curl -s -X GET "$BASE_URL/devices" \
  -H "User-ID: $USER_ID" | jq .
echo ""

# Add device configuration
echo "6️⃣ Adding device configuration..."
CONFIG_RESPONSE=$(curl -s -X POST "$BASE_URL/devices/$DEVICE_ID/configurations" \
  -H "Content-Type: application/json" \
  -H "User-ID: $USER_ID" \
  -d '{
    "config_name": "temperature_threshold",
    "config_value": "22.5",
    "config_type": "number"
  }')

echo $CONFIG_RESPONSE | jq .
echo ""

# List device configurations
echo "7️⃣ Listing device configurations..."
curl -s -X GET "$BASE_URL/devices/$DEVICE_ID/configurations" \
  -H "User-ID: $USER_ID" | jq .
echo ""

echo "✅ All tests completed successfully!"
echo ""
echo "🔗 Useful URLs:"
echo "  - Device Configuration API: http://localhost:8081"
echo "  - IoT Gateway API: http://localhost:8080"
echo "  - RabbitMQ Management: http://localhost:15672 (guest/guest)"
echo "  - PostgreSQL: localhost:5432 (postgres/postgres)" 