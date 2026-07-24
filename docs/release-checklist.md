# Release checklist

## Pre-release

- [ ] `custom_components/siseli/manifest.json` version matches the intended release number.
- [ ] `CHANGELOG.md` contains a `## [X.Y.Z]` section for the release.
- [ ] `README.md`, `SUPPORT.md`, and templates reflect the current Home Assistant UI flow.
- [ ] `ruff check custom_components/` passes.
- [ ] `python -m pytest tests/ --tb=short -q` passes.
- [ ] No secrets were introduced in documentation, templates, or workflow changes.

## Publish

- [ ] Create and push an annotated tag in the format `vX.Y.Z`.
- [ ] Confirm the GitHub release workflow succeeds.
- [ ] Confirm the release body contains the matching changelog section.

## Post-release validation

- [ ] Install the new release in a clean Home Assistant instance through HACS.
- [ ] Upgrade an existing installation through HACS and confirm entities/devices stay stable.
- [ ] Reconfigure credentials through the existing UI flow if reauth is triggered.
- [ ] Roll back to the previous published release in HACS and confirm startup succeeds after restart.
- [ ] Check that README instructions, compatibility notes, and release assets match the published release.
