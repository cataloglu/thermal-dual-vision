## Release 4.0.25

- Removed thermal `class_agnostic_diag` fallback path to stop recurring non-person class spam (`car`, `traffic light`, `train`) and cut unnecessary extra inference work.
- Added thermal motion hysteresis with separate activate/deactivate thresholds to reduce `active/idle` flicker near threshold boundaries.
- Net effect: cleaner logs, steadier thermal motion gating, and less noisy fallback behavior on OpenVINO.

