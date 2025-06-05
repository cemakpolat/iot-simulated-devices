# Use a slim Python base image
FROM python:3.9-slim-buster
ENV PYTHONUNBUFFERED=1
# Set the working directory in the container
WORKDIR /app

# Copy just the requirements file first to optimize Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your server application code
COPY . .

# Expose OPC UA ports (optional, for documentation/firewall)
EXPOSE 4840
EXPOSE 4843

# Command to run the server
# It will automatically try to setup TLS based on its logic and presence of certs.
CMD ["python", "server.py"]