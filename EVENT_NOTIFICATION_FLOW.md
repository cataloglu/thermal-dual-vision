# Event Production & Notification Flow

This document outlines the end-to-end flow for event production and MQTT/Telegram notifications.

## Event production points
- Motion detection stage emits `motion` events
- LLM analysis stage emits `analysis` events
- Alert stage emits `alert` events

## MQTT flow contract
- Topic prefix: `smart_motion`
- Payload: serialized `BaseEvent`
- Availability: `smart_motion/availability` with `online`/`offline`

## Telegram flow contract
- Alerts are sent for `alert` events only
- Message includes timestamp, threat level, and summary
- Optional screenshots attached when available

## Failure handling
- MQTT publish failures are logged and retried (best-effort)
- Telegram failures are logged; no retry in MVP
- Events are not dropped on notification failure

## Test/validation approach
- Unit tests for MQTT publish and Telegram send (mocked)
- E2E: verify MQTT topics and Telegram delivery manually
