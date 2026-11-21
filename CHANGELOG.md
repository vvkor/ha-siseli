# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.3.3] - 2026-11-21

### Fixed

- Stop calling the deprecated `device_registry.async_get_device`, which logged a Home Assistant deprecation warning on every start.

---

## [0.3.2] - 2026-11-21

### Fixed

- Reloading or restarting Home Assistant while the inverter is offline no longer leaves the integration in Home Assistant's setup-retry back-off (up to 10 minutes). The entry now loads with unavailable entities and recovers on the next regular poll as soon as the inverter reconnects. Cloud or login failures still use the normal setup retry.
- Model and firmware are no longer erased from the device registry when the integration starts while the inverter is offline, and they are filled in as soon as the inverter reports them.

---

## [0.3.1] - 2026-11-21

### Changed

- Update the pinned `python-siseli` dependency to 0.3.0. The integration is compatible with its breaking changes (it uses no datetimes from the API and treats `RateLimitError` as a normal retryable failure).
- Create the SDK client with `open_auth=True` instead of attaching the request-signing hook manually.
- Malformed cloud responses (`InvalidResponseError`) are handled as regular update failures, and as a connection error in the config flow.
- The "Rated apparent power" sensor now uses the SDK's `rated_apparent_power` key instead of the deprecated `load_apparent_power` alias. Existing entities are migrated automatically and keep their entity ID and history.
- Battery voltage settings are cross-checked against the live battery voltage by the SDK; a rejected write now tells the user to check that the inverter is online and that the battery nominal voltage option matches.

### Added

- Contract tests that run against the real `python-siseli` package and verify imports, client API, telemetry keys, configuration specs and translations, so SDK changes are caught in CI.

---

## [0.3.0] - 2026-11-21

### Fixed

- Configuration entities (switch, select, number) now recover right after the inverter comes back online instead of waiting for the 15-minute refresh or an integration reload: a refresh is requested when telemetry recovers, and failed or empty refreshes are retried every minute.
- Cloud API errors such as `Device is offline` (71000) are handled as normal update failures instead of logging an "Unexpected error" traceback on every poll.
- A cloud API error while reading lifetime energy counters no longer fails the whole telemetry update.
- Diagnostics no longer include the account name (the config entry title).
- Re-authentication can no longer re-point an entry to a different Siseli account.
- Translation keys of configuration entities are now lowercase snake_case, as hassfest requires (entity IDs and unique IDs are unchanged).
- The minimum Home Assistant version is now 2024.11 (set in `hacs.json`), which the code already required (`ConfigFlowResult`, `data_updates` in reauth).

### Added

- Reconfigure flow to change the account password without waiting for a failed login.
- A warning is logged when the account has more than one device, since only the first is monitored.

### Changed

- The initial configuration refresh runs as a config-entry background task and is cancelled on unload.
- Sensor and configuration entities share one device-info builder.
- Development: `.gitignore` added and committed bytecode removed; CI runs on Python 3.13 with the current Home Assistant test plugin, lints tests, reports coverage, and runs hassfest and HACS validation; test dependencies refreshed and `python-siseli` pinned to 0.2.6.

### Changed

- Update the pinned `python-siseli` dependency to 0.2.6, including the corrected configuration request payloads.

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
