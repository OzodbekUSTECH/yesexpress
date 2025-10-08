#!/bin/sh
# Start Uvicorn processes
echo "Starting Operator Daphne."
exec uv run daphne -b 0.0.0.0 -p 4547 tuktuk.asgi:application
