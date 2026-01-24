# Stage 1: Build UI
FROM node:20-alpine AS frontend
WORKDIR /ui
COPY ui/package.json ui/package-lock.json* ./
RUN npm ci
COPY ui/ ./
RUN npm run build

# Stage 2: Final Image
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    nginx \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Download go2rtc
# Use BUILD_ARCH for Home Assistant, fallback to TARGETARCH or default
ARG BUILD_ARCH
ARG TARGETARCH

RUN if [ -n "$BUILD_ARCH" ]; then ARCH="$BUILD_ARCH"; else ARCH="$TARGETARCH"; fi && \
    if [ -z "$ARCH" ]; then ARCH="amd64"; fi && \
    echo "Detected architecture: $ARCH" && \
    if [ "$ARCH" = "amd64" ]; then GO2RTC_ARCH="amd64"; \
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then GO2RTC_ARCH="arm64"; \
    elif [ "$ARCH" = "armv7" ] || [ "$ARCH" = "arm/v7" ]; then GO2RTC_ARCH="arm"; \
    elif [ "$ARCH" = "i386" ]; then GO2RTC_ARCH="i386"; \
    else echo "Unknown architecture: $ARCH, defaulting to amd64"; GO2RTC_ARCH="amd64"; fi && \
    echo "Downloading go2rtc for $GO2RTC_ARCH..." && \
    curl -L "https://github.com/AlexxIT/go2rtc/releases/download/v1.8.5/go2rtc_linux_${GO2RTC_ARCH}" -o /usr/local/bin/go2rtc && \
    chmod +x /usr/local/bin/go2rtc

# Setup Python environment
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app /app/app
COPY thermal-dual-vision /app/thermal-dual-vision
COPY go2rtc.yaml /app/go2rtc.yaml

# Copy built frontend
COPY --from=frontend /ui/dist /var/www/html

# Setup Nginx
RUN rm /etc/nginx/sites-enabled/default
COPY thermal-dual-vision/nginx.conf /etc/nginx/sites-enabled/default

# Setup Run Script
COPY thermal-dual-vision/run.sh /run.sh
RUN chmod +x /run.sh

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV GO2RTC_URL=http://localhost:1984
ENV DATA_DIR=/config

EXPOSE 8099 1984 8554

CMD ["/run.sh"]
