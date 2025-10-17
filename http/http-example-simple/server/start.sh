#!/bin/bash
set -e

echo "Starting Gunicorn..."
gunicorn --config /app/gunicorn.conf.py main:app &
GUNICORN_PID=$!

echo "Starting Nginx..."
nginx -g 'daemon off;' &
NGINX_PID=$!

# Graceful shutdown
shutdown() {
    echo "Shutting down..."
    kill -SIGTERM $GUNICORN_PID
    kill -SIGQUIT $NGINX_PID
    wait $GUNICORN_PID
    wait $NGINX_PID
    echo "Shutdown complete."
}

trap shutdown SIGTERM SIGINT

# Wait forever
wait $GUNICORN_PID