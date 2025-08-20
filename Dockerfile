# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Install system-level dependencies
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first (this rarely changes)
COPY ./requirements.txt /app/requirements.txt

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

# Now copy the full source (code changes don't affect dependency cache)
COPY . /app/property_street_backend

# Copy Alembic configuration and migration files
COPY alembic.ini ./alembic.ini
COPY ./alembic ./alembic

EXPOSE 8001

# Run migrations and start the app
CMD ["sh", "-c", "alembic upgrade head && uvicorn property_street_backend.app.main:app --host 0.0.0.0 --port 8001"]
