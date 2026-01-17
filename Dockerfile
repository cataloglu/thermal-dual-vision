# Stage 1: Build frontend with Node.js
FROM node:20-alpine AS frontend-builder

# Set working directory
WORKDIR /build

# Copy package files
COPY web/package.json web/package-lock.json* ./

# Install dependencies
RUN npm ci --prefer-offline --no-audit

# Copy frontend source
COPY web/ ./

# Build frontend
RUN npm run build

# Stage 2: Python runtime
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
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application source
COPY src/ /app/src/
COPY run.sh /

# Copy built frontend assets from stage 1
COPY --from=frontend-builder /build/dist/ /app/web/dist/

# Make run script executable
RUN chmod +x /run.sh

# Labels
LABEL \
    io.hass.name="Smart Motion Detector" \
    io.hass.description="AI-powered motion detection with YOLO and GPT-4 Vision" \
    io.hass.type="addon" \
    io.hass.version="1.0.0"

CMD ["/run.sh"]
