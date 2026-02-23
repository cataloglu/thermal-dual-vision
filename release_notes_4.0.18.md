## Release 4.0.18

- Adjusted thermal detection start confidence to a safe range (0.25-0.38) to avoid over-strict `0.50` lock behavior.
- Added log throttling for OpenVINO thermal fallback debug lines to prevent log flooding.
- Reduced repeated `fallback_exhausted` / `thermal_highres_fallback skipped` spam while preserving diagnostics.

