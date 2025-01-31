# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /property_street_backend

# Install system-level dependencies
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt into the container
COPY ./requirements.txt /property_street_backend/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /property_street_backend/requirements.txt

# Copy the entire backend folder into the container
COPY ./property_street_backend /property_street_backend

# Expose the port FastAPI will use
EXPOSE 80

# Use uvicorn to start the FastAPI application
CMD ["fastapi", "run", "app/main.py", "--port", "80"]