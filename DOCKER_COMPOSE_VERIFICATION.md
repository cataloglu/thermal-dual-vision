# Docker Compose Standalone Mode Verification

## Overview
This document describes the verification process for docker-compose standalone mode deployment with .env file configuration.

## Pre-Verification Checks Completed ✓

### 1. Environment File Setup
- ✓ `.env.example` exists with comprehensive documentation
- ✓ `.env` file created from `.env.example`
- ✓ Required variables configured:
  - `HA_MODE=false` (standalone mode)
  - `CAMERA_URL=rtsp://test:test@192.168.1.100:554/stream`
  - `OPENAI_API_KEY=sk-test-key-for-testing-purposes`

### 2. Docker Compose Configuration
- ✓ `docker-compose.yml` has valid YAML syntax
- ✓ Service `thermal-vision` properly configured
- ✓ Environment variables correctly referenced from .env file:
  ```yaml
  environment:
    - HA_MODE=false
    - CAMERA_URL=${CAMERA_URL}
    - OPENAI_API_KEY=${OPENAI_API_KEY}
    - TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
    - MQTT_HOST=${MQTT_HOST:-}
    # ... and other variables with defaults
  ```
- ✓ Port mapping configured: `8099:8099`
- ✓ Volume mounts configured:
  - `./data:/data` (for screenshots and logs)
  - `./config:/config` (for config.yaml)
- ✓ Restart policy: `unless-stopped`
- ✓ Logging configured with size limits

### 3. Dockerfile Configuration
- ✓ Default CMD set to standalone mode: `["python3", "-m", "src.main"]`
- ✓ Compatible with both standalone and HA add-on modes
- ✓ All required dependencies included

### 4. Required Directories
- ✓ `./data` directory created
- ✓ `./config` directory created

### 5. Configuration Files
- ✓ `config/config.yaml` exists with standalone configuration template
- ✓ All configuration sections properly structured

## Verification Script

A comprehensive verification script has been created: `verify-docker-compose.sh`

### What the script does:
1. Checks Docker and Docker Compose installation
2. Verifies .env file exists and has required variables
3. Validates docker-compose.yml syntax
4. Builds the Docker image
5. Starts the container in detached mode
6. Checks container status
7. Examines logs for HA_MODE=false confirmation
8. Tests web UI accessibility on port 8099
9. Provides a summary and next steps

### Running the script:
```bash
./verify-docker-compose.sh
```

## Manual Verification Steps

Since Docker is not available in the automated test environment, the following manual verification steps should be performed when Docker is available:

### Step 1: Prepare Environment
```bash
# Ensure you're in the project root directory
cd /path/to/motion-detector

# Verify .env file exists
ls -la .env

# Check critical variables
grep -E "^(HA_MODE|CAMERA_URL|OPENAI_API_KEY)=" .env
```

### Step 2: Validate Configuration
```bash
# Validate docker-compose.yml syntax
docker compose config --quiet
# OR (for older versions)
docker-compose config --quiet

# Should exit with no errors
```

### Step 3: Build and Start
```bash
# Build the Docker image
docker compose build

# Start the container in detached mode
docker compose up -d

# Or start with logs visible (Ctrl+C to stop)
docker compose up
```

### Step 4: Verify Container is Running
```bash
# Check container status
docker ps | grep thermal-vision

# Should show thermal-vision container with status "Up"
```

### Step 5: Check Logs for HA_MODE Confirmation
```bash
# View container logs
docker compose logs

# Look for one of these confirmations:
# - "HA_MODE=false" or "HA_MODE: false"
# - "Standalone mode" or "Running in standalone mode"
# - "Skipping MQTT auto-discovery (HA_MODE=false)"

# Follow logs in real-time
docker compose logs -f
```

### Step 6: Verify No Errors
Check logs for:
- ✓ No Python exceptions or stack traces
- ✓ Configuration loaded successfully
- ✓ Camera connection initialized (may fail without real camera, that's okay)
- ✓ MQTT auto-discovery skipped (HA_MODE=false confirmation)
- ✓ Web server started on port 8099

### Step 7: Access Web UI
```bash
# Open browser to:
http://localhost:8099

# Or test with curl:
curl -I http://localhost:8099
```

### Step 8: Clean Up
```bash
# Stop and remove container
docker compose down

# View logs if needed
docker compose logs
```

## Expected Log Output

When running correctly in standalone mode, logs should show:

```
INFO: Loading configuration...
INFO: HA_MODE=false (Standalone mode)
INFO: Loading config from /config/config.yaml
INFO: Applying environment variable overrides
INFO: Configuration loaded successfully
INFO: Camera URL: rtsp://test:test@192.168.1.100:554/stream
INFO: Initializing MQTT client...
INFO: Skipping MQTT auto-discovery (HA_MODE=false)
INFO: Starting web server on 0.0.0.0:8099
INFO: Motion detector ready
```

## Success Criteria

The verification is successful when:

1. ✓ `.env` file is properly configured with required variables
2. ✓ `docker-compose config` validates without errors
3. ✓ `docker compose up` starts the container without errors
4. ✓ Container status shows as "Up"
5. ✓ Logs confirm `HA_MODE=false` or "standalone mode"
6. ✓ Logs show "Skipping MQTT auto-discovery" (HA_MODE check)
7. ✓ No critical errors in logs (camera connection failures are acceptable)
8. ✓ Web UI is accessible on http://localhost:8099

## Troubleshooting

### Container exits immediately
```bash
# Check logs for errors
docker compose logs

# Common issues:
# - Missing required environment variables
# - Invalid camera URL format
# - Permission issues with volumes
```

### Cannot access web UI
```bash
# Check if port is bound
docker ps | grep 8099

# Check container logs
docker compose logs | grep -i "web\|server\|port"

# Test connection
curl -v http://localhost:8099
```

### Configuration not loading
```bash
# Verify config.yaml exists
ls -la config/config.yaml

# Check environment variables are passed
docker compose config | grep -A 20 environment

# Verify .env file is in same directory as docker-compose.yml
ls -la .env
```

## Files Created/Modified

- ✓ `.env` - Environment configuration file
- ✓ `verify-docker-compose.sh` - Automated verification script
- ✓ `DOCKER_COMPOSE_VERIFICATION.md` - This documentation
- ✓ `data/` - Directory for screenshots and logs
- ✓ `config/` - Directory for config.yaml

## Next Steps

After successful verification:
1. Proceed to subtask-4-3: Test MQTT optional connection
2. Complete final integration testing
3. Update documentation with any findings
4. Prepare for QA sign-off

## Verification Status

**Status**: ✓ Pre-verification completed successfully

**Note**: Full Docker-based verification requires a system with Docker installed. All preparatory steps and configuration validation have been completed. The verification script (`verify-docker-compose.sh`) is ready to be executed on a Docker-enabled system.

**Automated Checks Passed**:
- ✓ YAML syntax validation
- ✓ Environment file validation
- ✓ Required variables present
- ✓ HA_MODE set to false
- ✓ Directory structure created
- ✓ Configuration files present

**Manual Verification Required**:
- Container build and startup
- Log verification
- Web UI accessibility
- Full end-to-end functionality

---

*Generated as part of subtask-4-2: Verify docker-compose up works with .env file*
