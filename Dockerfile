ARG BUILD_FROM
FROM $BUILD_FROM

# Switch to root user just in case
USER root

# Install dependencies (Debian based - Much safer for OpenCV/Python)
# We assume BUILD_FROM is a Debian-based HA base image or we force python:3.11-slim
# Since HA might inject an Alpine image, we need to be careful.
# BEST PRACTICE: Force a known working base image if we rely on complex libs like OpenCV
# But HA Addon require FROM $BUILD_FROM.
# Workaround: Check OS and install accordingly, OR assume user configured build.json correctly.
#
# LET'S ASSUME DEBIAN environment for stability with OpenCV.
# If HA injects Alpine, 'apt-get' will fail immediately and we know the issue.

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
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
ARG TARGETARCH
# Map architecture names
RUN if [ "$TARGETARCH" = "aarch64" ]; then GO2RTC_ARCH="arm64"; \
    elif [ "$TARGETARCH" = "armv7" ]; then GO2RTC_ARCH="arm"; \
    else GO2RTC_ARCH="amd64"; fi && \
    curl -L "https://github.com/AlexxIT/go2rtc/releases/download/v1.8.5/go2rtc_linux_${GO2RTC_ARCH}" -o /usr/local/bin/go2rtc && \
    chmod +x /usr/local/bin/go2rtc

# Setup App Directory
WORKDIR /app

# Copy Backend Code
COPY app /app/app
COPY requirements.txt .

# Install Python dependencies
# --break-system-packages is for newer Python envs
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages || pip3 install --no-cache-dir -r requirements.txt

# Copy Frontend Code & Build
COPY ui /app/ui
WORKDIR /app/ui
RUN npm install && npm run build
WORKDIR /app

# Nginx Setup
COPY nginx_addon.conf /etc/nginx/sites-enabled/default
# Fix nginx directories for Debian
RUN rm -f /etc/nginx/sites-enabled/default && \
    cp nginx_addon.conf /etc/nginx/sites-available/default && \
    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# Copy Scripts & Configs
COPY run.sh /run.sh
COPY sync_options.py /app/sync_options.py
COPY go2rtc.yaml /app/go2rtc.yaml

RUN chmod +x /run.sh

CMD [ "/run.sh" ]
