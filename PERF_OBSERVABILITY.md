# Performance & Observability Improvements

This document outlines targets and monitoring approach for performance and observability.

## Performance targets
- Pipeline latency < 250 ms (P95)
- Event throughput > 30 events/min
- Startup time < 15s

## Resource metrics
- CPU usage (%)
- Memory RSS (MB)
- Disk IO (MB/s)
- Network throughput (KB/s)

## Observability needs
- Structured logs with correlation ids
- Health/ready endpoints for uptime checks
- Optional metrics export (Prometheus) in later phase

## Monitoring & reporting approach
- Aggregate metrics every 60 seconds
- Emit periodic status logs
- Optional webhook report for alerts
