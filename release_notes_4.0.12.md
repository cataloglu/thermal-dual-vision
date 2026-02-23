## Release 4.0.12

- Hardened AI response formatting to prevent wrong multi-person counting in collage analysis.
- Preserved existing event MP4 when quality-gate/regeneration fails to avoid missing video artifacts.
- Added short dropout tolerance (`no_detections_grace`) and temporal recovery for borderline single-frame detections.
- Added multi-stage thermal detection fallback when motion is active but strict inference returns zero detections.
- Added thermal plain-preprocess fallback (`thermal_plain_fallback`) to recover detections lost by aggressive enhancement.
- Added thermal aspect-ratio fallback (`thermal_ar_fallback`) for wider person-like thermal blobs.
- Added `DETECT_PIPELINE` logs to expose raw -> AR -> zone filtering counts and confidence for root-cause analysis.
- Applied the same detector reliability improvements to both threading and multiprocessing workers.

