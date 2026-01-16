## [1.0.1] - 2026-01-16

### Added
- Complete Home Assistant Add-on integration with s6-overlay service management
- S6-overlay v3.1.5.0 for proper service lifecycle management
- Container initialization script (01-init.sh) with bashio logging and prerequisite validation
- Service run and finish scripts for graceful startup and shutdown
- Comprehensive DOCS.md with installation, configuration, and troubleshooting guides
- Ingress support for seamless Home Assistant UI integration
- MQTT auto-discovery integration with Home Assistant
- Options UI schema validation for all configuration parameters
- Panel icon and title customization (mdi:motion-sensor)

### Changed
- Dockerfile updated to use s6-overlay init system instead of direct CMD execution
- Enhanced config.yaml with complete Home Assistant add-on metadata
- Added bashio dependency for Home Assistant integration functions

### Fixed
- Proper service management with supervised process lifecycle
- Enhanced error handling and logging for Home Assistant environment

## [1.0.0] - 2026-01-16

### Added
- Web UI specifications and design
- Standalone Mode specifications
- Complete project structure and specifications for thermal vision AI capabilities
- Updated project documentation with thermal-vision-ai branding and key differentiators

### Changed
- Updated .gitignore to track specification files in version control
- Enhanced CONTEXT.md with thermal-vision-ai branding information