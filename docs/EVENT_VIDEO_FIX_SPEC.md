# Event Video Fix Spec – Scrypted-style clean behaviour

**Context:** Project is a Home Assistant add-on. Tests run on live HA.

## Goals
- Event videos come **from recording** when possible (buffer fallback only when needed).
- Good quality (no "flush of closed file", no muddy image).
- **Single consistent timestamp** on video (no dual times).
- Retention cleans old media; recording buffer stays 1h (user does not own raw recordings).

---

## 1. MP4 source: Recording first, after segment closed
- **Problem:** Media runs 15s after event; segment still "open" → always buffer fallback.
- **Fix:** For MP4 only, wait ~55–60s after postbuffer then try `extract_clip`. On success use recording; else buffer fallback. Collage/AI/Telegram stay at 15s with buffer frames.

## 2. FFmpeg encode: Temp file instead of pipe
- **Problem:** Pipe to FFmpeg causes "flush of closed file", blacklist, then imageio (worse quality).
- **Fix:** Write frames to a temp raw file, run FFmpeg with `-i temp.raw` (size, fps). No stdin pipe.

## 3. Timestamp overlay: UTC, single format
- **Problem:** `datetime.fromtimestamp(ts)` uses local TZ; fallback uses event (UTC) → two different times on screen.
- **Fix:** Use `datetime.fromtimestamp(ts, tz=timezone.utc)` and one format (e.g. `%H:%M:%S.%f`). Single overlay only.

## 4. Retention
- No change: retention worker and recorder cleanup already handle old media and 1h recording buffer.

---
*Implementation order: 3 (timestamp) → 2 (FFmpeg) → 1 (recording-first).*
