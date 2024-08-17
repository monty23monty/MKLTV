# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install PostgreSQL client
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

# Copy the entrypoint script
COPY docker-entrypoint.sh /app/docker-entrypoint.sh

# Make the script executable
RUN chmod +x /app/docker-entrypoint.sh

# Copy project files
COPY . .

# Script to run the appropriate service
ENTRYPOINT ["bash", "/app/docker-entrypoint.sh"]
