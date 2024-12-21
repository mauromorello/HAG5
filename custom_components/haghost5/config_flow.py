
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

@config_entries.HANDLERS.register(DOMAIN)
class HAGhost5ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HAGhost5."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate the input (for example, check if IP is valid)
            if self._is_valid_ip(user_input["ip_address"]):
                return self.async_create_entry(title="HAGhost5", data=user_input)
            else:
                errors["ip_address"] = "invalid_ip"

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_schema(),
            errors=errors,
        )

    @staticmethod
    @callback
    def _is_valid_ip(ip):
        """Validate the given IP address."""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    def _get_schema(self):
        """Return the data schema for the form."""
        from homeassistant.helpers import config_validation as cv
        import voluptuous as vol

        return vol.Schema({
            vol.Required("ip_address", description="IP della stampante"): cv.string,
        })

