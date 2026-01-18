ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.20
FROM ${BUILD_FROM}

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    build-base \
    python3-dev \
    py3-opencv \
    ffmpeg \
    libstdc++ \
    libgcc \
    musl-dev \
    linux-headers

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt /app/

# Install Python dependencies
RUN python3 -m venv --system-site-packages /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
RUN pip install -U pip setuptools wheel
RUN grep -v -e '^ultralytics' -e '^opencv-python-headless' requirements.txt > /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application source
COPY src/ /app/src/
COPY run.sh /

# Normalize line endings and make run script executable
RUN sed -i 's/\r$//' /run.sh \
    && chmod +x /run.sh

# Labels
LABEL \
    io.hass.name="Smart Motion Detector" \
    io.hass.description="AI-powered motion detection with YOLO and GPT-4 Vision" \
    io.hass.type="addon" \
    io.hass.version="1.0.0"

CMD ["/run.sh"]
