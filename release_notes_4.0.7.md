## Release 4.0.7

- Auto motion thresholding was re-tuned to avoid over-shooting to max values (`min_area=2500`) too often.
- Product defaults now keep adaptive behavior calmer with `auto_multiplier=1.0` and `auto_min_area_ceiling=1800`.
- Stream stale gating is less aggressive in threading mode, reducing unnecessary reconnects during short frame hiccups.

