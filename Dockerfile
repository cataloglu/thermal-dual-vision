# Use standard Python image (Debian Bookworm)
# This avoids S6 Overlay complexity and PID 1 issues
FROM python:3.11-slim-bookworm

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    ffmpeg \
    nginx \
    curl \
    jq \
    git \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install go2rtc
# We need to detect arch manually since we are not using HA build args directly in FROM
ARG TARGETARCH
RUN if [ "$TARGETARCH" = "arm64" ]; then GO2RTC_ARCH="arm64"; \
    elif [ "$TARGETARCH" = "arm" ]; then GO2RTC_ARCH="arm"; \
    else GO2RTC_ARCH="amd64"; fi && \
    curl -L "https://github.com/AlexxIT/go2rtc/releases/download/v1.8.5/go2rtc_linux_${GO2RTC_ARCH}" -o /usr/local/bin/go2rtc && \
    chmod +x /usr/local/bin/go2rtc

# Setup App Directory
WORKDIR /app

# Copy Backend Code
COPY app /app/app
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

# Copy Frontend Code & Build
COPY ui /app/ui
WORKDIR /app/ui
RUN npm install && npm run build
WORKDIR /app

# Nginx Setup
# FIX: Copy to temp location first to avoid 'cannot stat' error
COPY nginx_addon.conf /tmp/nginx_addon.conf
RUN rm -f /etc/nginx/sites-enabled/default && \
    cp /tmp/nginx_addon.conf /etc/nginx/sites-available/default && \
    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# Copy Scripts & Configs
COPY run.sh /run.sh
COPY sync_options.py /app/sync_options.py
COPY fix_stream_roles.py /app/fix_stream_roles.py
COPY go2rtc.yaml /app/go2rtc.yaml

RUN chmod +x /run.sh

# Simple Entrypoint
ENTRYPOINT ["/run.sh"]
