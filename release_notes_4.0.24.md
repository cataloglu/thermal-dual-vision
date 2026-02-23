## Release 4.0.24

- Fixed Events `Confirmed` tab filtering: now explicitly fetches only non-rejected events.
- Fixed confusing confidence display: events with `no human` / probable false alarm summaries (or AI-rejected events) now show `N/A` instead of a confidence percentage.
- Eliminates the UI inconsistency where "no human" summary and confidence percentage appeared together.

