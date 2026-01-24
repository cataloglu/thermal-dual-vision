ARG BUILD_FROM
FROM $BUILD_FROM

# Install dependencies (Alpine based)
RUN apk add --no-cache \
    python3 \
    py3-pip \
    nodejs \
    npm \
    ffmpeg \
    nginx \
    curl \
    jq \
    git

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
# Note: --break-system-packages is needed for newer Python versions in Alpine
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

# Copy Frontend Code & Build
COPY ui /app/ui
WORKDIR /app/ui
RUN npm install && npm run build
WORKDIR /app

# Nginx Setup
COPY nginx_addon.conf /etc/nginx/http.d/default.conf
RUN mkdir -p /run/nginx

# Copy Scripts & Configs
COPY run.sh /run.sh
COPY go2rtc.yaml /app/go2rtc.yaml

RUN chmod +x /run.sh

CMD [ "/run.sh" ]
