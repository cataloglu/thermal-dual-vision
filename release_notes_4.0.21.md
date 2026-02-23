## Release 4.0.21

- Added `thermal_pseudocolor_fallback` (dynamic range normalization + colormap) to improve thermal detections in low-contrast scenes.
- Added `class_agnostic_recovery` in thermal fallback chain: if person mapping yields zero, model boxes from any class are promoted as `person_candidate` for downstream AR/zone filtering.
- Added `class_diag` summary in fallback logs to show top class distribution when thermal detection still fails.
- Applied the same thermal recovery and diagnostics path in both threading and multiprocessing workers.

