ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install s6-overlay
ARG S6_OVERLAY_VERSION="3.1.5.0"
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz /tmp
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz /tmp
RUN tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz \
    && tar -C / -Jxpf /tmp/s6-overlay-x86_64.tar.xz \
    && rm -f /tmp/s6-overlay-*.tar.xz

# Install system dependencies
RUN apk add --no-cache \
    bash \
    bashio \
    python3 \
    py3-pip \
    py3-numpy \
    py3-opencv \
    ffmpeg \
    libstdc++ \
    libgcc

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt /app/

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application source
COPY src/ /app/src/
COPY run.sh /
COPY rootfs/ /

# Make run script executable
RUN chmod +x /run.sh

# Labels
LABEL \
    io.hass.name="Smart Motion Detector" \
    io.hass.description="AI-powered motion detection with YOLO and GPT-4 Vision" \
    io.hass.type="addon" \
    io.hass.version="1.0.0"

# Set s6-overlay entrypoint
ENTRYPOINT ["/init"]
