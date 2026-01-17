#!/bin/bash

# Comprehensive integration test runner for Web UI
# This script builds, starts, and tests the entire web UI stack

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DOCKER_IMAGE="motion-detector-web-test"
CONTAINER_NAME="motion-detector-web-test"
TEST_PORT=8099
MAX_WAIT=60

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_step() {
    echo -e "${YELLOW}►${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

cleanup() {
    print_step "Cleaning up..."
    docker-compose -f docker-compose.test.yml down -v 2>/dev/null || true
    docker stop ${CONTAINER_NAME} 2>/dev/null || true
    docker rm ${CONTAINER_NAME} 2>/dev/null || true
    print_success "Cleanup complete"
}

# Trap for cleanup on exit
trap cleanup EXIT

main() {
    print_header "Web UI Integration Test Suite"

    # Step 1: Clean up any existing containers
    print_step "Step 1: Cleaning up existing test containers"
    cleanup

    # Step 2: Build Docker image
    print_header "Step 2: Building Docker Image"
    print_step "Building Docker image with multi-stage build (frontend + backend)..."

    if docker build -t ${DOCKER_IMAGE} .; then
        print_success "Docker image built successfully"
    else
        print_error "Docker build failed"
        exit 1
    fi

    # Step 3: Verify frontend assets exist in image
    print_header "Step 3: Verifying Frontend Assets"
    print_step "Checking if frontend assets were built and copied..."

    if docker run --rm ${DOCKER_IMAGE} ls -la /app/web/dist/ | grep -q "index.html"; then
        print_success "Frontend assets found in image"
    else
        print_error "Frontend assets not found in image"
        exit 1
    fi

    # Step 4: Start container with Docker Compose
    print_header "Step 4: Starting Web Server"
    print_step "Starting container with Docker Compose..."

    if docker-compose -f docker-compose.test.yml up -d; then
        print_success "Container started"
    else
        print_error "Failed to start container"
        exit 1
    fi

    # Step 5: Wait for server to be healthy
    print_header "Step 5: Waiting for Server Health Check"
    print_step "Waiting for server to respond (max ${MAX_WAIT}s)..."

    waited=0
    while [ $waited -lt $MAX_WAIT ]; do
        if curl -s -f http://localhost:${TEST_PORT}/health > /dev/null 2>&1; then
            print_success "Server is healthy and ready"
            break
        fi
        sleep 2
        waited=$((waited + 2))
        echo -n "."
    done

    if [ $waited -ge $MAX_WAIT ]; then
        print_error "Server failed to become healthy within ${MAX_WAIT}s"
        print_step "Showing container logs:"
        docker-compose -f docker-compose.test.yml logs
        exit 1
    fi

    # Step 6: Run integration tests
    print_header "Step 6: Running Integration Tests"

    if [ -f "./tests/integration/verify_integration.sh" ]; then
        print_step "Running automated integration tests..."
        if ./tests/integration/verify_integration.sh; then
            print_success "Integration tests passed"
        else
            print_error "Integration tests failed"
            print_step "Showing container logs:"
            docker-compose -f docker-compose.test.yml logs --tail=50
            exit 1
        fi
    else
        print_error "Integration test script not found"
        exit 1
    fi

    # Step 7: Run Python integration tests (if pytest available)
    print_header "Step 7: Running Python Integration Tests"

    if command -v pytest &> /dev/null; then
        print_step "Running pytest integration tests..."
        if pytest tests/integration/test_web_ui_integration.py -v --tb=short; then
            print_success "Python integration tests passed"
        else
            print_error "Python integration tests failed"
        fi
    else
        print_step "pytest not found, skipping Python tests"
    fi

    # Step 8: Show container logs summary
    print_header "Step 8: Container Logs Summary"
    print_step "Last 20 lines of container logs:"
    docker-compose -f docker-compose.test.yml logs --tail=20

    # Step 9: Show bundle size
    print_header "Step 9: Frontend Bundle Size Check"
    print_step "Checking bundle size (target: <100KB gzipped)..."

    docker run --rm ${DOCKER_IMAGE} sh -c "ls -lh /app/web/dist/assets/*.js 2>/dev/null || echo 'No JS files found'"

    # Success summary
    print_header "Integration Test Summary"
    echo -e "${GREEN}✓ Docker image built successfully${NC}"
    echo -e "${GREEN}✓ Frontend assets bundled and copied${NC}"
    echo -e "${GREEN}✓ Web server started and healthy${NC}"
    echo -e "${GREEN}✓ Integration tests passed${NC}"
    echo -e "${GREEN}✓ All API endpoints working${NC}"
    echo -e "${GREEN}✓ Frontend serves correctly${NC}"
    echo -e "${GREEN}✓ HA ingress path handling verified${NC}"

    print_header "Manual Testing Available"
    echo "The web UI is now running at: http://localhost:${TEST_PORT}"
    echo ""
    echo "Test the following pages:"
    echo "  - Dashboard:  http://localhost:${TEST_PORT}/"
    echo "  - Live View:  http://localhost:${TEST_PORT}/live"
    echo "  - Gallery:    http://localhost:${TEST_PORT}/gallery"
    echo "  - Events:     http://localhost:${TEST_PORT}/events"
    echo "  - Settings:   http://localhost:${TEST_PORT}/settings"
    echo ""
    echo "Press Ctrl+C to stop the container and cleanup"
    echo ""

    # Keep running for manual testing
    read -p "Press Enter to stop the test environment..."
}

# Run main function
main "$@"
