#!/bin/sh
# Start Uvicorn processes
echo "Starting Consumers."
exec uv run manage.py runworker firebase-notify telegram-notify