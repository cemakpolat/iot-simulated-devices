# Use a slim Python base image
FROM python:3.9-slim-buster
ENV PYTHONUNBUFFERED=1
# Set the working directory in the container
WORKDIR /app

# Copy just the requirements file first to optimize Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your client application code
COPY . .

# Command to run the client
CMD ["python", "client.py"]