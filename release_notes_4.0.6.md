## Release 4.0.6

- Fixed threading detector startup crash caused by detached SQLAlchemy `Camera` instances (`not bound to a Session`).
- Camera objects are now converted to safe detached snapshots before worker threads start.
- Stability improvement: prevents camera detection loops from failing right after startup in threading mode.

