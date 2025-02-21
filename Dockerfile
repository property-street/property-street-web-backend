# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Install system-level dependencies
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt into the container
COPY ./requirements.txt /app/property_street_backend/requirements.txt

# Copy Alembic configuration and migration files
COPY alembic.ini .
COPY ./alembic ./alembic

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/property_street_backend/requirements.txt

# Copy the entire backend folder into the container
COPY . /app/property_street_backend

# Use uvicorn to start the FastAPI application
CMD ["sh", "-c", "alembic upgrade head && fastapi run property_street_backend/app/main.py --port 8080"]