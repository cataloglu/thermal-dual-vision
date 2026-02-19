# Test Plan

## Automated Tests

```bash
python -m pytest          # full suite (174 tests as of v3.10.79)
python -m pytest -q       # quiet summary only
```

Test categories (pytest markers):
- `unit` — config validation, settings service, event pipeline
- `integration` — API endpoints, camera CRUD, event creation
- `slow` — retention, benchmark

---

## Manual Smoke Test (after each release)

### Backend API
```bash
# Health
curl http://localhost:8000/api/health

# Settings round-trip
curl http://localhost:8000/api/settings
curl -X PUT http://localhost:8000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"detection": {"confidence_threshold": 0.35}}'
curl http://localhost:8000/api/settings   # verify change persisted
```

### UI Settings Tabs (save each one)

| Tab | Action | Expected |
|---|---|---|
| Cameras | Add → Test → Save | Camera appears in list |
| Camera Settings | Change confidence → Save | Toast + value persists after reload |
| Zones | Draw polygon → Save Zone | Zone appears in saved list |
| Events | Change cooldown → Save | Value persists |
| Media | Change retention → Save | Value persists |
| AI | Enter key → Test → Save | Key masked after save |
| Telegram | Enter token → Test | Test message received |
| MQTT | Enable → Save | Status panel shows broker connection |
| Appearance | Switch language | UI language changes instantly |

### Persist Test
1. Save a setting via UI
2. Restart backend
3. `GET /api/settings` — verify value is still there

### Validation Errors
```bash
# Should return 422
curl -X PUT http://localhost:8000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"detection": {"confidence_threshold": 99}}'
```

---

## Regression Checklist (critical paths)

- [ ] Person detection triggers event creation (collage + MP4)
- [ ] Telegram notification sends with correct image + video
- [ ] MQTT publishes `binary_sensor` + `sensor` on event
- [ ] Live view loads (go2rtc or snapshot fallback)
- [ ] Retention worker deletes old events within disk limit
- [ ] AI summary generated when API key set and valid
- [ ] DB migration runs cleanly on fresh install and upgrade
