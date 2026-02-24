## Release 4.0.29

- Hardened AI gating so AI-rejected events are never treated as confirmed in downstream notify/publish paths.
- Added a single source-of-truth helper for AI confirmation checks to eliminate path inconsistencies.
- Made AI confirmation parsing conservative for ambiguous responses to reduce false-alarm approvals.

