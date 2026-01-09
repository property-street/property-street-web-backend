#!/bin/bash

set -e

echo "Starting Celery worker..."
celery -A property_street_backend.app.celery_config worker \
  --pool=solo \
  --loglevel=info \
  -E &

echo "Starting Celery beat..."
celery -A property_street_backend.app.celery_config beat \
  --loglevel=info &

echo "Starting FastAPI..."
uvicorn property_street_backend.app.main:app \
  --reload \
  --host 0.0.0.0 \
  --port 8001
