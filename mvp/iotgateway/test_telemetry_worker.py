#!/usr/bin/env python3
import requests
import json
import uuid
import time
import sys


GATEWAY_URL = "http://localhost:8080"
TEST_DEVICES = [
    {
        "device_id": str(uuid.uuid4()),
        "name": "Living Room Temperature Sensor",
        "type": "temperature_sensor",
        "serial_id": "TEMP001"
    },
    {
        "device_id": str(uuid.uuid4()),
        "name": "Smart Light Bulb",
        "type": "smart_light",
        "serial_id": "LIGHT001"
    },
    {
        "device_id": str(uuid.uuid4()),
        "name": "Front Door Lock",
        "type": "smart_lock",
        "serial_id": "LOCK001"
    },
    {
        "device_id": str(uuid.uuid4()),
        "name": "Security Camera",
        "type": "security_camera",
        "serial_id": "CAM001"
    }
]

def test_health_check():
    try:
        response = requests.get(f"{GATEWAY_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ IoT Gateway is running and healthy")
            return True
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to connect to IoT Gateway: {e}")
        print("Make sure the IoT Gateway is running on http://localhost:8080")
        return False

def register_test_devices():
    print("\n📋 Registering test devices...")
    
    registered_devices = []
    
    for device in TEST_DEVICES:
        try:
            response = requests.post(
                f"{GATEWAY_URL}/devices",
                headers={'Content-Type': 'application/json'},
                json=device,
                timeout=5
            )
            
            if response.status_code == 201:
                print(f"✅ Registered device: {device['name']} ({device['device_id']})")
                registered_devices.append(device)
            elif response.status_code == 409:
                print(f"⚠️  Device already exists: {device['name']} ({device['device_id']})")
                registered_devices.append(device)
            else:
                print(f"❌ Failed to register device {device['name']}: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error registering device {device['name']}: {e}")
    
    return registered_devices

def check_device_status(device_id, device_name):
    try:
        response = requests.get(f"{GATEWAY_URL}/devices/{device_id}/status", timeout=5)
        
        if response.status_code == 200:
            status_data = response.json()
            print(f"📊 {device_name}:")
            print(f"   Status: {status_data.get('status', 'unknown')}")
            print(f"   Last seen: {status_data.get('last_seen', 'never')}")
            
            telemetry = status_data.get('telemetry', {})
            if telemetry:
                print(f"   Telemetry: {json.dumps(telemetry, indent=6)}")
            else:
                print(f"   Telemetry: No data available")
            print()
            return True
        else:
            print(f"❌ Failed to get status for {device_name}: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error checking device {device_name}: {e}")
        return False

def monitor_telemetry(registered_devices, cycles=3):
    print(f"\n🔄 Monitoring telemetry for {cycles} cycles (each cycle = ~5 seconds)")
    print("The telemetry worker should update device data every 5 seconds...")
    
    for cycle in range(cycles):
        print(f"\n--- Cycle {cycle + 1}/{cycles} ---")
        
        for device in registered_devices:
            check_device_status(device['device_id'], device['name'])
        
        if cycle < cycles - 1:
            print("⏳ Waiting for next telemetry update...")
            time.sleep(6)

def main():
    print("🚀 IoT Gateway Telemetry Worker Test")
    print("=" * 50)
    

    if not test_health_check():
        print("\n❌ Cannot proceed without a running IoT Gateway")
        print("Please start the IoT Gateway using: python start_with_worker.py")
        sys.exit(1)
    

    registered_devices = register_test_devices()
    
    if not registered_devices:
        print("\n❌ No devices were registered successfully")
        sys.exit(1)
    
    print(f"\n✅ Successfully registered {len(registered_devices)} devices")
    

    print("\n⏳ Waiting 10 seconds for telemetry worker to start generating data...")
    time.sleep(10)
    

    monitor_telemetry(registered_devices)
    
    print("\n🎉 Test completed!")
    print("\nWhat you should see:")
    print("1. ✅ All devices registered successfully")
    print("2. 📊 Each device should have telemetry data updated every ~5 seconds")
    print("3. 🔄 Telemetry data should change between cycles")
    print("4. 📈 Different device types should have different telemetry fields")
    print("\nIf you see telemetry data changing between cycles, the worker is functioning correctly!")
    
    print(f"\n💡 You can also check RabbitMQ management interface to see telemetry messages")
    print(f"   being published to the 'telemetry' topic")

if __name__ == '__main__':
    main() 