"""Config flow for the Siseli integration."""

from __future__ import annotations

import logging
from functools import partial
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from siseli import AuthenticationError, NetworkError, SiseliClient

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


def _options_schema(current_interval: int) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
            ),
        }
    )


def _normalize_user_input(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize config flow user input."""
    data[CONF_USERNAME] = data[CONF_USERNAME].strip()
    return data


async def _validate_credentials(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, Any]:
    """Validate credentials against the Siseli cloud."""
    username = data[CONF_USERNAME].strip()
    client = await hass.async_add_executor_job(
        partial(
            SiseliClient,
            account=username, password=data[CONF_PASSWORD],
        )
    )
    await client.authenticate()
    return {"title": username}


class SiseliConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for the Siseli integration."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> SiseliOptionsFlow:
        """Return the options flow."""
        return SiseliOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input = _normalize_user_input(user_input)
            username = user_input[CONF_USERNAME]

            await self.async_set_unique_id(username)
            self._abort_if_unique_id_configured()

            try:
                info = await _validate_credentials(self.hass, user_input)
            except AuthenticationError:
                _LOGGER.warning(
                    "Siseli authentication failed for username '%s'",
                    username,
                )
                errors["base"] = "invalid_auth"
            except NetworkError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Siseli config flow")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauthentication confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input = _normalize_user_input(user_input)
            username = user_input[CONF_USERNAME]

            try:
                await _validate_credentials(self.hass, user_input)
            except AuthenticationError:
                _LOGGER.warning(
                    "Siseli re-authentication failed for username '%s'",
                    username,
                )
                errors["base"] = "invalid_auth"
            except NetworkError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Siseli reauth flow")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates=user_input,
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class SiseliOptionsFlow(OptionsFlow):
    """Options flow for the Siseli integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options step."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(current_interval),
        )
