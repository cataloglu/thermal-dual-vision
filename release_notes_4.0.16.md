## Release 4.0.16

- Added thermal-aware motion detection pipeline (separate from color flow):
  - global-mean compensation
  - controlled IIR background
  - adaptive thresholds (k1 update-control, k2 detection)
  - 2/3 temporal persistence
  - morphology + connected-components filtering
- Added short motion gate hold (~1.5s default) for NUC/reset-like global thermal jumps.
- Kept color camera motion flow unchanged to avoid cross-regression.

