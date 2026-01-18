# Pipeline Plugin System

This document defines the plugin system and stage registry approach for pipelines.

## Goals
- Provide a stable, minimal plugin API for pipeline stages
- Centralize stage discovery and registration
- Keep compatibility with existing pipelines

## Plugin loading approach
- Plugins are simple Python modules that register stages on import.
- The application loads plugins by import path (string), defined in config or env.
- Example load flow:
  1) Read `PIPELINE_PLUGINS` from env (comma-separated).
  2) Import each module path.
  3) Module import registers one or more stages into the registry.

## Stage registry responsibilities
- Register a stage by name and return a callable factory.
- Prevent duplicate names.
- Provide a read-only view of registered stages.

## Extension points
- New stage types can implement the `Stage` protocol.
- Stage factories can read configuration from `Config`.
- Pipelines may compose stages by name to build custom flows.

## Backwards compatibility plan
- Existing pipelines continue to work without any plugins.
- Registry provides a default no-op stage for missing optional stages.
- New stages are opt-in via plugin registration.
