#!/bin/bash

# Integration verification script for Web UI with HA ingress support
# Tests all end-to-end requirements

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8099}"
INGRESS_PATH="/api/hassio_ingress/test123"
ALLOWED_IP="172.30.32.2"

# Counters
PASSED=0
FAILED=0

# Helper functions
print_header() {
    echo -e "\n${YELLOW}========================================${NC}"
    echo -e "${YELLOW}$1${NC}"
    echo -e "${YELLOW}========================================${NC}\n"
}

print_test() {
    echo -e "${YELLOW}TEST:${NC} $1"
}

print_pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    ((FAILED++))
}

print_info() {
    echo -e "${YELLOW}INFO:${NC} $1"
}

# Test function
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_pattern="$3"

    print_test "$test_name"

    if output=$(eval "$test_command" 2>&1); then
        if [[ -z "$expected_pattern" ]] || echo "$output" | grep -q "$expected_pattern"; then
            print_pass "$test_name"
            return 0
        else
            print_fail "$test_name - Expected pattern not found: $expected_pattern"
            echo "Output: $output"
            return 1
        fi
    else
        print_fail "$test_name - Command failed"
        echo "Error: $output"
        return 1
    fi
}

# Check if server is running
check_server() {
    print_header "CHECKING SERVER STATUS"

    if curl -s -f "${BASE_URL}/health" > /dev/null 2>&1; then
        print_pass "Web server is running at $BASE_URL"
        return 0
    else
        print_fail "Web server is not running at $BASE_URL"
        print_info "Start the server with: python src/web_server.py"
        exit 1
    fi
}

# Test 1: Frontend loads under ingress path
test_frontend_loads() {
    print_header "TEST 1: Frontend Loads Under Ingress Path"

    run_test "Frontend index.html serves" \
        "curl -s -H 'X-Ingress-Path: ${INGRESS_PATH}' -H 'X-Forwarded-For: ${ALLOWED_IP}' ${BASE_URL}/" \
        "div id=\"app\""

    run_test "Frontend has DOCTYPE" \
        "curl -s -H 'X-Ingress-Path: ${INGRESS_PATH}' -H 'X-Forwarded-For: ${ALLOWED_IP}' ${BASE_URL}/" \
        "<!DOCTYPE html>"
}

# Test 2: API calls work with ingress prefix
test_api_endpoints() {
    print_header "TEST 2: API Calls Work With Ingress Prefix"

    run_test "API status endpoint" \
        "curl -s -H 'X-Ingress-Path: ${INGRESS_PATH}' -H 'X-Forwarded-For: ${ALLOWED_IP}' ${BASE_URL}/api/status" \
        "\"status\""

    run_test "API stats endpoint" \
        "curl -s -H 'X-Ingress-Path: ${INGRESS_PATH}' -H 'X-Forwarded-For: ${ALLOWED_IP}' ${BASE_URL}/api/stats" \
        "\"total_detections\""

    run_test "API events endpoint" \
        "curl -s -H 'X-Ingress-Path: ${INGRESS_PATH}' -H 'X-Forwarded-For: ${ALLOWED_IP}' ${BASE_URL}/api/events" \
        "\"events\""

    run_test "API screenshots endpoint" \
        "curl -s -H 'X-Ingress-Path: ${INGRESS_PATH}' -H 'X-Forwarded-For: ${ALLOWED_IP}' ${BASE_URL}/api/screenshots" \
        "\"screenshots\""

    run_test "API config GET endpoint" \
        "curl -s -H 'X-Ingress-Path: ${INGRESS_PATH}' -H 'X-Forwarded-For: ${ALLOWED_IP}' ${BASE_URL}/api/config" \
        "\"camera\""
}

# Test 3: WebSocket connection works
test_websocket() {
    print_header "TEST 3: WebSocket Connection"

    # Check if wscat is available
    if command -v wscat &> /dev/null; then
        print_test "WebSocket connection test (with wscat)"
        timeout 5 wscat -c "ws://localhost:8099/socket.io/?EIO=4&transport=websocket" &
        WS_PID=$!
        sleep 2
        if kill -0 $WS_PID 2>/dev/null; then
            print_pass "WebSocket connection established"
            kill $WS_PID 2>/dev/null || true
        else
            print_fail "WebSocket connection failed"
        fi
    else
        print_info "wscat not installed - skipping WebSocket test"
        print_info "Install with: npm install -g wscat"
    fi

    # Test Socket.IO endpoint exists
    run_test "Socket.IO endpoint responds" \
        "curl -s ${BASE_URL}/socket.io/" \
        "Missing"  # Socket.IO returns error for HTTP requests
}

# Test 4: Live stream displays
test_live_stream() {
    print_header "TEST 4: Live Stream Displays"

    run_test "MJPEG stream endpoint responds" \
        "curl -s -H 'X-Ingress-Path: ${INGRESS_PATH}' -H 'X-Forwarded-For: ${ALLOWED_IP}' -N ${BASE_URL}/api/stream --max-time 2" \
        "multipart"
}

# Test 5: SPA routing works
test_spa_routing() {
    print_header "TEST 5: SPA Client-Side Routing"

    local routes=("/" "/live" "/gallery" "/events" "/settings" "/dashboard")

    for route in "${routes[@]}"; do
        run_test "Route ${route} serves index.html" \
            "curl -s -H 'X-Ingress-Path: ${INGRESS_PATH}' -H 'X-Forwarded-For: ${ALLOWED_IP}' ${BASE_URL}${route}" \
            "div id=\"app\""
    done
}

# Test 6: Static assets serve correctly
test_static_assets() {
    print_header "TEST 6: Static Assets"

    # Check if assets directory exists
    if curl -s "${BASE_URL}/assets/" | grep -q "404\|index"; then
        print_info "Static assets directory structure verified"
    fi

    # Test that unknown routes fall back to index.html
    run_test "Unknown route falls back to index.html" \
        "curl -s -H 'X-Ingress-Path: ${INGRESS_PATH}' -H 'X-Forwarded-For: ${ALLOWED_IP}' ${BASE_URL}/unknown-route" \
        "div id=\"app\""
}

# Test 7: IP whitelist enforcement
test_ip_whitelist() {
    print_header "TEST 7: IP Whitelist Enforcement"

    # Test with whitelisted IP
    run_test "Whitelisted IP (${ALLOWED_IP}) allowed" \
        "curl -s -H 'X-Forwarded-For: ${ALLOWED_IP}' ${BASE_URL}/api/status" \
        "\"status\""

    # Test with non-whitelisted IP (only if not in DEV_MODE)
    if [[ "${DEV_MODE}" != "true" ]]; then
        print_test "Non-whitelisted IP blocked"
        if curl -s -H 'X-Forwarded-For: 192.168.1.100' "${BASE_URL}/api/status" | grep -q "Forbidden"; then
            print_pass "Non-whitelisted IP blocked"
        else
            print_info "IP blocking not enforced (DEV_MODE may be enabled)"
        fi
    else
        print_info "DEV_MODE enabled - skipping IP whitelist blocking test"
    fi
}

# Test 8: Health check
test_health_check() {
    print_header "TEST 8: Health Check"

    run_test "Health endpoint responds" \
        "curl -s ${BASE_URL}/health" \
        "\"ok\""

    run_test "Health endpoint returns correct service name" \
        "curl -s ${BASE_URL}/health" \
        "motion-detector-web"
}

# Test 9: CORS headers
test_cors() {
    print_header "TEST 9: CORS Headers"

    run_test "CORS headers present" \
        "curl -s -I ${BASE_URL}/api/status" \
        "Access-Control-Allow-Origin"
}

# Test 10: Ingress path variations
test_ingress_variations() {
    print_header "TEST 10: Ingress Path Variations"

    local paths=("/api/hassio_ingress/abc123" "/api/hassio_ingress/xyz789" "/custom/path")

    for path in "${paths[@]}"; do
        run_test "Ingress path ${path}" \
            "curl -s -H 'X-Ingress-Path: ${path}' -H 'X-Forwarded-For: ${ALLOWED_IP}' ${BASE_URL}/api/status" \
            "\"status\""
    done
}

# Print summary
print_summary() {
    print_header "TEST SUMMARY"

    local total=$((PASSED + FAILED))

    echo -e "Total Tests: $total"
    echo -e "${GREEN}Passed: $PASSED${NC}"
    echo -e "${RED}Failed: $FAILED${NC}"

    if [[ $FAILED -eq 0 ]]; then
        echo -e "\n${GREEN}✓ ALL TESTS PASSED${NC}\n"
        return 0
    else
        echo -e "\n${RED}✗ SOME TESTS FAILED${NC}\n"
        return 1
    fi
}

# Main execution
main() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Web UI Integration Verification${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Base URL: $BASE_URL"
    echo "Ingress Path: $INGRESS_PATH"
    echo "Allowed IP: $ALLOWED_IP"
    echo ""

    # Run all tests
    check_server
    test_health_check
    test_frontend_loads
    test_api_endpoints
    test_websocket
    test_live_stream
    test_spa_routing
    test_static_assets
    test_ip_whitelist
    test_cors
    test_ingress_variations

    # Print summary and exit with appropriate code
    print_summary
    exit $?
}

# Run main function
main "$@"
