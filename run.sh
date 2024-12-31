#!/bin/bash

# Kill any existing Redis server
pkill redis-server

# Kill any existing uvicorn process
pkill uvicorn

# Create and activate virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
source venv/bin/activate
echo "Installing dependencies..."
pip install -r requirements.txt

# Start Redis server in background
echo "Starting Redis server..."
redis-server redis.conf &
sleep 2  # Wait for Redis to start

# Start the FastAPI application
echo "Starting FastAPI application..."
uvicorn app:app --reload --host 0.0.0.0 --port 8000 