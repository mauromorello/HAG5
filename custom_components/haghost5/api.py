# api.py

import time
from homeassistant.components.http import HomeAssistantView
from aiohttp import web, ClientSession
import asyncio
import os
import logging

from .const import DOMAIN
from .const import UPLOAD_URL
from .sensor import PrinterStatusSensor

_LOGGER = logging.getLogger(__name__)

class GCodeUploadAndPrintView(HomeAssistantView):
    url = "/api/haghost5/upload_and_print"
    name = "api:haghost5:upload_and_print"
    requires_auth = False

    def __init__(self, ip_address):
        self._ip_address = ip_address

    def _get_sensor_ref(self, hass):
        sensor_ref = hass.data[DOMAIN].get("printer_status_sensor")
        if not sensor_ref or not isinstance(sensor_ref, PrinterStatusSensor):
            _LOGGER.warning("PrinterStatusSensor non trovato o non valido.")
            return None
        return sensor_ref

    async def post(self, request):
        hass = request.app["hass"]

        data = await request.post()
        file_field = data.get("file")
        if not file_field:
            return web.Response(text="No file provided", status=400)

        filename = file_field.filename
        file_bytes = file_field.file.read()

        _LOGGER.info("Received file for upload_and_print: %s", filename)

        # Salvo localmente
        gcodes_dir = hass.config.path("gcodes")
        os.makedirs(gcodes_dir, exist_ok=True)
        save_path = os.path.join(gcodes_dir, filename)
        try:
            def _write_file(path, data):
                with open(path, "wb") as f:
                    f.write(data)
            
            await hass.async_add_executor_job(_write_file, save_path, file_bytes)
        except Exception as e:
            _LOGGER.error("Error saving file: %s", e)
            return web.Response(text=f"Error saving file: {e}", status=500)
        
        
        # Upload asincrono alla stampante
        current_timestamp = int(time.time())  # Ottiene il timestamp corrente (secondi dall'epoca)
        upload_url = f"http://{self._ip_address}/upload?X-Filename={filename}&timestamp={current_timestamp}"
        _LOGGER.debug("Uploading to printer at: %s", upload_url)
        try:
            async with ClientSession() as session:
                async with session.post(upload_url, data=file_bytes, timeout=120) as resp:
                    if resp.status == 200:
                        resp_json = await resp.json()  # Converti la risposta in formato JSON
                        if resp_json.get("err") == 0:
                            _LOGGER.info("File uploaded successfully: %s", filename)
                            # Se arriviamo qui, il file è stato ricevuto correttamente dalla stampante
                            # Adesso inviamo i comandi M23/M24 (se abbiamo il sensor).
                            sensor_ref = self._get_sensor_ref(hass)
                            if sensor_ref:
                                try:
                                    sensor_ref.send_ws_command(f"M23 {filename}")
                                    await asyncio.sleep(1)  # Micro ritardo
                                    sensor_ref.send_ws_command("M24")
                                    _LOGGER.info("Sent M23 %s and M24 via WebSocket.", filename)
                                except Exception as e:
                                    _LOGGER.error("Error sending WS commands: %s", e)
                                    return web.Response(text=f"Error sending WS commands: {e}", status=500)
                            else:
                                _LOGGER.warning("No sensor_ref found; cannot send WS commands to start print.")
                        else:
                            _LOGGER.error("Printer returned error: %s", resp_json)
                            return web.Response(
                                text=f"Printer returned error: {resp_json}",
                                status=500
                            )
                    else:
                        _LOGGER.error("Printer upload failed with status: %d", resp.status)
                        return web.Response(
                            text=f"Printer upload failed with status: {resp.status}",
                            status=500
                        )
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout while uploading file to printer.")
            return web.Response(text="Timeout while uploading file to printer.", status=504)
        except Exception as e:
            _LOGGER.error("Exception uploading file to printer: %s", e)
            return web.Response(text=f"Exception uploading file: {e}", status=500)



        return web.Response(text=f"File {filename} uploaded to printer {self._ip_address} and print started!")

class HAG5GetGcodeFile(HomeAssistantView):
    """
    Endpoint:
      GET /api/haghost5/get_gcode_file?filename=<nome>.gcode

    Legge il file .gcode da config/gcodes/<filename> e lo restituisce in plain text
    """

    url = "/api/haghost5/get_gcode_file"
    name = "api:haghost5:get_gcode_file"
    requires_auth = False  # o True se vuoi che sia accessibile solo a utenti loggati

    async def get(self, request):
        hass = request.app["hass"]

        # 1) Recupera il parametro "filename" dalla query string
        filename = request.query.get("filename")
        if not filename:
            return web.Response(text="Missing parameter ?filename=", status=400)

        # 2) Costruisce il path nel filesystem
        gcodes_dir = hass.config.path("gcodes")
        file_path = os.path.join(gcodes_dir, filename)

        # 3) Controlla che il file esista
        if not os.path.isfile(file_path):
            return web.Response(text=f"File '{filename}' not found.", status=404)

        _LOGGER.debug("Serving GCODE file: %s", file_path)

        # 4) Legge il file in modalità testo e lo ritorna
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                file_content = f.read()
        except Exception as e:
            _LOGGER.error("Error reading GCODE file '%s': %s", file_path, e)
            return web.Response(text=f"Error reading file: {e}", status=500)

        # 5) Risponde con il contenuto, come text/plain
        return web.Response(text=file_content, content_type="text/plain")


class GCodeUploadView(HomeAssistantView):
    """
    View per gestire l'upload di file GCODE su /api/haghost5/upload_gcode
    Esempio di form:
      <form method="POST" action="/api/haghost5/upload_gcode" enctype="multipart/form-data">
        <input type="file" name="file" />
        <button type="submit">Invia</button>
      </form>
    """

    url = "/api/haghost5/upload_gcode"  # Aggiungi il percorso URL
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

        # Nuovo percorso per la cartella GCODE
        save_dir = hass.config.path("www", "community", "haghost5", "gcodes")
        os.makedirs(save_dir, exist_ok=True)  # Crea la directory se non esiste

        # Salviamo il file nella nuova directory
        save_path = os.path.join(save_dir, filename)

        try:
            with open(save_path, "wb") as f:
                f.write(file_content)
        except Exception as e:
            _LOGGER.error("Error writing file: %s", e)
            return web.Response(text=f"Error writing file: {e}", status=500)

        return web.Response(text=f"File {filename} uploaded successfully.")
