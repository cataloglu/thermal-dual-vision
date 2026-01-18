# External Integrations

This document defines optional external system integrations.

## Target systems
- Home Assistant (native)
- MQTT brokers (generic)
- Telegram (alerts)
- Webhooks (generic HTTP POST)

## Integration points
- Event publishing pipeline (`BaseEvent` output)
- Health/ready endpoints
- Notification layer (Telegram/MQTT)

## Security & authentication
- Webhook: HMAC signature header (`X-Signature`)
- MQTT: username/password or TLS
- Telegram: bot token + chat allowlist

## MVP scope
- Expose webhook sink (POST JSON event payload)
- Leave advanced retries and batching out of scope
