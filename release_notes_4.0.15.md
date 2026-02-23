## Release 4.0.15

- Fixed person filtering to use model class labels robustly instead of relying only on `class_id=0`.
- Added a single-class model fallback so person-only exports are not dropped due to class-id remapping.
- Targets the recurring `DETECT_PIPELINE raw=0` pattern when motion is active but detections are discarded by class mapping assumptions.

