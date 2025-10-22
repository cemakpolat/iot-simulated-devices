FROM python:3.9-slim

# Install Nginx and ensure 'nginx' user/group exist


RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends nginx curl; \
    rm -rf /var/lib/apt/lists/*; \
    # Create nginx user/group if not present (some slim images skip this)
    if ! getent passwd nginx >/dev/null; then \
        addgroup --system --gid 101 nginx; \
        adduser --system --disabled-login --ingroup nginx --no-create-home --home /nonexistent --gecos "nginx user" --shell /bin/false --uid 101 nginx; \
    fi

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/app /app
COPY server/nginx.conf /etc/nginx/nginx.conf

# Fix log and run dir permissions
RUN mkdir -p /var/log/nginx /var/lib/nginx && \
    chown -R nginx:nginx /var/log/nginx /var/lib/nginx

EXPOSE 80

COPY server/start.sh /start.sh
RUN chmod +x /start.sh

# Run as non-root user (security best practice)
#USER nginx

CMD ["/start.sh"]