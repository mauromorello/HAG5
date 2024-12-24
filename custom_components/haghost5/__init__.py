import logging
import os
import shutil

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.components.http import HomeAssistantView
from aiohttp import web

from .const import DOMAIN
# (nuovo) Importiamo la nuova view dal file api.py

from .api import GCodeUploadAndPrintView
from .api import HAG5GetGcodeFile  # <--- Import della classe

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

    # 3) Registra la View per l'upload semplice (/api/haghost5/upload_gcode)
    hass.http.register_view(GCodeUploadView())

    # 4) Copia la pagina HTML in config/www/community/haghost5/hag5_upload.html
    await hass.async_add_executor_job(copy_upload_page, hass)
    await hass.async_add_executor_job(copy_visual_page, hass)
    await hass.async_add_executor_job(copy_card_page, hass)
    #copy_upload_page(hass)
    #copy_visual_page(hass)
    #copy_card_page(hass)
    
    # 4.1) Crea directory Gcode
    path_gcodes = hass.config.path("gcodes")
    os.makedirs(path_gcodes, exist_ok=True)

    # 5) Crea (se non esiste) la cartella 'gcodes' dove verranno salvati i file
    gcode_path = hass.config.path(UPLOAD_DIR_NAME)
    if not os.path.exists(gcode_path):
        os.makedirs(gcode_path, exist_ok=True)
        _LOGGER.info("Created folder for GCODE files at: %s", gcode_path)

    # (nuovo) 6) Registriamo anche la view "upload_and_print"
    # Per ora, non passiamo sensor_ref (None). Se in futuro avrai
    # un oggetto per inviare i comandi WS, lo passerai qui.
    
    sensor_ref = next(
        (entity for entity in hass.data[DOMAIN]["entities"] if isinstance(entity, PrinterStatusSensor)), 
        None
    )
    _LOGGER.info("GCodeUploadAndPrintView: %s", sensor_ref)
    view_print = GCodeUploadAndPrintView(ip_address=ip_address, sensor_ref=sensor_ref)
    hass.http.register_view(view_print)
    hass.http.register_view(HAG5GetGcodeFile())

    #7 Registra la card
    hass.http.register_static_path(
        "/local/community/haghost5/hag5_gcode_card.js",
        hass.config.path("www/community/haghost5/hag5_gcode_card.js"),
    )
    _LOGGER.info("Risorsa Lovelace registrata manualmente.")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload the integration."""
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")

    return True


def copy_upload_page(hass: HomeAssistant):
    """
    Copia il file 'hag5_upload.html' dalla cartella custom_components/haghost5/web/
    in config/www/community/haghost5/hag5_upload.html, 
    in modo che sia accessibile via /local/community/haghost5/hag5_upload.html.
    """
    src_file = hass.config.path("custom_components/haghost5/web/hag5_upload.html")

    # Creiamo la cartella /www/community/haghost5/ se non esiste
    dst_dir = hass.config.path("www", "community", "haghost5")
    os.makedirs(dst_dir, exist_ok=True)

    dst_file = os.path.join(dst_dir, "hag5_upload.html")


    try:
        shutil.copyfile(src_file, dst_file)
        _LOGGER.info("Copied hag5_upload.html to %s", dst_file)
    except Exception as e:
        _LOGGER.error("Error copying hag5_upload.html: %s", e)

def copy_visual_page(hass: HomeAssistant):
    """
    Copia il file 'hag5_visualizer.html' dalla cartella custom_components/haghost5/web/
    in config/www/community/haghost5/hag5_visualizer.html, 
    in modo che sia accessibile via /local/community/haghost5/hag5_visualizer.html
    """
    src_file = hass.config.path("custom_components/haghost5/web/hag5_visualizer.html")

    # Creiamo la cartella /www/community/haghost5/ se non esiste
    dst_dir = hass.config.path("www", "community", "haghost5")
    os.makedirs(dst_dir, exist_ok=True)

    dst_file = os.path.join(dst_dir, "hag5_visualizer.html")



    try:
        shutil.copyfile(src_file, dst_file)
        _LOGGER.info("Copied hag5_visualizer.html to %s", dst_file)
    except Exception as e:
        _LOGGER.error("Error copying hag5_visualizer.html: %s", e)

def copy_card_page(hass: HomeAssistant):
    """
    Copia il file 'hag5_gcode_card.js' dalla cartella custom_components/haghost5/www/
    in config/www/community/haghost5/hag5_gcode_card.js,
    in modo che sia accessibile via /local/community/haghost5/hag5_gcode_card.js
    """
    src_file = hass.config.path("custom_components/haghost5/web/hag5_gcode_card.js")

    # Creiamo la cartella /www/community/haghost5/ se non esiste
    dst_dir = hass.config.path("www", "community", "haghost5")
    os.makedirs(dst_dir, exist_ok=True)

    dst_file = os.path.join(dst_dir, "hag5_gcode_card.js")

    try:
        shutil.copyfile(src_file, dst_file)
        _LOGGER.info("Copied hag5_gcode_card.js to %s", dst_file)
    except Exception as e:
        _LOGGER.error("Error copying hag5_gcode_card.js: %s", e)


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
    requires_auth = False  # Richiede login su HA

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
