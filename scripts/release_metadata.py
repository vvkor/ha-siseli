from __future__ import annotations

import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "custom_components" / "siseli" / "manifest.json"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
TAG_PATTERN = re.compile(r"v\d+\.\d+\.\d+")


def _read_version(tag_name: str) -> str:
    if not TAG_PATTERN.fullmatch(tag_name):
        raise SystemExit(f"Unsupported tag format: {tag_name}")
    return tag_name[1:]


def _read_changelog_section(version: str) -> str:
    changelog = CHANGELOG_PATH.read_text(encoding="utf-8")
    pattern = rf"## \[{re.escape(version)}\]\n(.*?)(?:\n## \[|\Z)"
    match = re.search(pattern, changelog, re.S)
    if not match:
        raise SystemExit(f"CHANGELOG.md is missing section ## [{version}]")

    notes = match.group(1).strip()
    return re.sub(r"\n---\s*$", "", notes).strip()


def validate(tag_name: str) -> int:
    version = _read_version(tag_name)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest["version"] != version:
        raise SystemExit(
            f"manifest.json version {manifest['version']} does not match release tag {version}"
        )

    _read_changelog_section(version)
    return 0


def notes(tag_name: str) -> int:
    version = _read_version(tag_name)
    print(_read_changelog_section(version))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in {"validate", "notes"}:
        raise SystemExit("Usage: python scripts/release_metadata.py <validate|notes> <vX.Y.Z>")

    command, tag_name = argv[1], argv[2]
    if command == "validate":
        return validate(tag_name)
    return notes(tag_name)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
