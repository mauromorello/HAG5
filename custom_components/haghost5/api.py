# api.py

import logging
import os
import asyncio
from homeassistant.components.http import HomeAssistantView
from aiohttp import web, ClientSession

_LOGGER = logging.getLogger(__name__)

class GCodeUploadAndPrintView(HomeAssistantView):
    """
    View su /api/haghost5/upload_and_print:
      - Riceve il file GCODE (POST)
      - Salva in config/gcodes/<filename>
      - Manda in modo asincrono il file alla stampante (POST),
      - Invio comandi WebSocket (M23, M24) se sensor_ref è disponibile.
    """

    url = "/api/haghost5/upload_and_print"
    name = "api:haghost5:upload_and_print"
    requires_auth = False

    def __init__(self, ip_address, sensor_ref=None):
        """
        ip_address: IP o hostname della stampante (es. config_entry.data["ip_address"])
        sensor_ref: riferimento a un oggetto con un metodo per inviare comandi WS 
                    (ad es. sensor_ref.send_ws_command("M23 file.gcode"))
        """
        self._ip_address = ip_address
        self._sensor_ref = sensor_ref

    async def post(self, request):
        """Riceve il file e inizia la stampa asincronamente."""
        hass = request.app["hass"]

        # 1) Recupera il file dal form
        data = await request.post()
        file_field = data.get("file")
        if not file_field:
            return web.Response(text="No file provided", status=400)

        filename = file_field.filename
        file_bytes = file_field.file.read()  # lettura in memoria
        _LOGGER.info("Received file for upload_and_print: %s", filename)

        # 2) Salvataggio in config/gcodes/<filename>
        gcodes_dir = hass.config.path("gcodes")
        os.makedirs(gcodes_dir, exist_ok=True)
        save_path = os.path.join(gcodes_dir, filename)

        try:
            with open(save_path, "wb") as f:
                f.write(file_bytes)
        except Exception as e:
            _LOGGER.error("Error saving file: %s", e)
            return web.Response(text=f"Error saving file: {e}", status=500)

        # 3) Invio asincrono del file alla stampante
        upload_url = f"http://{self._ip_address}/upload?X-Filename={filename}"
        _LOGGER.debug("Uploading to printer at: %s", upload_url)

        try:
            async with ClientSession() as session:
                async with session.post(upload_url, data=file_bytes, timeout=30) as resp:
                    if resp.status != 200:
                        resp_text = await resp.text()
                        _LOGGER.error("Printer upload error: %s %s", resp.status, resp_text)
                        return web.Response(
                            text=f"Printer upload error: {resp.status} {resp_text}",
                            status=500
                        )
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout while uploading file to printer.")
            return web.Response(text="Timeout while uploading file to printer.", status=504)
        except Exception as e:
            _LOGGER.error("Exception uploading file to printer: %s", e)
            return web.Response(text=f"Exception uploading file: {e}", status=500)

        # 4) Invia comandi WS se sensor_ref è disponibile
        if self._sensor_ref:
            try:
                self._sensor_ref.send_ws_command(f"M23 {filename}")
                await asyncio.sleep(1)  # Aspetta 1 secondo prima di inviare M24
                self._sensor_ref.send_ws_command("M24")
                _LOGGER.info("Sent M23 %s and M24 via WebSocket.", filename)
            except Exception as e:
                _LOGGER.error("Error sending WS commands: %s", e)
                return web.Response(text=f"Error sending WS commands: {e}", status=500)
        else:
            _LOGGER.warning("No sensor_ref provided; cannot send WS commands to start print.")

        return web.Response(
            text=f"File {filename} uploaded to printer {self._ip_address} and print started!"
        )


# api.py

import logging
import os
from homeassistant.components.http import HomeAssistantView
from aiohttp import web

_LOGGER = logging.getLogger(__name__)

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
