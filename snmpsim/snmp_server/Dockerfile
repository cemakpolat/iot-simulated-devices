FROM python:3.9-slim

# Install system dependencies (GCC and required libraries)
# Psutil requires gcc
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* \

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py /app/snmp_server.py

CMD ["python", "/app/snmp_server.py"]
