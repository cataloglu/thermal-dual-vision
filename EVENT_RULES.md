# Event Rules & Filtering

This document defines the baseline requirements for the event rules and filtering engine.

## Rule types
- **Allow**: pass events that match criteria
- **Block**: drop events that match criteria
- **Transform**: enrich or mutate event payload fields
- **Rate-limit**: throttle events by key (e.g., camera_id)

## Priorities
- Rules have integer priority (lower runs first).
- `Block` rules override later `Allow` or `Transform` rules.
- `Transform` rules apply before `Rate-limit`.

## Filtering scope
- Inputs: `BaseEvent` fields (`event_type`, `camera_id`, `source`, `payload`)
- Filters can match:
  - event type (exact or list)
  - camera_id (exact or wildcard)
  - payload fields (equality or numeric ranges)

## Configuration format (proposal)
```yaml
rules:
  - name: "block_thermal_debug"
    type: "block"
    priority: 10
    match:
      event_type: ["health", "ready"]
      source: "pipeline"

  - name: "allow_motion"
    type: "allow"
    priority: 20
    match:
      event_type: ["motion", "alert"]

  - name: "rate_limit_camera"
    type: "rate_limit"
    priority: 30
    match:
      camera_id: "*"
    config:
      window_seconds: 5
      max_events: 3
```

## Performance considerations
- Prefer simple field matches; avoid deep payload traversal.
- Cache compiled rule predicates for reuse.
- Apply block/allow rules before transforms to reduce work.
