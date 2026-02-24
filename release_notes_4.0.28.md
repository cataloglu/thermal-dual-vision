## Release 4.0.28

- Expanded `DETECT_PIPELINE` diagnostics to separate `ar` (aspect-ratio), `qual` (thermal quality gate), and `zone` drops so the root cause is visible from logs.
- Relaxed thermal bbox quality floors slightly to avoid dropping low-confidence fallback recoveries.
- Normalized bbox coordinates before aspect-ratio checks to prevent inverted boxes from being filtered incorrectly.

