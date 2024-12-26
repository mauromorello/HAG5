import logging
import os
import shutil
import random
import string

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

def generate_random_token(length=8):
    """Genera un token random alfanumerico."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


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
    await hass.async_add_executor_job(copy_renderer_card_page, hass)
    await hass.async_add_executor_job(copy_gcode_loader_page, hass)
    
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
    # Registra la card
    _LOGGER.debug("Inizio registrazione della card hag5-gcode-card...")
    
    try:
        # Registra il percorso statico per la card
        hass.http.register_static_path(
            "/local/community/haghost5/hag5_gcode_card.js",  # Percorso pubblico
            hass.config.path("www/community/haghost5/hag5_gcode_card.js"),  # File nella tua configurazione
        )
        _LOGGER.info("Percorso statico registrato: /local/community/haghost5/hag5_gcode_card.js")
    except Exception as e:
        _LOGGER.error("Errore nella registrazione del percorso statico della card: %s", e)
    
    # Verifica se le risorse Lovelace sono disponibili
    resources = hass.data.get("lovelace_resources")
    if resources is not None:
        _LOGGER.debug("Risorse Lovelace trovate: %s", resources.async_items())
        try:
            # Controlla se la risorsa è già registrata
            resource_exists = any(
                "/local/community/haghost5/hag5_gcode_card.js" in r["url"] for r in resources.async_items()
            )
            if resource_exists:
                _LOGGER.info("La risorsa hag5_gcode_card.js è già registrata.")
            else:
                # Aggiungi la risorsa a Lovelace
                resources.async_create_item(
                    {"res_type": "module", "url": "/local/community/haghost5/hag5_gcode_card.js"}
                )
                _LOGGER.info("Risorsa hag5-gcode-card.js aggiunta a Lovelace.")
        except Exception as e:
            _LOGGER.error("Errore durante il controllo o la registrazione delle risorse Lovelace: %s", e)
    else:
        _LOGGER.warning(
            "Risorse Lovelace non trovate. Potrebbe essere necessario aggiungere manualmente la card nelle risorse UI."
        )
    
    _LOGGER.debug("Fine registrazione della card hag5_gcode_card.")


    # Genera un token random per forzare l'aggiornamento
    random_token = generate_random_token()
    resource_url = f"/local/community/haghost5/hag5-renderer-card/hag5-renderer-card.js?{random_token}"

    # Controlla se la risorsa è già presente
    frontend_resources = await hass.helpers.frontend.async_get_panel_resources()
    if not any(resource_url.split('?')[0] in resource["url"] for resource in frontend_resources):
        # Aggiungi la risorsa
        try:
            await hass.services.async_call(
                "frontend", "reload_themes", {}
            )  # Per assicurarsi che la UI sia aggiornata

            await hass.services.async_call(
                "frontend",
                "set_resource",
                {
                    "url": resource_url,
                    "res_type": "module",
                },
            )
            _LOGGER.info("Custom card resource added with random token: %s", resource_url)
        except Exception as e:
            _LOGGER.error("Failed to add custom card resource: %s", e)

    
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

def copy_renderer_card_page(hass: HomeAssistant):
    """
    Copia il file 'hag5-renderer-card.js' dalla cartella custom_components/haghost5/web/
    in config/www/community/haghost5/hag5-renderer-card/hag5-renderer-card.js,
    in modo che sia accessibile via /local/community/haghost5/hag5-renderer-card/hag5-renderer-card.js
    """
    src_file = hass.config.path("custom_components/haghost5/web/hag5-renderer-card.js")

    # Creiamo la cartella /www/community/haghost5/hag5-renderer-card/ se non esiste
    dst_dir = hass.config.path("www", "community", "haghost5", "hag5-renderer-card")
    os.makedirs(dst_dir, exist_ok=True)

    dst_file = os.path.join(dst_dir, "hag5-renderer-card.js")

    try:
        shutil.copyfile(src_file, dst_file)
        _LOGGER.info("Copied hag5-renderer-card.js to %s", dst_file)
    except Exception as e:
        _LOGGER.error("Error copying hag5-renderer-card.js: %s", e)

def copy_gcode_loader_page(hass: HomeAssistant):
    """
    Copia il file 'gcode_loader.js' dalla cartella custom_components/haghost5/web/
    in config/www/community/haghost5/gcode_loader.js,
    in modo che sia accessibile via /local/community/haghost5/gcode_loader.js
    """
    src_file = hass.config.path("custom_components/haghost5/web/gcode_loader.js")

    # Creiamo la cartella /www/community/haghost5/ se non esiste
    dst_dir = hass.config.path("www", "community", "haghost5")
    os.makedirs(dst_dir, exist_ok=True)

    dst_file = os.path.join(dst_dir, "gcode_loader.js")

    try:
        shutil.copyfile(src_file, dst_file)
        _LOGGER.info("Copied gcode_loader.js to %s", dst_file)
    except Exception as e:
        _LOGGER.error("Error copying gcode_loader.js: %s", e)

