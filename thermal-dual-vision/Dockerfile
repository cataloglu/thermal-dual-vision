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
ARG TARGETARCH=amd64
# Map standard docker arch to go2rtc naming
RUN if [ "$TARGETARCH" = "amd64" ]; then GO2RTC_ARCH="amd64"; \
    elif [ "$TARGETARCH" = "arm64" ]; then GO2RTC_ARCH="arm64"; \
    elif [ "$TARGETARCH" = "arm/v7" ]; then GO2RTC_ARCH="arm"; \
    else GO2RTC_ARCH="amd64"; fi && \
    echo "Downloading go2rtc for $GO2RTC_ARCH..." && \
    curl -L "https://github.com/AlexxIT/go2rtc/releases/download/v1.8.5/go2rtc_linux_${GO2RTC_ARCH}" -o /usr/local/bin/go2rtc && \
    chmod +x /usr/local/bin/go2rtc

# Setup Python environment
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app /app/app
# Changed directory name here
COPY thermal-dual-vision /app/thermal-dual-vision
COPY go2rtc.yaml /app/go2rtc.yaml

# Copy built frontend
COPY --from=frontend /ui/dist /var/www/html

# Setup Nginx
RUN rm /etc/nginx/sites-enabled/default
# Updated path
COPY thermal-dual-vision/nginx.conf /etc/nginx/sites-enabled/default

# Setup Run Script
# Updated path
COPY thermal-dual-vision/run.sh /run.sh
RUN chmod +x /run.sh

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV GO2RTC_URL=http://localhost:1984
ENV DATA_DIR=/config

EXPOSE 8099 1984 8554

CMD ["/run.sh"]
