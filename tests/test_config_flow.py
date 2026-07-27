"""Tests for the Siseli config flow."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.siseli.config_flow import SiseliConfigFlow, _validate_credentials
from custom_components.siseli.const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

from .conftest import (
    MOCK_PASSWORD,
    MOCK_USERNAME,
    AuthenticationError,
    NetworkError,
)

# ---------------------------------------------------------------------------
# Config flow — user step
# ---------------------------------------------------------------------------


async def test_user_step_success(hass: HomeAssistant) -> None:
    """Test successful credential entry creates a config entry."""
    with patch(
        "custom_components.siseli.config_flow._validate_credentials",
        return_value={"title": MOCK_USERNAME},
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_USERNAME
    assert result["data"] == {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD}


async def test_user_step_normalizes_username_before_validation(
    hass: HomeAssistant,
) -> None:
    """Test username normalization before unique ID and validation."""
    user_input = {
        CONF_USERNAME: f"  {MOCK_USERNAME}  ",
        CONF_PASSWORD: MOCK_PASSWORD,
    }

    with (
        patch(
            "custom_components.siseli.config_flow._validate_credentials",
            return_value={"title": MOCK_USERNAME},
        ) as mock_validate_credentials,
        patch.object(
            SiseliConfigFlow,
            "async_set_unique_id",
            autospec=True,
            wraps=SiseliConfigFlow.async_set_unique_id,
        ) as mock_set_unique_id,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input,
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_USERNAME
    assert result["data"] == {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD}
    mock_validate_credentials.assert_awaited_once_with(
        hass,
        {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
    )
    assert mock_set_unique_id.await_args.args[1] == MOCK_USERNAME


async def test_user_step_invalid_auth(hass: HomeAssistant) -> None:
    """Test that invalid credentials show the correct error."""
    user_input = {
        CONF_USERNAME: f"  {MOCK_USERNAME}  ",
        CONF_PASSWORD: MOCK_PASSWORD,
    }
    with patch(
        "custom_components.siseli.config_flow._validate_credentials",
        side_effect=AuthenticationError("bad creds"),
    ) as mock_validate_credentials:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input,
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    mock_validate_credentials.assert_awaited_once_with(
        hass,
        {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
    )


async def test_user_step_invalid_auth_logs_normalized_username(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test auth failure logging uses normalized username without password."""
    user_input = {
        CONF_USERNAME: f"  {MOCK_USERNAME}  ",
        CONF_PASSWORD: MOCK_PASSWORD,
    }
    caplog.set_level(logging.WARNING)

    with patch(
        "custom_components.siseli.config_flow._validate_credentials",
        side_effect=AuthenticationError("bad creds"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input
        )

    assert result["type"] == FlowResultType.FORM
    assert "Siseli authentication failed for username" in caplog.text
    assert MOCK_USERNAME in caplog.text
    assert "bad creds" in caplog.text
    assert MOCK_PASSWORD not in caplog.text


async def test_user_step_cannot_connect(hass: HomeAssistant) -> None:
    """Test that connection errors show the correct error."""
    with patch(
        "custom_components.siseli.config_flow._validate_credentials",
        side_effect=NetworkError("timeout"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_step_unexpected_error(hass: HomeAssistant) -> None:
    """Test that unexpected exceptions show the unknown error key."""
    with patch(
        "custom_components.siseli.config_flow._validate_credentials",
        side_effect=RuntimeError("oops"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_validate_credentials_creates_client_in_executor(
    hass: HomeAssistant,
) -> None:
    """Credential validation creates client via executor job."""
    mock_client = AsyncMock()
    mock_client.authenticate = AsyncMock()
    with patch.object(
        hass,
        "async_add_executor_job",
        new=AsyncMock(return_value=mock_client),
    ) as mock_add_executor_job:
        info = await _validate_credentials(
            hass,
            {
                CONF_USERNAME: f"  {MOCK_USERNAME}  ",
                CONF_PASSWORD: MOCK_PASSWORD,
            },
        )

    mock_add_executor_job.assert_awaited_once()
    mock_client.authenticate.assert_awaited_once()
    client_factory = mock_add_executor_job.await_args.args[0]
    assert client_factory.keywords["account"] == MOCK_USERNAME
    assert info == {"title": MOCK_USERNAME}


async def test_user_step_already_configured(hass: HomeAssistant) -> None:
    """Test that a duplicate account is rejected."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_USERNAME,
        data={CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.siseli.config_flow._validate_credentials",
        return_value={"title": MOCK_USERNAME},
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: f"  {MOCK_USERNAME}  ",
                CONF_PASSWORD: MOCK_PASSWORD,
            },
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# ---------------------------------------------------------------------------
# Reauth flow
# ---------------------------------------------------------------------------


async def test_reauth_success(hass: HomeAssistant) -> None:
    """Test successful reauthentication updates the entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_USERNAME,
        data={CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.siseli.config_flow._validate_credentials",
            return_value={"title": MOCK_USERNAME},
        ) as mock_validate_credentials,
        patch(
            "custom_components.siseli.coordinator.SiseliClient",
        ) as mock_client_class,
    ):
        mock_client_class.return_value.get_all_devices = AsyncMock(return_value=[])
        mock_client_class.return_value.get_device_state = AsyncMock()
        result = await entry.start_reauth_flow(hass)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: f"  {MOCK_USERNAME}  ",
                CONF_PASSWORD: "new_password",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    mock_validate_credentials.assert_awaited_once_with(
        hass,
        {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: "new_password"},
    )
    assert entry.data == {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: "new_password"}


async def test_reauth_invalid_auth(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that invalid credentials during reauth show the correct error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_USERNAME,
        data={CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
    )
    entry.add_to_hass(hass)

    user_input = {
        CONF_USERNAME: f"  {MOCK_USERNAME}  ",
        CONF_PASSWORD: MOCK_PASSWORD,
    }
    caplog.set_level(logging.WARNING)

    with patch(
        "custom_components.siseli.config_flow._validate_credentials",
        side_effect=AuthenticationError("HTTP 401: invalid credentials"),
    ) as mock_validate_credentials:
        result = await entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input,
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    mock_validate_credentials.assert_awaited_once_with(
        hass,
        {CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
    )
    assert "Siseli re-authentication failed for username" in caplog.text
    assert MOCK_USERNAME in caplog.text
    assert "HTTP 401: invalid credentials" in caplog.text
    assert MOCK_PASSWORD not in caplog.text


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------


async def test_options_flow_default(hass: HomeAssistant) -> None:
    """Test options flow shows the default polling interval."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_USERNAME,
        data={CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
        options={},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    schema_keys = [str(k) for k in result["data_schema"].schema]
    assert CONF_SCAN_INTERVAL in schema_keys


async def test_options_flow_update_interval(hass: HomeAssistant) -> None:
    """Test that the options flow saves a custom polling interval."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_USERNAME,
        data={CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
        options={},
    )
    entry.add_to_hass(hass)
    new_interval = 60

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: new_interval},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_SCAN_INTERVAL: new_interval}


@pytest.mark.parametrize("bad_value", [MIN_SCAN_INTERVAL - 1, MAX_SCAN_INTERVAL + 1])
async def test_options_flow_rejects_out_of_range(
    hass: HomeAssistant, bad_value: int
) -> None:
    """Test that out-of-range polling intervals are rejected by voluptuous."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_USERNAME,
        data={CONF_USERNAME: MOCK_USERNAME, CONF_PASSWORD: MOCK_PASSWORD},
        options={},
    )
    entry.add_to_hass(hass)

    await hass.config_entries.options.async_init(entry.entry_id)

    import voluptuous as vol

    with pytest.raises(vol.Invalid):
        from custom_components.siseli.config_flow import _options_schema

        schema = _options_schema(DEFAULT_SCAN_INTERVAL)
        schema({CONF_SCAN_INTERVAL: bad_value})
