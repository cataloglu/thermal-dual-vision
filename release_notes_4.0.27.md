## Release 4.0.27

- Widened thermal person aspect-ratio filtering to `0.08-2.50` so thermal "blob-like" boxes are not dropped as `ar=0`.
- Kept existing thermal bbox quality gating and stricter temporal requirements to avoid increasing false alarms.
- Applied consistently in both threading and multiprocessing detector workers.

