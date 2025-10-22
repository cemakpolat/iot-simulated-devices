#!/bin/sh
set -e

# Start Nginx in the background
echo "Starting Nginx..."
nginx

# Start Gunicorn in the foreground
echo "Starting Gunicorn..."
exec gunicorn --config gunicorn.conf.py main:app
