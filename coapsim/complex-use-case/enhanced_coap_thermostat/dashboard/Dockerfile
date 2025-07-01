# dashboard/Dockerfile
FROM python:3.10-slim-buster


WORKDIR /app

COPY requirements.txt .
# Install Flask, Flask-SocketIO, etc.
RUN pip install --no-cache-dir -r requirements.txt

# Copy dashboard application code
COPY ./dashboard/app.py /app/app.py
COPY ./dashboard/static /app/static
COPY ./dashboard/templates /app/templates

# Expose the Flask app port
EXPOSE 5000
ENV PYTHONUNBUFFERED=1
# Command to run the Flask dashboard application using Gunicorn for production or Flask development server for debug
# For development, simpler: CMD ["python", "app.py"]
# For production: CMD ["gunicorn", "--worker-class", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "-w", "1", "-b", "0.0.0.0:5000", "app:app"]
# Using Flask-SocketIO's own run method which handles websockets directly with gevent/eventlet
CMD ["python", "app.py"]