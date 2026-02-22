## Release 4.0.9

- Fixed collage event highlight: removed full-frame blue border and kept marker on person bbox only.
- Restored user control for `min_event_duration`; removed forced `1.5s` override.
- Set event cooldown default to `60s` while keeping user-changed values untouched.
- Removed settings sanitize rules that were overriding saved user preferences during updates.
- Added protection to prevent masked secrets (`***REDACTED***`) from overwriting real saved secrets.

