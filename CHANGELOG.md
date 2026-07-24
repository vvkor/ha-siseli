# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- Phase 1 foundation: custom component scaffold under `custom_components/siseli/`
- `manifest.json` with integration metadata (domain, version, codeowners, iot_class)
- `Config Flow` with credential validation against the Siseli cloud
- Re-authentication flow for expired/revoked credentials
- `DataUpdateCoordinator` (`SiseliCoordinator`) for centralised cloud polling
- Integration setup and unload support for config entry lifecycle
- English UI translations (`strings.json`, `translations/en.json`)
- `hacs.json` for HACS compatibility
- `LICENSE` (MIT)
- Baseline `README.md` with installation and configuration instructions
