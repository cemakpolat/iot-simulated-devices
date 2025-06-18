# client/Dockerfile
FROM python:3.10-slim-buster

WORKDIR /app

# Install system dependencies for DTLS (if needed, e.g., libssl-dev)
# For aiocoap with DTLS, usually only requires Python cryptography, which is handled by pip
# Uncomment and add if you encounter issues with DTLS security dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./client/app /app/app

# Ensure certs directory exists for DTLS PSK/Certificates (if used)
# This directory should be mounted as a volume in docker-compose.yml
RUN mkdir -p /app/certs
# COPY certs /app/certs # Will be mounted by docker-compose

# Expose CoAP ports (UDP)
EXPOSE 5683/udp
EXPOSE 5684/udp

# Command to run the CoAP device application
CMD ["python", "app/main.py"]