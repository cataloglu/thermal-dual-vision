## Release 4.0.17

- Fixed OpenVINO incompatibility with thermal high-resolution fallback (`832x832`) that caused detection loop crashes.
- High-resolution fallback is now skipped safely when backend is OpenVINO.
- Applied the same safety guard in both threading and multiprocessing detector paths.

