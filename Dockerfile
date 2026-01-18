ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install system dependencies
RUN apk add --no-cache \
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
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy application source
COPY src/ /app/src/
COPY run.sh /

# Make run script executable
RUN chmod +x /run.sh

# Labels
LABEL \
    io.hass.name="Smart Motion Detector" \
    io.hass.description="AI-powered motion detection with YOLO and GPT-4 Vision" \
    io.hass.type="addon" \
    io.hass.version="1.0.0"

CMD ["/run.sh"]
