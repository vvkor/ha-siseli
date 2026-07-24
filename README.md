# ha-siseli

![Siseli logo](docs/images/siseli.svg)

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![GitHub Release](https://img.shields.io/github/v/release/vvkor/ha-siseli)](https://github.com/vvkor/ha-siseli/releases)

Home Assistant custom integration for **Siseli** solar inverters.

Built on top of [python-siseli](https://github.com/vvkor/python-siseli) — all Siseli Cloud API logic lives in the SDK; this repository contains only the Home Assistant adapter layer.

---

## Features

- Cloud-based polling of inverter telemetry via the Siseli API
- UI-based setup via Config Flow (no YAML required)
- Re-authentication flow for expired credentials
- Installable via HACS

---

## Requirements

- Home Assistant 2024.1 or newer
- A Siseli cloud account with at least one registered device
- [python-siseli](https://pypi.org/project/python-siseli/) (installed automatically)

### Compatibility matrix

| Component | Supported versions | Notes |
|-----------|--------------------|-------|
| Home Assistant Core | 2024.1+ | `manifest.json` enforces the minimum supported HA version |
| HACS | Latest stable release | Recommended installation path for upgrades and rollbacks |
| Siseli SDK | `python-siseli>=0.1.0` | API and domain logic stay in the SDK |

---

## Installation

### Via HACS (recommended)

1. Open HACS in your Home Assistant instance.
2. Go to **Integrations** → click the three-dot menu → **Custom repositories**.
3. Add `https://github.com/vvkor/ha-siseli` with category **Integration**.
4. Find **Siseli** in the list and click **Download** to install the latest published `vX.Y.Z` release.
5. Restart Home Assistant.

### Manual

1. Copy the `custom_components/siseli/` directory into your Home Assistant
   `config/custom_components/` folder.
2. Restart Home Assistant.

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Siseli**.
3. Enter your Siseli cloud **username** and **password**.
4. Click **Submit** — the integration validates credentials before saving.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `invalid_auth` error during setup | Wrong username or password | Double-check your Siseli account credentials |
| `cannot_connect` error | Network issue or Siseli cloud outage | Check internet connectivity and retry |
| Integration shows as unavailable | Transient cloud error | It will recover automatically on next poll |
| Re-authentication prompt | Credentials expired or changed | Follow the re-authentication flow in Notifications |

---

## Upgrades and rollback

- Upgrade through HACS by selecting the latest published release and restarting Home Assistant.
- If a release causes regressions, roll back in HACS to the previous published release, restart Home Assistant, and reopen the issue with diagnostics attached.
- Manual installs should replace the `custom_components/siseli/` directory with the matching release contents before restart.

---

## Support boundaries

- Supported setup path: **Settings → Devices & Services → Add Integration** using the UI config flow.
- Supported runtime scope: released `python-siseli` features exposed through the coordinator-backed HA entities in this repository.
- Unsupported scope: YAML setup, beta/nightly Home Assistant builds, and HA-side Siseli API workarounds that belong in the SDK first.
- See [SUPPORT.md](SUPPORT.md) for issue triage expectations and [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow.

---

## Development

See [roadmap.md](roadmap.md) for the development plan and quality targets, [CONTRIBUTING.md](CONTRIBUTING.md) for local setup, and [docs/release-checklist.md](docs/release-checklist.md) for release validation steps.

Contributions are welcome — please open an issue or pull request.
