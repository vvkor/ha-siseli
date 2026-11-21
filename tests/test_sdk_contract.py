"""Contract tests against the real python-siseli package.

The rest of the suite replaces ``siseli`` with a fake module, so these tests run
the real SDK in a separate interpreter and check that everything this
integration relies on still exists with the expected shape.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from custom_components.siseli.config_entity import translation_key_for
from custom_components.siseli.sensor import SENSORS

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "siseli"

_PROBE = r"""
import importlib.metadata as metadata
import inspect
import json
import siseli
from siseli import state

client = siseli.SiseliClient
payload = {
    "version": metadata.version("python-siseli"),
    "exports": sorted(n for n in dir(siseli) if not n.startswith("_")),
    "client_methods": sorted(n for n in dir(client) if not n.startswith("_")),
    "client_init": sorted(inspect.signature(client.__init__).parameters),
    "safe_set": sorted(inspect.signature(client.safe_set_device_config).parameters),
    "sensor_keys": sorted(state._parse_device_state({}).to_sensor_data()),
    "device_info_keys": sorted(state._parse_device_state({}).to_device_info()),
    "specs": [
        {
            "key": spec.key,
            "kind": spec.kind.value,
            "risk": spec.risk.name.lower(),
            "options": dict(spec.options or {}),
            "minimum": spec.minimum,
            "maximum": spec.maximum,
            "step": spec.step,
            "scales_with_battery": spec.scales_with_battery,
        }
        for spec in siseli.CONFIG_SPECS.values()
    ],
    "access_names": sorted(m.lower() for m in siseli.ConfigAccess.__members__),
    "write_statuses": sorted(s.value for s in siseli.ConfigWriteStatus),
    "rate_limit_is_network": issubclass(siseli.RateLimitError, siseli.NetworkError),
    "invalid_response_is_network": issubclass(
        siseli.InvalidResponseError, siseli.NetworkError
    ),
    "auth_is_network": issubclass(siseli.AuthenticationError, siseli.NetworkError),
}
print(json.dumps(payload))
"""


@pytest.fixture(scope="module")
def sdk() -> dict:
    """Return facts about the real SDK, gathered in an isolated interpreter."""
    result = subprocess.run(
        [sys.executable, "-I", "-c", _PROBE],
        capture_output=True,
        text=True,
        check=False,
        cwd="/",
    )
    if result.returncode != 0:
        pytest.fail(f"The real python-siseli could not be probed:\n{result.stderr}")
    return json.loads(result.stdout)


def _imported_sdk_names() -> set[str]:
    """Collect every name the integration imports from the ``siseli`` package."""
    names: set[str] = set()
    for path in COMPONENT.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module == "siseli":
                names.update(alias.name for alias in node.names)
    return names


def test_installed_sdk_matches_the_pinned_requirement(sdk: dict) -> None:
    """manifest.json, requirements_test.txt and the installed SDK agree."""
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    pins = {r for r in manifest["requirements"] if r.startswith("python-siseli==")}
    test_pins = {
        line.strip()
        for line in (ROOT / "requirements_test.txt").read_text().splitlines()
        if line.startswith("python-siseli==")
    }

    assert pins == test_pins == {f"python-siseli=={sdk['version']}"}


def test_everything_imported_from_the_sdk_exists(sdk: dict) -> None:
    """Every ``from siseli import ...`` in the integration resolves."""
    assert _imported_sdk_names() <= set(sdk["exports"])


def test_client_api_used_by_the_integration_exists(sdk: dict) -> None:
    """Client methods and constructor options used by the integration exist."""
    assert {
        "authenticate",
        "get_all_devices",
        "get_device_state",
        "get_device_energy_totals",
        "get_cached_device_configs",
        "safe_set_device_config",
    } <= set(sdk["client_methods"])
    assert {"account", "password", "open_auth"} <= set(sdk["client_init"])
    assert {"key", "value", "access", "battery_nominal_voltage"} <= set(
        sdk["safe_set"]
    )


def test_exception_hierarchy_keeps_throttling_out_of_reauth(sdk: dict) -> None:
    """429 is a retryable network error; auth errors stay separate."""
    assert sdk["rate_limit_is_network"]
    assert not sdk["auth_is_network"]
    # InvalidResponseError is deliberately caught on its own by the integration.
    assert not sdk["invalid_response_is_network"]


def test_every_sensor_is_provided_by_the_sdk(sdk: dict) -> None:
    """Each sensor key is a real telemetry key (or added by the coordinator)."""
    coordinator_keys = {"pv_generated_energy_total"}
    keys = {description.key for description in SENSORS}

    assert keys - coordinator_keys <= set(sdk["sensor_keys"])


def test_deprecated_sensor_keys_are_not_used(sdk: dict) -> None:
    """The deprecated ``load_apparent_power`` alias must not be exposed."""
    assert "load_apparent_power" not in {description.key for description in SENSORS}


def test_device_info_keys_exist(sdk: dict) -> None:
    """The device registry fields come from real SDK keys."""
    assert {"machine_type", "firmware_version"} <= set(sdk["device_info_keys"])


def test_access_levels_match_the_integration_options(sdk: dict) -> None:
    """Every access level offered in the options exists in the SDK."""
    assert {"safe", "advanced", "critical"} <= set(sdk["access_names"])
    assert {"applied", "unknown"} <= set(sdk["write_statuses"])


def test_real_config_specs_are_fully_supported(sdk: dict) -> None:
    """Every real SDK setting maps to a platform, a valid translation and metadata."""
    translations = json.loads((COMPONENT / "strings.json").read_text("utf-8"))["entity"]
    on_off = {"0": "Disable", "1": "Enable"}
    seen: set[str] = set()

    for spec in sdk["specs"]:
        if spec["kind"] == "number":
            platform = "number"
            assert None not in (spec["minimum"], spec["maximum"], spec["step"]), spec
        else:
            assert spec["kind"] == "enum", spec
            assert spec["options"], spec
            platform = "switch" if spec["options"] == on_off else "select"
        assert spec["risk"] in {"safe", "advanced", "critical"}, spec

        key = translation_key_for(spec["key"])
        assert re.fullmatch(r"[a-z0-9_-]+", key), key
        assert key in translations[platform], f"missing {platform} translation {key}"
        seen.add(key)

    assert len(seen) == len(sdk["specs"])
