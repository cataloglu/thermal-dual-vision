## Release 4.0.14

- Fixed ffprobe resolution probing to use the configured RTSP transport (`tcp/udp`) consistently.
- Made ffprobe output parsing robust against mixed diagnostic lines (such as `461 Unsupported transport`).
- Reduced noisy startup ffprobe parse errors while keeping camera open fallback behavior intact.

