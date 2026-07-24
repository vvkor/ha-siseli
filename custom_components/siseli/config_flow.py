"""Config flow for the Siseli integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from siseli import SiseliAuthError, SiseliClient, SiseliConnectionError

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def _validate_credentials(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, Any]:
    """Validate credentials against the Siseli cloud."""
    client = SiseliClient(
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
    )
    await client.authenticate()
    return {"title": data[CONF_USERNAME]}


class SiseliConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for the Siseli integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_USERNAME])
            self._abort_if_unique_id_configured()

            try:
                info = await _validate_credentials(self.hass, user_input)
            except SiseliAuthError:
                errors["base"] = "invalid_auth"
            except SiseliConnectionError:
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
            try:
                await _validate_credentials(self.hass, user_input)
            except SiseliAuthError:
                errors["base"] = "invalid_auth"
            except SiseliConnectionError:
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
