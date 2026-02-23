## Release 4.0.22

- Fixed false alarms introduced by `4.0.21` thermal class-agnostic recovery.
- Class-agnostic step is now diagnostics-only (`class_agnostic_diag`) and no longer promotes non-person boxes into the event path.
- Keeps `class_diag` root-cause visibility while stopping fake person event spam.

