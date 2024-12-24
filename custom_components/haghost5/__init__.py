import logging
import os
import shutil

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.components.http import HomeAssistantView
from aiohttp import web

from .const import DOMAIN
from .const import UPLOAD_URL


from .api import GCodeUploadAndPrintView
from .api import GCodeUploadView
from .api import HAG5GetGcodeFile

_LOGGER = logging.getLogger(__name__)

# Imposta l'endpoint e la cartella (in config) dove salveremo i file caricati
UPLOAD_DIR_NAME = "www/community/haghost5/gcodes"


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the integration via YAML (not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up the integration from a config entry."""
    ip_address = config_entry.data["ip_address"]
    _LOGGER.debug("Setting up HAGhost5 integration for IP: %s", ip_address)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {"entities": []}

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


    # 4) Copia la pagina HTML in config/www/community/haghost5/hag5_upload.html
    await hass.async_add_executor_job(copy_upload_page, hass)
    await hass.async_add_executor_job(copy_visual_page, hass)
    await hass.async_add_executor_job(copy_card_page, hass)
    
    # Nuovo percorso per la directory GCODE
    gcode_path = hass.config.path("www", "community", "haghost5", "gcodes")
    
    # Crea la directory se non esiste
    os.makedirs(gcode_path, exist_ok=True)
    _LOGGER.info("Created folder for GCODE files at: %s", gcode_path)


    # (nuovo) 6) Registriamo anche la view "upload_and_print"
    # Per ora, non passiamo sensor_ref (None). Se in futuro avrai
    # un oggetto per inviare i comandi WS, lo passerai qui.
    

    view_print = GCodeUploadAndPrintView(ip_address=ip_address)
    hass.http.register_view(view_print)
    hass.http.register_view(HAG5GetGcodeFile())
    hass.http.register_view(GCodeUploadView())

    #7 Registra la card
    # Registra automaticamente la risorsa per la Lovelace UI
    hass.http.register_static_path(
        "/hacspublic/hag5-gcode-card.js",  # Percorso pubblico
        hass.config.path("www/community/haghost5/hag5-gcode-card.js"),  # File nella tua configurazione
    )
    
    # Aggiungi la risorsa a Lovelace
    resources = hass.data.get("lovelace_resources")
    if resources is not None:
        # Controlla se la risorsa è già registrata
        if not any("/hacspublic/hag5-gcode-card.js" in r["url"] for r in resources.async_items()):
            resources.async_create_item(
                {"res_type": "module", "url": "/hacspublic/hag5-gcode-card.js"}
            )
            _LOGGER.info("Hag5GCodeCard aggiunta alle risorse di Lovelace.")


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

