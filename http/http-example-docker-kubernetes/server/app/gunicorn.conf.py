# Gunicorn config for production

import os

bind = "0.0.0.0:5000"
workers = int(os.getenv("GUNICORN_WORKERS", 4))
threads = int(os.getenv("GUNICORN_THREADS", 2))
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
capture_output = True