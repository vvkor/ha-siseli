# Roadmap

This document defines the development plan for the **ha-siseli** Home Assistant integration.

Primary objective: deliver a stable integration that is suitable for **HACS** distribution and progressively aligned with the **Home Assistant Integration Quality Scale**.

The integration is built on top of **python-siseli** and follows a strict architecture:
all Siseli Cloud API logic belongs to the SDK, while this repository contains only Home Assistant specific logic.

---

# Vision

Build a reliable, maintainable and user-friendly Home Assistant integration for Siseli devices.

Key goals:

- provide stable real-time telemetry in Home Assistant;
- keep API-specific logic out of HA code (SDK-first);
- be installable and maintainable via HACS;
- reach and maintain a high Home Assistant Quality Scale level over time.

---

# Architecture Principles

## SDK-First

`ha-siseli` must not implement Siseli Cloud protocol details.

All API calls, authentication, retries, parsing, and domain logic are delegated to **python-siseli**.

## Thin HA Layer

This repository should focus on:

- Config Flow / Options Flow
- Config entries lifecycle
- DataUpdateCoordinator
- Entity model & lifecycle
- Device registry metadata
- Diagnostics
- Services (when introduced)

## Single Data Access Path

Entities must never call cloud endpoints directly.
All runtime data is provided through the Coordinator.

---

# Target Architecture

```text
User Config
    │
    ▼
Config Flow
    │
    ▼
SiseliClient (python-siseli)
    │
    ▼
DataUpdateCoordinator
    │
    ├── Sensor entities
    ├── Binary sensor entities
    └── (future) control entities/services
```

---

# HACS Readiness Requirements

These requirements are mandatory for public HACS use:

- [ ] repository contains a valid custom component in `custom_components/siseli/`
- [ ] `manifest.json` is complete and valid (domain, name, version, dependencies, requirements)
- [ ] semantic version tags are published (`vX.Y.Z`)
- [ ] clear `README.md` with install/setup/troubleshooting instructions
- [ ] `hacs.json` present and valid (if used by current HACS expectations)
- [ ] `LICENSE` included
- [ ] `CHANGELOG.md` maintained
- [ ] compatibility policy documented (supported Home Assistant versions)
- [ ] basic visuals/assets as needed by HACS listing/documentation
- [ ] no secrets in logs/docs/examples

Status:

**Planned**

---

# Home Assistant Quality Scale Strategy

The integration should progress through quality levels incrementally.
Exact level targeting depends on current implementation maturity, but each phase below includes quality gates aligned with Quality Scale expectations.

Cross-cutting quality requirements:

- [ ] config flow (no YAML-only setup)
- [ ] reauth flow
- [ ] unload support
- [ ] diagnostics with redaction
- [ ] runtime error handling and availability behavior
- [ ] tests for critical paths
- [ ] documentation for setup and known limitations
- [ ] ownership/maintenance expectations documented

---

# Development Phases

## Phase 1 — Foundation (Installable Integration)

Goal:

Deliver a working custom integration installable through HACS-compatible workflow.

Tasks:

- [ ] repository scaffold for custom component
- [ ] `manifest.json` and integration metadata
- [ ] setup/unload for config entries
- [ ] Config Flow with credential validation
- [ ] initial DataUpdateCoordinator
- [ ] dependency wiring to `python-siseli`
- [ ] baseline docs (`README`, install, configuration)

Quality gates:

- [ ] integration can be installed and configured from UI
- [ ] unload/reload works correctly
- [ ] authentication failures are user-readable
- [ ] no blocking I/O in async paths

Status:

**Planned**

---

## Phase 2 — MVP Telemetry Sensors

Goal:

Expose the most useful inverter telemetry as production-grade HA entities.

Initial sensor set:

- [ ] Battery SOC
- [ ] Battery Voltage
- [ ] Battery Current
- [ ] Battery Power
- [ ] PV Voltage
- [ ] PV Current
- [ ] PV Power
- [ ] Grid Voltage
- [ ] Grid Frequency
- [ ] Grid Power
- [ ] Output Voltage
- [ ] Output Frequency
- [ ] Load Power
- [ ] Inverter State

Entity quality requirements:

- [ ] stable `unique_id` for each entity
- [ ] proper `device_info` and device registry linkage
- [ ] correct `device_class`, `state_class`, and native units where applicable
- [ ] sensible naming and translation-ready strings
- [ ] graceful `unavailable` behavior on API/network failures

Quality gates:

- [ ] entities survive restarts/reloads without duplication
- [ ] values are mapped consistently and typed correctly
- [ ] coordinator update failures do not crash platform

Status:

**Planned**

---

## Phase 3 — Reliability, Diagnostics, and QA

Goal:

Achieve robust day-to-day behavior and measurable quality.

Tasks:

- [ ] Options Flow (e.g., polling interval within safe bounds)
- [ ] coordinator backoff/retry strategy
- [ ] explicit reauthentication flow
- [ ] diagnostics endpoint with strict secret redaction
- [ ] structured logging policy (debuggable, privacy-safe)
- [ ] user-facing repairs/errors where appropriate

Testing & CI:

- [ ] unit tests for config flow
- [ ] tests for coordinator success/failure cycles
- [ ] entity mapping tests
- [ ] regression tests for auth/token error handling
- [ ] CI: lint + type checks + tests

Quality gates:

- [ ] critical paths covered by automated tests
- [ ] diagnostics confirmed to exclude tokens/passwords
- [ ] common transient failures handled without manual recovery

Status:

**Planned**

---

## Phase 4 — HACS Production Readiness

Goal:

Prepare stable public releases and maintenance workflow.

Tasks:

- [ ] semantic release process (`vX.Y.Z`)
- [ ] release notes/changelog discipline
- [ ] documented support boundaries and compatibility matrix
- [ ] issue templates (bug report/feature request)
- [ ] contribution guidelines and development setup docs
- [ ] post-release validation checklist

Quality gates:

- [ ] clean install/upgrade path across versions
- [ ] rollback strategy documented
- [ ] user documentation matches actual UI flow
- [ ] HACS-facing metadata/docs fully consistent

Status:

**Planned**

---

## Phase 5 — Feature Expansion

Goal:

Add non-MVP capabilities after stability baseline is reached.

Features:

- [ ] historical/statistical sensors
- [ ] energy dashboard support
- [ ] alarm sensors/history
- [ ] binary sensors for status flags
- [ ] firmware information entities
- [ ] selected services/device actions

Constraints:

- API/domain logic still implemented in SDK first;
- new features require tests + docs before release;
- advanced or risky controls are opt-in.

Status:

**Planned**

---

## Phase 6 — Advanced / Experimental

Goal:

Carefully expose advanced controls only when safe and well-understood.

Candidates:

- [ ] configuration editor (subset of writable parameters)
- [ ] remote commands
- [ ] fast reporting controls
- [ ] passthrough-backed features from SDK

Safety rules:

- explicit opt-in;
- strict validation;
- clear recovery behavior;
- strong warnings in documentation.

Status:

**Not Started**

---

# Definition of Done (per phase)

A phase is complete only when:

- functionality is implemented and documented;
- tests cover successful and failure scenarios;
- no credentials/tokens appear in logs or diagnostics;
- architecture remains SDK-first (no API duplication in HA layer);
- manual validation in a real Home Assistant instance is passed;
- HACS and Quality Scale requirements relevant to the phase are met.

---

# Dependency Strategy

`ha-siseli` tracks stable `python-siseli` releases.

Rules:

- API features are implemented in SDK first;
- HA integration consumes released SDK versions;
- avoid HA-side protocol workarounds whenever possible.

---

# Guiding Principle

**python-siseli is the foundation; ha-siseli is the Home Assistant adapter.**

If a feature requires Siseli API logic, implement it in SDK first, then expose it in HA.
This keeps the integration clean, reusable, and maintainable long-term.