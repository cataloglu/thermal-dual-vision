# Environment Variables

Most configuration (AI API key, Telegram, retention, MQTT, zones, etc.) is
stored in `data/config.json` via the web UI Settings page — **not** in env vars.

Only infrastructure / runtime knobs are controlled through env vars.

---

## Variables

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `info` | Backend log level: `debug`, `info`, `warning`, `error` |
| `GO2RTC_URL` | `http://127.0.0.1:1984` | go2rtc HTTP API URL (embedded process) |
| `GO2RTC_RTSP_URL` | `rtsp://127.0.0.1:8554` | go2rtc RTSP base URL used by detector workers |
| `GO2RTC_CHECK_INTERVAL` | `10` | How often (seconds) to check go2rtc availability |
| `CORS_ORIGINS` | *(empty)* | Comma-separated allowed CORS origins (empty = same-origin only) |
| `MEDIA_MAX_CONCURRENCY` | `2` | Max parallel collage/MP4 encoding jobs |
| `FFMPEG_LOGLEVEL` | `error` | FFmpeg subprocess log level |
| `DEBUG_HEADERS` | *(empty)* | Set to `1` to log incoming request headers (dev only) |

---

## Setup (local development)

```bash
cp env.example .env
# Edit .env as needed, then:
source .env   # Linux/Mac
# or just set vars in your terminal/IDE on Windows
```

The backend reads `.env` automatically when present (via `python-dotenv` if
installed, or set them manually in your shell).

---

## What is NOT here

These are configured via the web UI and saved to `data/config.json`:

- OpenAI API key
- Telegram bot token & chat IDs
- MQTT broker settings
- Recording retention policy
- Detection model & thresholds
- All camera RTSP URLs
