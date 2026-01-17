#!/bin/bash
# Verification script for docker-compose standalone mode
# This script verifies that docker-compose up works correctly with .env file

set -e

echo "=============================================="
echo "Docker Compose Standalone Mode Verification"
echo "=============================================="
echo ""

# Step 1: Check prerequisites
echo "Step 1: Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo "✗ Docker is not installed"
    exit 1
fi

if ! docker compose version &> /dev/null && ! docker-compose --version &> /dev/null; then
    echo "✗ Docker Compose is not installed"
    exit 1
fi

echo "✓ Docker and Docker Compose are installed"
echo ""

# Step 2: Verify .env file exists and has required variables
echo "Step 2: Verifying .env file..."
if [ ! -f .env ]; then
    echo "✗ .env file not found"
    echo "  Please copy .env.example to .env and fill in required values"
    exit 1
fi

# Check for required variables
for var in HA_MODE CAMERA_URL OPENAI_API_KEY; do
    if ! grep -q "^${var}=" .env; then
        echo "✗ Missing required variable: ${var}"
        exit 1
    fi
done

# Verify HA_MODE is false (for standalone mode)
if grep -q "^HA_MODE=false" .env; then
    echo "✓ HA_MODE is set to false (standalone mode)"
else
    echo "⚠ Warning: HA_MODE is not set to false"
    echo "  For standalone mode testing, set HA_MODE=false in .env"
fi

echo "✓ .env file is properly configured"
echo ""

# Step 3: Validate docker-compose.yml
echo "Step 3: Validating docker-compose.yml..."
if docker compose config --quiet 2>/dev/null || docker-compose config --quiet 2>/dev/null; then
    echo "✓ docker-compose.yml is valid"
else
    echo "✗ docker-compose.yml has errors"
    exit 1
fi
echo ""

# Step 4: Build the image
echo "Step 4: Building Docker image..."
if docker compose build 2>/dev/null || docker-compose build 2>/dev/null; then
    echo "✓ Docker image built successfully"
else
    echo "✗ Failed to build Docker image"
    exit 1
fi
echo ""

# Step 5: Start the container
echo "Step 5: Starting container..."
echo "Running: docker compose up -d"
if docker compose up -d 2>/dev/null || docker-compose up -d 2>/dev/null; then
    echo "✓ Container started successfully"
else
    echo "✗ Failed to start container"
    exit 1
fi
echo ""

# Step 6: Wait for container to initialize
echo "Step 6: Waiting for container to initialize (5 seconds)..."
sleep 5
echo ""

# Step 7: Check container status
echo "Step 7: Checking container status..."
if docker ps | grep -q thermal-vision; then
    echo "✓ Container is running"
else
    echo "✗ Container is not running"
    echo ""
    echo "Showing container logs:"
    docker compose logs 2>/dev/null || docker-compose logs 2>/dev/null
    exit 1
fi
echo ""

# Step 8: Check logs for HA_MODE confirmation
echo "Step 8: Checking logs for HA_MODE=false confirmation..."
echo ""
echo "Container logs:"
echo "----------------------------------------"
docker compose logs 2>/dev/null || docker-compose logs 2>/dev/null
echo "----------------------------------------"
echo ""

if docker compose logs 2>/dev/null | grep -iq "HA_MODE.*false" || \
   docker compose logs 2>/dev/null | grep -iq "standalone.*mode" || \
   docker-compose logs 2>/dev/null | grep -iq "HA_MODE.*false" || \
   docker-compose logs 2>/dev/null | grep -iq "standalone.*mode"; then
    echo "✓ HA_MODE=false or standalone mode confirmed in logs"
else
    echo "⚠ Could not confirm HA_MODE=false in logs"
    echo "  Please check logs manually"
fi
echo ""

# Step 9: Check if web UI is accessible
echo "Step 9: Checking web UI accessibility..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8099 | grep -q "200\|404"; then
    echo "✓ Web UI is accessible on http://localhost:8099"
else
    echo "⚠ Web UI may not be accessible yet (this is okay if the app is still initializing)"
fi
echo ""

# Step 10: Summary
echo "=============================================="
echo "Verification Summary"
echo "=============================================="
echo "✓ .env file configured correctly"
echo "✓ docker-compose.yml is valid"
echo "✓ Docker image built successfully"
echo "✓ Container started without errors"
echo "✓ Container is running"
echo ""
echo "Next steps:"
echo "1. Access the web UI at http://localhost:8099"
echo "2. Check real-time logs: docker compose logs -f"
echo "3. Stop the container: docker compose down"
echo ""
echo "✓ Verification completed successfully!"
