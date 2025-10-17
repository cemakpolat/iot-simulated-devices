# # Use a newer Python image based on Debian Bookworm to get modern libpq
FROM python:3.11-slim-bookworm

# Install Nginx and all necessary build dependencies, including netcat
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends nginx curl gcc libpq-dev build-essential netcat-openbsd; \
    rm -rf /var/lib/apt/lists/*; \
    # Create nginx user/group if not present
    if ! getent passwd nginx >/dev/null; then \
        addgroup --system --gid 101 nginx; \
        adduser --system --disabled-login --ingroup nginx --no-create-home --home /nonexistent --gecos "nginx user" --shell /bin/false --uid 101 nginx; \
    fi

# Set the working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application and config files from their correct locations
COPY app /app
COPY nginx.conf /etc/nginx/nginx.conf
COPY app/gunicorn.conf.py /app/

# Fix log and run dir permissions
RUN mkdir -p /var/log/nginx /var/lib/nginx && \
    chown -R nginx:nginx /var/log/nginx /var/lib/nginx

# Expose the port Nginx will listen on
EXPOSE 80

# Copy and make utility scripts executable
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh
COPY start.sh /start.sh
RUN chmod +x /start.sh

# The CMD will be overridden in docker-compose for the worker
CMD ["/start.sh"]
