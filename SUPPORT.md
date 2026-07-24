# Support policy

## Supported scope

| Area | Support status | Notes |
|------|----------------|-------|
| Home Assistant Core | Supported on 2024.1+ | Minimum version is declared in `custom_components/siseli/manifest.json` |
| Installation | Supported via HACS and manual copy | HACS is the recommended path for upgrades and rollback |
| Setup flow | Supported via the UI config flow | No YAML setup is provided |
| Runtime features | Supported for released `python-siseli` capabilities exposed by this integration | HA layer stays coordinator-based |

## Unsupported scope

- Beta, dev, or nightly Home Assistant builds.
- Unreleased or locally modified `python-siseli` behavior unless the issue is reproducible on a released SDK version.
- Requests to duplicate Siseli API logic in Home Assistant instead of the SDK.
- Environment-specific support for custom local patches.

## Before opening an issue

Please collect:

- Home Assistant version
- Integration version
- Installation method (HACS or manual)
- Relevant log excerpts with secrets removed
- Diagnostics output when the problem involves runtime data or device metadata

## Maintenance expectations

- Maintainer: `@vvkor`
- Responses are best effort; reproducible bug reports with versions and diagnostics are prioritized.
- Feature requests should describe the user problem and whether the required API capability already exists in `python-siseli`.
