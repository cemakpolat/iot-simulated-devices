# server/Dockerfile
FROM python:3.10-slim-buster

WORKDIR /app

# Install system dependencies that might be needed by Python packages (e.g., cryptography)
# This is usually not strictly necessary for basic pip install but can help resolve build issues.
# Uncomment and add if you encounter issues during `pip install` related to native libraries.
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     libssl-dev \
#     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code from server/app to /app/app in the container
COPY ./server/app /app/app

# Create a dedicated directory for ML models and logs inside the container
RUN mkdir -p /app/models /app/logs
# Copy any pre-trained models (if they exist) into the container
# This directory should be mounted as a volume in docker-compose.yml for persistence
COPY models /app/models

# Expose ports that the server might use.
# 8000 for FastAPI (REST API - to be implemented in later phases)
# 8001 for WebSockets (Dashboard communication - to be implemented in later phases)
EXPOSE 8000
EXPOSE 8001

# Command to run the AI controller application's main control loop.
# For now, we'll run `app.main.py`. In later phases, this might switch to `uvicorn`.
CMD ["python", "app/main.py"]