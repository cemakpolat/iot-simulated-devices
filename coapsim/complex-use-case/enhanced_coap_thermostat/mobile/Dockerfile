# mobile/Dockerfile
FROM python:3.10-slim-buster

WORKDIR /app

COPY requirements.txt .
# Install FastAPI, uvicorn, pyjwt, firebase-admin etc.
RUN pip install --no-cache-dir -r requirements.txt

# Copy mobile API code
COPY ./mobile /app/mobile
# Copy certs directory, potentially needed for Firebase Admin SDK or other secrets
# This should also be mounted as a volume if containing sensitive files
COPY certs /app/certs

EXPOSE 8000

# Command to run the FastAPI mobile API
# The mobile_endpoints.py exposes the `app` instance.
CMD ["uvicorn", "mobile.api.mobile_endpoints:app", "--host", "0.0.0.0", "--port", "8000"]