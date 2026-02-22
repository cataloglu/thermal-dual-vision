## Release 4.0.8

- Reduced reconnect noise in threading detector by adding stale gate debounce (requires consecutive stale checks).
- Added reconnect cooldown to avoid rapid repeated reconnect attempts on short frame hiccups.
- Reconnect log severity lowered from warning to info for expected transient recoveries.

