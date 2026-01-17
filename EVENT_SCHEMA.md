# Event Schema

Shared event contract used by pipelines and notification layers.

## Base Event (required fields)
- `event_id` (string, required): unique id (UUID recommended)
- `event_type` (string, required): event type, see `EventType`
- `timestamp` (string, required): ISO-8601 timestamp in UTC
- `source` (string, required): event producer (e.g. `pipeline`, `mqtt`, `telegram`)
- `camera_id` (string|null, required): logical camera identifier, null if not applicable
- `payload` (object, required): event-specific payload data
- `schema_version` (string, required): schema version, default `1.0`

## Event types and required payload fields
### `motion`
- `detected` (bool): motion detected flag
- `confidence` (number, optional): confidence score (0-1 or 0-100)
- `objects` (array<string>, optional): detected objects
- `threat_level` (string, optional): threat level label

### `analysis`
- `summary` (string): short analysis summary
- `details` (string, optional): extended analysis text
- `confidence` (number, optional): analysis confidence

### `alert`
- `title` (string): alert title
- `message` (string): alert body
- `channels` (array<string>, optional): delivery channels (e.g. `mqtt`, `telegram`)

### `health`
- `status` (string): `ok` | `degraded` | `down`
- `components` (object, optional): component status map

### `ready`
- `ready` (bool): readiness indicator
- `status` (string, optional): `ok` | `degraded` | `down`

## Compatibility rules
- Pipelines emit `BaseEvent` with `event_type` + `payload` matching the contract.
- Notification layers consume `BaseEvent` without inspecting pipeline internals.
- New fields must be added under `payload` to keep backwards compatibility.

## Extension guidance
- Add new event types to `EventType` and document required payload fields.
- Avoid breaking changes by keeping `BaseEvent` fields stable.
