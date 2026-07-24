# Contributing to ha-siseli

Thanks for contributing to the Siseli Home Assistant integration.

## Scope

- Keep the integration **SDK-first**: Siseli Cloud API logic belongs in `python-siseli`, not in this repository.
- Keep the HA layer focused on config entries, coordinators, entities, diagnostics, and HA UX.
- Preserve compatibility with supported Home Assistant and HACS requirements.

## Development setup

1. Use Python 3.12.
2. Create and activate a virtual environment.
3. Install test dependencies:

   ```bash
   pip install -r requirements_test.txt
   ```

4. Run the existing checks before opening a pull request:

   ```bash
   ruff check custom_components/
   python -m pytest tests/ --tb=short -q
   ```

## Pull requests

- Make focused changes with tests or documentation updates when behavior changes.
- Keep `README.md`, `CHANGELOG.md`, and `roadmap.md` aligned with user-visible changes.
- Do not add direct cloud calls from entities or platform code; route runtime data through the coordinator.
- If a change needs new Siseli API behavior, land it in `python-siseli` first and then consume the released SDK version here.

## Release process

1. Update `custom_components/siseli/manifest.json` with the target release version.
2. Move user-facing changes from `## [Unreleased]` into a matching `## [X.Y.Z]` section in `CHANGELOG.md`.
3. Verify `README.md`, `SUPPORT.md`, and issue templates still reflect the current UI flow and supported versions.
4. Run the validation commands above.
5. Create an annotated git tag in the format `vX.Y.Z`.
6. Push the branch and tag; the release workflow validates metadata, reruns checks, and publishes the GitHub release.
7. Complete the post-release checks in [docs/release-checklist.md](docs/release-checklist.md).
