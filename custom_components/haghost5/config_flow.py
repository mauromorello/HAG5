import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

class HAGhost5ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for HAGhost5."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Validazione input
            ip_address = user_input.get("ip_address")
            if not self._is_valid_ip(ip_address):
                errors["ip_address"] = "invalid_ip"
            else:
                return self.async_create_entry(
                    title=f"Printer ({ip_address})", data=user_input
                )

        data_schema = vol.Schema(
            {vol.Required("ip_address"): str}
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """Check if the IP address is valid."""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
