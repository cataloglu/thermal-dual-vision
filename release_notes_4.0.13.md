## Release 4.0.13

- Added thermal high-resolution fallback inference (`832x832`) when motion is active but standard passes still return zero detections.
- Added explicit `fallback_exhausted` debug logs to confirm when all detector recovery stages fail.
- Kept threading and multiprocessing detector behavior aligned for thermal miss recovery paths.

