import logging
import asyncio
from aiohttp import ClientSession, WSMsgType
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_ON, STATE_OFF
from datetime import datetime, timedelta
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)


class HAGhost5BaseSensor(SensorEntity):
    """Base class for HAGhost5 sensors."""

    def __init__(self, ip_address: str, sensor_name: str):
        """Initialize the sensor."""
        self._ip_address = ip_address
        self._state = None
        self._attributes = {}
        self._sensor_name = sensor_name  # Name identifier for unique_id
        self._is_listening = False

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return f"{self._ip_address}_{self._sensor_name}"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def device_info(self):
        """Return device information for Home Assistant."""
        return {
            "identifiers": {(DOMAIN, self._ip_address)},  # Questo collega l'entità al device
            "name": f"Printer ({self._ip_address})",
            "manufacturer": "HAGhost5",
            "model": "3D Printer",
            "sw_version": "1.0",
        }


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the HAGhost5 sensor platform."""
    ip_address = config_entry.data["ip_address"]
    sensor = PrinterStatusSensor(ip_address)
    async_add_entities([sensor])

class PrinterStatusSensor(SensorEntity):
    """Sensor to represent the printer's online/offline status."""

    def __init__(self, ip_address):
        self._ip_address = ip_address
        self._state = STATE_OFF
        self._last_message = None

    @property
    def name(self):
        return "Printer Online Status"

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return {"last_message": self._last_message}
        
    @property
    def device_info(self):
        """Return device information for Home Assistant."""
        return {
            "identifiers": {(DOMAIN, self._ip_address)},  # Questo collega l'entità al device
            "name": f"Printer ({self._ip_address})",
            "manufacturer": "HAGhost5",
            "model": "3D Printer",
            "sw_version": "1.0",
        }
        @property
        
    def is_on(self):
        """Return True if the printer is online."""
        if self._last_message_time:
            online = datetime.now() - self._last_message_time < timedelta(seconds=5)
            if online and not self._websocket_started:
                self._websocket_started = True
                self._start_websocket_callback()
            return online
        if not self._websocket_started:
            # Se non è mai stato avviato, forziamo l'avvio una volta
            self._websocket_started = True
            self._start_websocket_callback()
        return False    
        
    async def async_update(self):
        """Check if the printer is online and start WebSocket if needed."""
        try:
            async with ClientSession() as session:
                async with session.get(f"http://{self._ip_address}:80", timeout=5) as response:
                    if response.status == 200:
                        if self._state != STATE_ON:
                            _LOGGER.info("Printer is online. Starting WebSocket...")
                            self._state = STATE_ON
                            asyncio.create_task(self._start_websocket())
                        return
        except Exception as e:
            _LOGGER.error("Error checking printer status: %s", e)

        self._state = STATE_OFF

    async def _start_websocket(self):
        """Start the WebSocket connection and log all incoming messages."""
        ws_url = f"ws://{self._ip_address}:8081/"
        _LOGGER.info("Connecting to WebSocket at: %s", ws_url)
        while self._state == STATE_ON:
            try:
                async with ClientSession() as session:
                    async with session.ws_connect(ws_url) as ws:
                        async for msg in ws:
                            if msg.type == WSMsgType.TEXT:
                                self._last_message = msg.data
                                _LOGGER.debug("WebSocket message: %s", msg.data)
                            elif msg.type in {WSMsgType.CLOSED, WSMsgType.ERROR}:
                                _LOGGER.warning("WebSocket closed or error.")
                                break
            except Exception as e:
                _LOGGER.error("WebSocket error: %s", e)
                await asyncio.sleep(5)  # Retry connection
