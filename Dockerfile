ARG BUILD_FROM
FROM $BUILD_FROM

# Switch to root user just in case
USER root

# Install dependencies (Debian based - Much safer for OpenCV/Python)
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
COPY app/ /app/app/
COPY requirements.txt ./

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages || pip3 install --no-cache-dir -r requirements.txt

# Copy Frontend Code & Build
COPY ui/ /app/ui/
WORKDIR /app/ui
RUN npm install && npm run build
WORKDIR /app

# Nginx Setup
COPY nginx_addon.conf /app/nginx_addon.conf
RUN mkdir -p /run/nginx && \
    rm -f /etc/nginx/sites-enabled/default && \
    cp /app/nginx_addon.conf /etc/nginx/sites-available/default && \
    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# Copy Configs
COPY sync_options.py /app/sync_options.py
COPY go2rtc.yaml /app/go2rtc.yaml

# Copy S6 Overlay Services (v3)
COPY rootfs /
RUN chmod a+x /etc/s6-overlay/s6-rc.d/thermal-vision/run

# Init handled by base image (S6 v3)
