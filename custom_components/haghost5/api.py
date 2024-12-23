# api.py

import logging
import os
import requests  # Se preferisci sincrono. Se vuoi async userai aiohttp
from homeassistant.components.http import HomeAssistantView
from aiohttp import web

_LOGGER = logging.getLogger(__name__)

class GCodeUploadAndPrintView(HomeAssistantView):
    """Gestisce /api/haghost5/upload_and_print:
       - Carica il file in config/gcodes/
       - Esegue POST alla stampante
       - Invia comandi WebSocket M23, M24
    """

    url = "/api/haghost5/upload_and_print"
    name = "api:haghost5:upload_and_print"
    requires_auth = False  # O True, se vuoi proteggere l'accesso

    def __init__(self, ip_address, sensor_ref=None):
        """
        ip_address: IP della stampante (es. config_entry.data["ip_address"])
        sensor_ref: riferimento al sensor (o classe) che può inviare comandi WS
        """
        self._ip_address = ip_address
        self._sensor_ref = sensor_ref

    async def post(self, request):
        """Handle POST for 'upload and print'."""
        hass = request.app["hass"]

        data = await request.post()
        file_field = data.get("file")
        if not file_field:
            return web.Response(text="No file provided", status=400)

        filename = file_field.filename
        file_bytes = file_field.file.read()
        _LOGGER.info("Received file for upload+print: %s", filename)

        # 1) Salvataggio in config/gcodes/filename
        gcodes_dir = hass.config.path("gcodes")
        os.makedirs(gcodes_dir, exist_ok=True)
        save_path = os.path.join(gcodes_dir, filename)
        with open(save_path, "wb") as f:
            f.write(file_bytes)

        # 2) Upload alla stampante
        try:
            upload_url = f"http://{self._ip_address}/upload?X-Filename={filename}"
            resp = requests.post(upload_url, data=file_bytes, timeout=30)
            if resp.status_code != 200:
                return web.Response(
                    text=f"Printer upload failed: {resp.status_code} {resp.text}",
                    status=500
                )
        except Exception as e:
            _LOGGER.error("Printer upload error: %s", e)
            return web.Response(text=f"Printer upload error: {e}", status=500)

        # 3) Comandi WS: M23 <filename>, M24
        if self._sensor_ref:
            try:
                # Esempio: self._sensor_ref.send_ws_command("M23 file.gcode")
                self._sensor_ref.send_ws_command(f"M23 {filename}")
                self._sensor_ref.send_ws_command("M24")
            except Exception as e:
                _LOGGER.error("Error sending WS commands: %s", e)
                return web.Response(text=f"WS commands error: {e}", status=500)
        else:
            _LOGGER.warning("No sensor reference provided; can't send M23/M24")

        return web.Response(
            text=f"File {filename} uploaded and print started on {self._ip_address}!"
        )
