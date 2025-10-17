FROM python:3.9-slim

# Install netcat (nc), which is needed by the wait script
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app

# Copy the wait script
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

# REMOVE the ENTRYPOINT. We will define the full command in Kubernetes.
# ENTRYPOINT ["/wait-for-it.sh", "server:80"]

# The CMD remains the default command to be run.
CMD ["python", "-m", "main"]