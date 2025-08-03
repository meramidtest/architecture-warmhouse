#!/bin/bash

echo "Starting IoT Gateway MVP..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed."
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Run the application with telemetry worker
echo "Starting IoT Gateway with API and Telemetry Worker..."
python start_with_worker.py 