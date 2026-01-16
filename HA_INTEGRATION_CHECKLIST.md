# Home Assistant Integration Verification Checklist

This checklist provides step-by-step verification procedures for the Smart Motion Detector add-on integration with Home Assistant. Complete each section to ensure full functionality.

---

## 📋 Pre-Installation Checks

### Repository Structure
- [ ] `config.yaml` exists and contains valid YAML
- [ ] `Dockerfile` includes s6-overlay integration
- [ ] `DOCS.md` documentation is complete
- [ ] `CHANGELOG.md` includes HA integration notes
- [ ] `rootfs/` directory structure exists:
  - [ ] `rootfs/etc/cont-init.d/01-init.sh` (executable)
  - [ ] `rootfs/etc/services.d/smart-motion/run` (executable)
  - [ ] `rootfs/etc/services.d/smart-motion/finish` (executable)

### File Permissions
```bash
# Verify all scripts are executable
find rootfs -type f \( -name "*.sh" -o -name "run" -o -name "finish" \) -exec test -x {} \; && echo "✓ All scripts executable"
```
- [ ] All service scripts have executable permissions

### Configuration Validation
```bash
# Validate config.yaml syntax
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))" && echo "✓ config.yaml is valid"
```
- [ ] config.yaml passes YAML validation
- [ ] All required fields present: name, version, slug, arch, startup, boot, init
- [ ] Options schema matches available options
- [ ] Ingress configuration present (port 8099)
- [ ] MQTT service enabled

---

## 🏗️ Build and Installation

### Docker Build
```bash
# Build the add-on (run in HA environment or test with Docker)
docker build -t smart-motion-detector-test .
```
- [ ] Docker build completes without errors
- [ ] s6-overlay is correctly installed
- [ ] Python dependencies install successfully
- [ ] YOLO model downloads complete
- [ ] No security warnings in build output

### Add-on Installation (Home Assistant)
- [ ] Add-on repository successfully added to HA
- [ ] Add-on appears in Supervisor → Add-on Store
- [ ] Add-on icon displays correctly (if provided)
- [ ] Add-on description shows properly
- [ ] Architecture matches (amd64 or aarch64)
- [ ] Installation completes without errors
- [ ] Installation time is reasonable (< 10 minutes)

---

## ⚙️ Configuration (Options UI)

### Access Options
- [ ] Navigate to add-on page in Supervisor
- [ ] **Configuration** tab is accessible
- [ ] Options UI loads without errors

### Required Options
Test each required configuration option:

#### Camera Configuration
- [ ] `camera_url`: Accepts valid RTSP/HTTP URLs
- [ ] `camera_url`: Rejects invalid URLs (schema validation)
- [ ] `camera_fps`: Accepts values 1-30
- [ ] `camera_fps`: Rejects out-of-range values

#### Motion Detection
- [ ] `motion_sensitivity`: Accepts values 1-10
- [ ] `motion_min_area`: Accepts values 100-10000
- [ ] `motion_cooldown`: Accepts values 1-60

#### YOLO Configuration
- [ ] `yolo_model`: Shows dropdown (yolov8n, yolov8s, yolov8m)
- [ ] `yolo_confidence`: Accepts float 0.1-1.0
- [ ] `yolo_classes`: Accepts list of class names

#### OpenAI Configuration
- [ ] `openai_api_key`: Accepts password input (masked)
- [ ] `screenshot_before_sec`: Accepts values 1-10
- [ ] `screenshot_after_sec`: Accepts values 1-10

#### MQTT Configuration
- [ ] `mqtt_topic_prefix`: Accepts string
- [ ] `mqtt_discovery`: Shows boolean toggle

#### Telegram Configuration (Optional)
- [ ] `telegram_enabled`: Shows boolean toggle
- [ ] `telegram_bot_token`: Optional password field
- [ ] `telegram_chat_id`: Optional string field

#### Logging
- [ ] `log_level`: Shows dropdown (DEBUG, INFO, WARNING, ERROR)

### Save and Restart
- [ ] Click **Save** → Changes persist
- [ ] **Restart** button appears after config change
- [ ] Restart initiates successfully
- [ ] Add-on stops and starts cleanly

---

## 🌐 Ingress Panel Access

### Panel Availability
- [ ] "Smart Motion" panel appears in left sidebar
- [ ] Panel icon shows correctly (mdi:motion-sensor)
- [ ] Panel title displays as "Smart Motion"

### Ingress Access
- [ ] Click panel → Ingress URL loads
- [ ] Web UI displays without errors
- [ ] No CORS or authentication errors
- [ ] URL format: `http://homeassistant.local:8123/hassio/ingress/smart_motion_detector`

### Web UI Functionality
- [ ] Health check endpoint responds (`/health`)
- [ ] UI shows "Motion Detector Running"
- [ ] Status information displays correctly
- [ ] No console errors in browser developer tools

### Direct Port Access (if configured)
- [ ] Port 8099 accessible from HA network (if not using ingress-only)
- [ ] Direct access works: `http://[ha-ip]:8099/health`

---

## 📡 MQTT Integration

### MQTT Broker Connection
- [ ] MQTT broker (Mosquitto) is installed and running
- [ ] Add-on logs show MQTT connection success
- [ ] No authentication errors in logs

### Auto-Discovery
- [ ] Navigate to **Settings** → **Devices & Services** → **MQTT**
- [ ] Check **Devices** tab for auto-discovered entities
- [ ] "Smart Motion Detector" device appears (if discovery enabled)

### MQTT Topics
Verify messages published to expected topics:

```bash
# Subscribe to MQTT topics (from HA terminal or MQTT client)
mosquitto_sub -h localhost -t "smart_motion/#" -v
```

Expected topics (with `mqtt_topic_prefix: "smart_motion"`):
- [ ] `smart_motion/status` - Add-on status messages
- [ ] `smart_motion/motion` - Motion detection events
- [ ] `smart_motion/detection` - Object detection results
- [ ] `smart_motion/analysis` - GPT-4 Vision analysis results

### Message Format
- [ ] Messages are valid JSON
- [ ] Timestamps are present and correct
- [ ] Detection confidence scores included
- [ ] Screenshot paths included (if enabled)

---

## 📊 Logging and Monitoring

### Log Access
- [ ] Navigate to add-on page → **Log** tab
- [ ] Logs display in real-time
- [ ] Log level matches configuration (INFO by default)

### Startup Logs
Verify the following appear in startup logs:
- [ ] s6-overlay init messages
- [ ] Container init script (`01-init.sh`) runs
- [ ] Service start (`smart-motion/run`) executes
- [ ] Bashio messages show proper formatting
- [ ] Python application starts
- [ ] Camera connection established
- [ ] YOLO model loaded
- [ ] MQTT connection confirmed
- [ ] Web server listening on port 8099

### Runtime Logs
- [ ] Motion detection events logged
- [ ] Object detection results logged
- [ ] No repeated error messages
- [ ] No Python tracebacks (unless expected errors)
- [ ] Log rotation works (if configured)

### Error Handling
Test error scenarios and verify proper logging:
- [ ] Invalid camera URL → Clear error message
- [ ] Invalid OpenAI API key → API error logged
- [ ] MQTT broker unavailable → Connection retry logged
- [ ] Missing required config → Validation error shown

---

## 🔄 Service Management

### Start/Stop/Restart
- [ ] **Start** button works
- [ ] **Stop** button works
- [ ] **Restart** button works
- [ ] Status indicator updates correctly (Running/Stopped)

### S6-Overlay Service
Verify s6-overlay manages the service properly:
- [ ] Service starts via `/init` entrypoint
- [ ] Container init script runs first
- [ ] Main service script runs after init
- [ ] Service finish script runs on stop/crash

### Graceful Shutdown
- [ ] Stop command completes cleanly
- [ ] Finish script logs exit information
- [ ] No orphaned processes remain
- [ ] Resources cleaned up properly

### Auto-Start on Boot
- [ ] Enable "Start on boot" option
- [ ] Restart Home Assistant (or test with container restart)
- [ ] Add-on starts automatically
- [ ] All services initialize correctly

### Crash Recovery
Simulate crash and verify recovery:
```bash
# From HA terminal or SSH
docker exec -it addon_smart_motion_detector pkill -9 python
```
- [ ] s6-overlay detects service crash
- [ ] Finish script logs exit code
- [ ] Service automatically restarts (if configured)
- [ ] Add-on returns to running state

---

## 🔧 Configuration Changes

### Runtime Updates
Test configuration changes with running add-on:
- [ ] Change `motion_sensitivity` → Save
- [ ] Restart add-on → New value takes effect
- [ ] Check logs confirm new configuration
- [ ] Motion detection behaves according to new setting

### API Key Rotation
- [ ] Update `openai_api_key` → Save → Restart
- [ ] New API key used for subsequent requests
- [ ] Old key no longer used

### MQTT Topic Change
- [ ] Update `mqtt_topic_prefix` → Save → Restart
- [ ] New topics used for publishing
- [ ] Auto-discovery updates (if enabled)

### Toggle Features
- [ ] Disable `telegram_enabled` → Telegram notifications stop
- [ ] Enable `telegram_enabled` → Notifications resume
- [ ] Disable `mqtt_discovery` → Auto-discovery removed

---

## 🔐 Security and Permissions

### Password Fields
- [ ] `openai_api_key` not visible in logs
- [ ] `telegram_bot_token` not visible in logs
- [ ] Secrets properly masked in configuration UI

### File Permissions
- [ ] Add-on runs as correct user (not root if possible)
- [ ] Configuration files readable by add-on
- [ ] Screenshot directory writable
- [ ] Log files writable

### Network Security
- [ ] Ingress provides proper isolation
- [ ] Direct port access secured (if exposed)
- [ ] MQTT uses authentication (if configured)
- [ ] No sensitive data in MQTT topics

---

## 📈 Performance and Resources

### Resource Usage
Monitor in Supervisor → Add-ons → Smart Motion Detector:
- [ ] CPU usage reasonable (< 50% average)
- [ ] Memory usage stable (no leaks)
- [ ] Disk usage acceptable
- [ ] No continuous high I/O

### Camera Stream
- [ ] Camera stream connects reliably
- [ ] FPS setting respected
- [ ] No buffering or lag issues
- [ ] Stream reconnects after interruption

### Detection Performance
- [ ] Motion detection responsive (< 1 second)
- [ ] YOLO inference completes quickly (< 2 seconds)
- [ ] GPT-4 Vision analysis returns timely (< 10 seconds)
- [ ] No processing backlog

### Cooldown Behavior
- [ ] `motion_cooldown` prevents event spam
- [ ] Events properly throttled
- [ ] Cooldown timer resets correctly

---

## 🧪 Integration Testing Scenarios

### Scenario 1: Basic Motion Detection
1. [ ] Configure camera URL and start add-on
2. [ ] Trigger motion in camera view
3. [ ] Verify motion event in logs
4. [ ] Check MQTT topic receives event
5. [ ] Verify screenshot saved (if enabled)

### Scenario 2: Object Detection
1. [ ] Configure YOLO classes (e.g., person, car)
2. [ ] Trigger motion with configured object
3. [ ] Verify object detected in logs
4. [ ] Check detection published to MQTT
5. [ ] Verify confidence score reasonable

### Scenario 3: GPT-4 Vision Analysis
1. [ ] Configure valid OpenAI API key
2. [ ] Trigger motion event
3. [ ] Verify GPT-4 Vision called (check logs)
4. [ ] Check analysis description received
5. [ ] Verify analysis published to MQTT

### Scenario 4: Telegram Notification
1. [ ] Configure Telegram bot and chat ID
2. [ ] Enable `telegram_enabled`
3. [ ] Trigger motion event
4. [ ] Verify Telegram message received
5. [ ] Check screenshot attached to message

### Scenario 5: MQTT Auto-Discovery
1. [ ] Enable `mqtt_discovery`
2. [ ] Start add-on
3. [ ] Check HA MQTT integration for new entities
4. [ ] Verify entities controllable from HA
5. [ ] Test entity state updates

### Scenario 6: Configuration Update
1. [ ] Start with default configuration
2. [ ] Change multiple settings via Options UI
3. [ ] Save and restart
4. [ ] Verify all changes applied
5. [ ] Confirm behavior matches new config

### Scenario 7: Error Recovery
1. [ ] Start with valid configuration
2. [ ] Disconnect camera (or use invalid URL)
3. [ ] Verify error logged, not crash
4. [ ] Restore camera connection
5. [ ] Verify automatic recovery

### Scenario 8: High Load
1. [ ] Configure aggressive motion sensitivity
2. [ ] Trigger continuous motion
3. [ ] Verify system remains stable
4. [ ] Check no memory leaks
5. [ ] Confirm cooldown prevents overload

---

## ✅ Final Acceptance Criteria

### Core Functionality
- [ ] Add-on installs and starts successfully
- [ ] All configuration options work as expected
- [ ] Motion detection operational
- [ ] YOLO object detection operational
- [ ] GPT-4 Vision analysis operational (with valid key)
- [ ] MQTT integration functional

### Home Assistant Integration
- [ ] Add-on appears in Supervisor
- [ ] Options UI fully functional
- [ ] Ingress panel accessible
- [ ] Logs visible in Supervisor
- [ ] Auto-discovery works (if enabled)
- [ ] Service management works (start/stop/restart)

### Documentation
- [ ] DOCS.md provides clear installation instructions
- [ ] All configuration options documented
- [ ] Troubleshooting guide helpful
- [ ] CHANGELOG.md updated with HA integration

### Reliability
- [ ] Add-on runs continuously without crashes
- [ ] Error handling prevents crashes
- [ ] Service restarts cleanly
- [ ] Resources properly managed
- [ ] No memory leaks over 24-hour test

### Performance
- [ ] Detection latency acceptable (< 2 seconds)
- [ ] Resource usage reasonable
- [ ] Camera stream stable
- [ ] MQTT messages timely

---

## 🐛 Known Issues and Workarounds

Document any issues found during testing:

### Issue Template
```markdown
**Issue:** [Brief description]
**Severity:** Critical / High / Medium / Low
**Steps to Reproduce:**
1. [Step 1]
2. [Step 2]

**Expected:** [What should happen]
**Actual:** [What actually happens]
**Workaround:** [Temporary solution, if any]
**Fix Required:** [What needs to be done]
```

---

## 📝 Test Environment Details

Fill in your test environment information:

**Home Assistant Version:** _________________
**Supervisor Version:** _________________
**Architecture:** amd64 / aarch64
**Add-on Version:** 1.0.0
**MQTT Broker:** Mosquitto / Other: _________________
**Test Date:** _________________
**Tester Name:** _________________

---

## 🎯 Sign-Off

### Development Team
- [ ] All unit tests pass (if applicable)
- [ ] Integration tests complete
- [ ] Code review completed
- [ ] Documentation reviewed

**Developer Signature:** _________________ **Date:** _______

### QA Team
- [ ] All checklist items completed
- [ ] No critical issues found
- [ ] Performance acceptable
- [ ] Documentation verified

**QA Signature:** _________________ **Date:** _______

### Product Owner
- [ ] Acceptance criteria met
- [ ] Ready for release
- [ ] Documentation approved

**PO Signature:** _________________ **Date:** _______

---

## 📚 References

- [Home Assistant Add-on Development Guide](https://developers.home-assistant.io/docs/add-ons)
- [S6-Overlay Documentation](https://github.com/just-containers/s6-overlay)
- [Bashio Function Reference](https://github.com/hassio-addons/bashio)
- Add-on DOCS.md (included in repository)
- config.yaml schema reference

---

**Last Updated:** 2026-01-16
**Checklist Version:** 1.0.0
