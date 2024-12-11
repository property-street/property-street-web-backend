#!/bin/sh

# Run Alembic migrations
echo "Running Alembic migrations..."
alembic -c /property_street_backend/alembic.ini upgrade head


# Start the FastAPI application using `fastapi run`
echo "Starting FastAPI..."
exec fastapi run app/main.py --port 80
