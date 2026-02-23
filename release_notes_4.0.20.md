## Release 4.0.20

- Fixed thermal auto-mode threshold floor enforcement: thermal `min_area` floor now remains active after auto-learning updates.
- Enforced thermal warmup gate at motion decision layer to suppress early startup false activations.
- Added `thermal_raw_fallback` inference step (raw frame + lower confidence) before high-res fallback.
- Adjusted thermal confidence cap default to 0.30 for better recovery on difficult thermal scenes.

