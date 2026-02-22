## Release 4.0.4

- Event flow updated for faster actions: when AI confirms person presence from collage analysis, MQTT notification is published immediately.
- MP4 generation is kept in background after notification, so event alerts are no longer delayed by video creation.
- `postbuffer_seconds` is fixed to `2.0s` in backend and hidden from UI to keep behavior stable and predictable across users.

