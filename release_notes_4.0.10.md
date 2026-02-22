## Release 4.0.10

- Changed `Reset Defaults` in Settings to reset only the active page section (no full wipe).
- Added a separate `Factory Default (Full Reset)` button with extra `FACTORY` typed confirmation.
- Fixed camera/performance presets so they no longer overwrite `event` settings.
- Added media guard to skip collage/video generation when no person bbox exists in the event window.
- Applied temporal consistency tuning (`min_consecutive_frames=2`, `max_gap_frames=2`) in both worker modes.

