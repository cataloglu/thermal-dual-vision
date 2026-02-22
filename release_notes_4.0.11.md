## Release 4.0.11

- Stabilized backend CI by installing async test runtime and using module-based pytest execution.
- Fixed log tail reading order and empty-line handling in `LogsService.get_logs()`.
- Fixed Telegram notification cleanup path causing `UnboundLocalError` on early returns.
- Updated backend tests to match current product defaults and runtime behavior.

