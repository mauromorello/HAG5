import logging
import os
import shutil

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.components.http import HomeAssistantView
from aiohttp import web

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Imposta l'endpoint e la cartella (in config) dove salveremo i file caricati
UPLOAD_URL = "/api/haghost5/upload_gcode"
UPLOAD_DIR_NAME = "gcodes"


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the integration via YAML (not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up the integration from a config entry."""
    ip_address = config_entry.data["ip_address"]
    _LOGGER.debug("Setting up HAGhost5 integration for IP: %s", ip_address)

    # 1) Registra il dispositivo esplicitamente
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, ip_address)},
        name=f"Printer ({ip_address})",
        manufacturer="HAGhost5",
        model="3D Printer",
        sw_version="1.0"
    )

    # 2) Avvia la piattaforma dei sensori
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "sensor")
    )

    # 3) Registra la View per l'upload del file GCODE
    #    (richiede che hass.http sia disponibile)
    hass.http.register_view(GCodeUploadView())

    # 4) Copia la pagina HTML in config/www/hag5_upload.html
    copy_upload_page(hass)

    # 5) Crea (se non esiste) la cartella 'gcodes' dove verranno salvati i file
    gcode_path = hass.config.path(UPLOAD_DIR_NAME)
    if not os.path.exists(gcode_path):
        os.makedirs(gcode_path, exist_ok=True)
        _LOGGER.info("Created folder for GCODE files at: %s", gcode_path)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload the integration."""
    # Se tu avessi inizializzato hass.data[DOMAIN] in async_setup_entry,
    # potresti fare un pop, tipo: hass.data[DOMAIN].pop(entry.entry_id, None)
    # ma non sembra che tu lo stia facendo, quindi lascio così:

    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return True


def copy_upload_page(hass: HomeAssistant):
    """
    Copia il file 'hag5_upload.html' dalla cartella custom_components/haghost5/web/
    in config/www/hag5_upload.html, in modo che sia accessibile via /local/hag5_upload.html.
    """
    src_file = hass.config.path("custom_components/haghost5/web/hag5_upload.html")
    dst_dir = hass.config.path("www")
    dst_file = os.path.join(dst_dir, "community/haghost5/hag5_upload.html")

    try:
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copyfile(src_file, dst_file)
        _LOGGER.info("Copied hag5_upload.html to %s", dst_file)
    except Exception as e:
        _LOGGER.error("Error copying hag5_upload.html: %s", e)


class GCodeUploadView(HomeAssistantView):
    """
    View per gestire l'upload di file GCODE su /api/haghost5/upload_gcode
    Esempio di form:
      <form method="POST" action="/api/haghost5/upload_gcode" enctype="multipart/form-data">
        <input type="file" name="file" />
        <button type="submit">Invia</button>
      </form>
    """

    url = UPLOAD_URL
    name = "api:haghost5:upload_gcode"
    requires_auth = True  # Richiede login su HA

    async def post(self, request):
        """Handle POST request for file upload."""
        hass = request.app["hass"]

        data = await request.post()
        file_field = data.get("file")
        if not file_field:
            return web.Response(text="No file provided", status=400)

        filename = file_field.filename
        _LOGGER.info("Received GCODE file: %s", filename)

        file_content = file_field.file.read()

        # Salviamo nella cartella config/gcodes/
        save_dir = hass.config.path(UPLOAD_DIR_NAME)
        save_path = os.path.join(save_dir, filename)

        try:
            with open(save_path, "wb") as f:
                f.write(file_content)
        except Exception as e:
            _LOGGER.error("Error writing file: %s", e)
            return web.Response(text=f"Error writing file: {e}", status=500)

        return web.Response(text=f"File {filename} uploaded successfully.")
