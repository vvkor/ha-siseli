# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.2.1] - 2026-10-12

### Added

- Optional inverter configuration controls generated from the SDK allowlist, with writes disabled by default, configurable risk tiers, battery-voltage scaling, serialized verified writes, and a separate 15-minute refresh. Controls are exposed as switch, select and number entities and require `python-siseli` 0.2.5.
- Lifetime PV generated energy sensor (kWh, `total_increasing`) for the Home Assistant Energy dashboard, refreshed every 15 minutes instead of on every poll.
- Sensors for readable inverter mode, load percentage, rated apparent power, heat-sink temperature, bus voltage, charging/mains/load statuses, source priorities and battery type; diagnostic ones are categorised as diagnostic. The raw `inverter_state` entity is unchanged.
- Device registry model and firmware version from the SDK; diagnostics include device identification.
- Pins `python-siseli==0.2.5` in the manifest and test requirements (adds `get_device_energy_totals`, extended `to_sensor_data`/`to_device_info` and the safe-write config API).

### Fixed

- Use SDK-normalized semantic telemetry for sensor entities; raw API field mapping, power unit conversion, and battery calculations are owned by `python-siseli`.
- Convert reported kW power values to W in the SDK and ignore invalid numeric telemetry.
- Remove the grid-power entity because no confirmed API field provides its value.
- Remove the output source priority configuration control: SDK 0.2.5 rejects writes for that unverified key. The read-only `Output source priority` sensor remains.

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
