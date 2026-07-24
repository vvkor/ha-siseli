# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.2.0]

### Added

- Phase 2: sensor platform with 14 inverter telemetry entities
  - Battery: state of charge, voltage, current, power
  - PV: voltage, current, power
  - Grid: voltage, frequency, power
  - Output: voltage, frequency
  - Load power
  - Inverter state
- Sensor entities use stable `unique_id`, `device_info`, and correct HA `device_class`/`state_class`/units
- Entities become `unavailable` automatically on coordinator update failure
- Platform forwarding wired in `async_setup_entry` and `async_unload_entry`
- Phase 3 reliability features: options flow, coordinator retry/backoff, diagnostics redaction, and CI validation
- Phase 4 release readiness docs and repository templates for HACS and Home Assistant maintenance

---

## [0.1.0]

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
