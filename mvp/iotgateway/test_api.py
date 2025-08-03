#!/usr/bin/env python3

import requests
import json
import uuid
import time

BASE_URL = "http://localhost:8080"

def test_health():
    print("Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health check: {response.status_code} - {response.json()}")
    return response.status_code == 200

def test_register_device():
    print("\nTesting device registration...")
    
    device_data = {
        "device_id": str(uuid.uuid4()),
        "name": "Test Thermostat",
        "type": "thermostat",
        "serial_id": "TEST001"
    }
    
    response = requests.post(
        f"{BASE_URL}/devices",
        headers={"Content-Type": "application/json"},
        json=device_data
    )
    
    print(f"Register device: {response.status_code}")
    if response.status_code == 201:
        print(f"Response: {response.json()}")
        return device_data["device_id"]
    else:
        print(f"Error: {response.json()}")
        return None

def test_get_device_status(device_id):
    print(f"\nTesting device status for {device_id}...")
    
    response = requests.get(f"{BASE_URL}/devices/{device_id}/status")
    print(f"Get device status: {response.status_code}")
    
    if response.status_code == 200:
        print(f"Response: {response.json()}")
        return True
    else:
        print(f"Error: {response.json()}")
        return False

def test_send_command(device_id):
    print(f"\nTesting send command to {device_id}...")
    
    command_data = {
        "command": "set_temperature",
        "parameters": {
            "temperature": 22.5,
            "unit": "celsius"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/devices/{device_id}/commands",
        headers={"Content-Type": "application/json"},
        json=command_data
    )
    
    print(f"Send command: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
        return True
    else:
        print(f"Error: {response.json()}")
        return False

def test_error_cases():
    print("\nTesting error cases...")
    

    response = requests.get(f"{BASE_URL}/devices/invalid-uuid/status")
    print(f"Invalid UUID: {response.status_code} - {response.json()}")
    

    fake_uuid = str(uuid.uuid4())
    response = requests.get(f"{BASE_URL}/devices/{fake_uuid}/status")
    print(f"Non-existent device: {response.status_code} - {response.json()}")
    

    response = requests.post(
        f"{BASE_URL}/devices",
        headers={"Content-Type": "application/json"},
        json={"name": "Incomplete Device"}
    )
    print(f"Missing fields: {response.status_code} - {response.json()}")

def main():
    print("IoT Gateway API Test Suite")
    print("=" * 40)
    
    try:

        if not test_health():
            print("Health check failed. Is the server running?")
            return
        

        device_id = test_register_device()
        if not device_id:
            print("Device registration failed")
            return
        

        time.sleep(0.1)
        

        test_get_device_status(device_id)
        

        test_send_command(device_id)
        

        test_error_cases()
        
        print("\n" + "=" * 40)
        print("All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to the server. Make sure it's running on http://localhost:8080")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main() 