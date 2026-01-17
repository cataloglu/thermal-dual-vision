ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest
FROM ${BUILD_FROM}

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-numpy \
    ffmpeg \
    libstdc++ \
    libgcc \
    gstreamer \
    gst-plugins-base \
    gst-plugins-good \
    gst-plugins-bad \
    gst-plugins-ugly \
    bash \
    jq \
    curl

# Create directory for bashio (Home Assistant Supervisor)
# Note: bashio library is usually provided by supervisor at runtime,
# but we create the directory for compatibility
RUN mkdir -p /usr/lib/bashio

# Set working directory
WORKDIR /app

# Copy requirements first for caching
ARG REQUIREMENTS_FILE=requirements.txt
COPY ${REQUIREMENTS_FILE} /app/requirements.txt

# Install Python dependencies
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Install OpenCV bindings after pip to avoid apk metadata issues
RUN apk add --no-cache \
    py3-opencv \
    opencv

# Copy application source
COPY src/ /app/src/
COPY run.sh /

# Normalize line endings and make run script executable
RUN sed -i 's/\r$//' /run.sh && chmod +x /run.sh

# Labels
LABEL \
    io.hass.name="Smart Motion Detector" \
    io.hass.description="AI-powered motion detection with YOLO and GPT-4 Vision" \
    io.hass.type="addon" \
    io.hass.version="1.0.0"

CMD ["/bin/sh", "/run.sh"]
