#!/usr/bin/env python3

import requests
import json
import uuid

BASE_URL = "http://localhost:8081/api/v1"
HEADERS = {
    "Content-Type": "application/json",
    "User-ID": "test-user-123"
}

def test_health():
    print("🔍 Testing health endpoint...")
    response = requests.get("http://localhost:8081/health")
    print(f"Health check: {response.status_code} - {response.json()}")
    return response.status_code == 200

def test_device_logic(device_id):
    print(f"\n🔍 Testing device logic endpoints for device {device_id}...")
    

    response = requests.get(f"{BASE_URL}/devices/{device_id}/logic", headers=HEADERS)
    print(f"GET logic: {response.status_code}")
    if response.status_code == 200:
        print(f"Existing logic: {response.json()}")
    

    new_logic = {
        "name": "Temperature Control",
        "value": {
            "trigger": "temperature < 18",
            "action": "set_temperature(22)"
        },
        "type": "temperature_control",
        "is_active": True
    }
    
    response = requests.post(
        f"{BASE_URL}/devices/{device_id}/logic", 
        json=new_logic, 
        headers=HEADERS
    )
    print(f"POST logic: {response.status_code}")
    if response.status_code == 201:
        logic_data = response.json()
        logic_id = logic_data['logic_config_id']
        print(f"Created logic: {logic_id}")
        

        update_data = {
            "name": "Updated Temperature Control",
            "is_active": False
        }
        response = requests.put(
            f"{BASE_URL}/devices/{device_id}/logic/{logic_id}",
            json=update_data,
            headers=HEADERS
        )
        print(f"PUT logic: {response.status_code}")
        

        response = requests.get(f"{BASE_URL}/devices/{device_id}/logic", headers=HEADERS)
        if response.status_code == 200:
            print(f"Updated logic: {response.json()}")
        

        response = requests.delete(
            f"{BASE_URL}/devices/{device_id}/logic/{logic_id}",
            headers=HEADERS
        )
        print(f"DELETE logic: {response.status_code}")
    
    return True

def test_device_telemetry(device_id):
    print(f"\n🔍 Testing telemetry endpoint for device {device_id}...")
    
    response = requests.get(
        f"{BASE_URL}/devices/{device_id}/telemetry?limit=10", 
        headers=HEADERS
    )
    print(f"GET telemetry: {response.status_code}")
    if response.status_code == 200:
        telemetry = response.json()
        print(f"Telemetry data: {len(telemetry)} records")
    
    return True

def test_device_commands(device_id):
    print(f"\n🔍 Testing commands endpoint for device {device_id}...")
    
    command = {
        "command_type": "set_temperature",
        "parameters": {
            "temperature": 23
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/devices/{device_id}/commands",
        json=command,
        headers=HEADERS
    )
    print(f"POST command: {response.status_code}")
    if response.status_code == 202:
        result = response.json()
        print(f"Command result: {result}")
    elif response.status_code == 500:

        print("Expected error: IoT Gateway not available")
    
    return True

def test_get_all_devices():
    print(f"\n🔍 Testing get all devices endpoint...")
    

    response = requests.get(f"{BASE_URL}/devices", headers=HEADERS)
    print(f"GET all devices: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Found {data['total_count']} devices")
        print(f"Returned {len(data['devices'])} devices in this page")
        print(f"Has more: {data['has_more']}")
    

    response = requests.get(f"{BASE_URL}/devices?limit=5&offset=0", headers=HEADERS)
    print(f"GET devices with pagination: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Pagination test - limit: {data['limit']}, offset: {data['offset']}")
    
    return True

def test_get_device_by_id(device_id):
    print(f"\n🔍 Testing get device by ID endpoint for {device_id}...")
    
    response = requests.get(f"{BASE_URL}/devices/{device_id}", headers=HEADERS)
    print(f"GET device by ID: {response.status_code}")
    if response.status_code == 200:
        device = response.json()
        print(f"Device found: {device['name']} (type: {device['type']})")
    elif response.status_code == 404:
        print("Device not found (expected if device doesn't exist)")
    
    return True

def main():
    print("🚀 Starting Device Management API Tests")
    

    if not test_health():
        print("❌ Service is not healthy, stopping tests")
        return
    

    test_get_all_devices()
    

    test_device_id = str(uuid.uuid4())
    print(f"\n📱 Using test device ID: {test_device_id}")
    print("Note: Some tests may fail if the device doesn't exist in the database")
    
    try:

        test_get_device_by_id(test_device_id)
        test_device_logic(test_device_id)
        test_device_telemetry(test_device_id)
        test_device_commands(test_device_id)
        

        print(f"\n🔍 Testing get device after creating through logic...")
        test_get_device_by_id(test_device_id)
        
        print("\n✅ All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to the API. Make sure the service is running on localhost:8081")
    except Exception as e:
        print(f"❌ Test error: {e}")

if __name__ == "__main__":
    main() 