## Release 4.0.23

- Added thermal pre-event bbox quality filtering to reject low-confidence, very small-area, and too-short candidate boxes.
- Tightened thermal temporal consistency (`3 frames`, `max_gap=1`) and disabled single-frame temporal recovery bypass for thermal path.
- Focused on reducing fake person alarms in stable thermal scenes while preserving color camera behavior.

