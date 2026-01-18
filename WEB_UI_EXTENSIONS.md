# Web UI Extensions

This document defines the camera list and event timeline requirements.

## Camera list requirements
- Show camera name, type (thermal/color/dual), and status
- Show last event timestamp per camera
- Support quick filter by type/status

## Timeline scope
- Render recent events (motion/alert/analysis)
- Group by camera_id
- Support time range selection (last 1h/24h)

## Data sources & update model
- Primary source: event store API (future)
- Poll every 5s for new events
- Pagination for history fetches

## Performance limits
- Max 200 events in memory for UI
- Lazy render for older events
