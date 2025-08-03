#!/usr/bin/env python3

import requests
import sys
import json

def check_health(base_url="http://localhost:8081"):
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Service is healthy: {data}")
            return True
        else:
            print(f"❌ Service returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to service at {base_url}")
        return False
    except Exception as e:
        print(f"❌ Error checking health: {e}")
        return False

if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8081"
    if check_health(base_url):
        sys.exit(0)
    else:
        sys.exit(1) 