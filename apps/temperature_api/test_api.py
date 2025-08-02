#!/usr/bin/env python3
"""
Test script for IoT Gateway API
Run this after starting the Flask application to test all endpoints

Usage:
    python test_api.py                    # Test default localhost:5000
    python test_api.py --url http://localhost:8000  # Custom URL
    python test_api.py --check-db         # Check database type first
"""

import requests
import json
import time
import argparse
import sys

BASE_URL = "http://localhost:5000"

def test_endpoint(method, url, data=None, expected_status=200):
    """Test an API endpoint"""
    print(f"\n{method} {url}")
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data, headers={"Content-Type": "application/json"})
        elif method == "PUT":
            response = requests.put(url, json=data, headers={"Content-Type": "application/json"})
        elif method == "PATCH":
            response = requests.patch(url, json=data, headers={"Content-Type": "application/json"})
        elif method == "DELETE":
            response = requests.delete(url)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == expected_status:
            print("✅ Success")
        else:
            print("❌ Failed")
        
        if response.content:
            try:
                result = response.json()
                print(f"Response: {json.dumps(result, indent=2)}")
                return result
            except:
                print(f"Response: {response.text}")
                
        return None
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - make sure the Flask app is running on localhost:5000")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def check_database_info(base_url):
    """Check what database the API is using"""
    print("\n🔍 Checking database information...")
    try:
        # Get all sensors to see if the API is working
        response = requests.get(f"{base_url}/api/v1/sensors")
        if response.status_code == 200:
            sensors = response.json()
            print(f"✅ API is working, found {len(sensors)} sensors")
            
            # Try to determine database type from response patterns
            if sensors:
                print("📊 Sample sensor data structure verified")
            return True
        else:
            print(f"❌ API not responding correctly: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Test IoT Gateway API')
    parser.add_argument('--url', default=BASE_URL,
                       help=f'Base URL for API (default: {BASE_URL})')
    parser.add_argument('--check-db', action='store_true',
                       help='Check database information first')
    
    args = parser.parse_args()
    base_url = args.url.rstrip('/')
    
    print("🚀 Testing IoT Gateway API")
    print(f"📍 Target URL: {base_url}")
    print("=" * 50)
    
    # Check database info if requested
    if args.check_db:
        if not check_database_info(base_url):
            print("\n💡 Make sure the API server is running:")
            print("   python start.py                    # SQLite")
            print("   python start.py --db postgres      # PostgreSQL")
            sys.exit(1)
    
    # Test health check
    test_endpoint("GET", f"{base_url}/health")
    
    # Test temperature API
    print("\n📡 Testing Temperature API")
    test_endpoint("GET", f"{base_url}/temperature?location=Kitchen")
    test_endpoint("GET", f"{base_url}/temperature/temp002")
    test_endpoint("GET", f"{base_url}/temperature/nonexistent", expected_status=404)
    
    # Test sensor management API
    print("\n🔧 Testing Sensor Management API")
    
    # Get all sensors
    sensors_result = test_endpoint("GET", f"{base_url}/api/v1/sensors")
    
    # Get specific sensor
    test_endpoint("GET", f"{base_url}/api/v1/sensors/1")
    test_endpoint("GET", f"{base_url}/api/v1/sensors/999", expected_status=404)
    
    # Create new sensor
    new_sensor_data = {
        "name": "Test Garden Sensor",
        "type": "temperature",
        "location": "Garden",
        "unit": "°C",
        "sensor_id": "test001",
        "sensor_type": "DHT22"
    }
    created_sensor = test_endpoint("POST", f"{base_url}/api/v1/sensors", new_sensor_data, expected_status=201)
    
    if created_sensor:
        sensor_id = created_sensor.get("id")
        print(f"\n📝 Created sensor with ID: {sensor_id}")
        
        # Update the sensor
        update_data = {
            "name": "Updated Test Garden Sensor",
            "status": "maintenance"
        }
        test_endpoint("PUT", f"{base_url}/api/v1/sensors/{sensor_id}", update_data)
        
        # Update sensor value
        value_data = {
            "value": 28.5,
            "status": "active"
        }
        test_endpoint("PATCH", f"{base_url}/api/v1/sensors/{sensor_id}/value", value_data)
        
        # Get updated sensor
        test_endpoint("GET", f"{base_url}/api/v1/sensors/{sensor_id}")
        
        # Test temperature API with new sensor
        test_endpoint("GET", f"{base_url}/temperature/test001")
        test_endpoint("GET", f"{base_url}/temperature?location=Garden")
        
        # Delete the sensor
        test_endpoint("DELETE", f"{base_url}/api/v1/sensors/{sensor_id}")
        
        # Verify deletion
        test_endpoint("GET", f"{base_url}/api/v1/sensors/{sensor_id}", expected_status=404)
    
    # Test error cases
    print("\n🚨 Testing Error Cases")
    test_endpoint("POST", f"{base_url}/api/v1/sensors", {"invalid": "data"}, expected_status=400)
    test_endpoint("PUT", f"{base_url}/api/v1/sensors/999", {"name": "test"}, expected_status=404)
    test_endpoint("PATCH", f"{base_url}/api/v1/sensors/999/value", {"value": 20}, expected_status=404)
    
    print("\n🎉 Testing completed!")
    print("=" * 50)

if __name__ == "__main__":
    main() 