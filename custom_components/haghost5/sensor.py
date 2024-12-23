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
            "identifiers": {(DOMAIN, self._ip_address)},  # Link entity to device
            "name": f"Printer ({self._ip_address})",
            "manufacturer": "HAGhost5",
            "model": "3D Printer",
            "sw_version": "1.0",
        }

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the HAGhost5 sensor platform."""
    ip_address = config_entry.data["ip_address"]

    # Crea i sensori
    online_sensor = PrinterStatusSensor(ip_address)
    m997_sensor = PrinterM997Sensor(ip_address)

    # Aggiungi i sensori a Home Assistant
    async_add_entities([online_sensor, m997_sensor])

    # Passa il riferimento del secondo sensore al WebSocket
    online_sensor.attach_m997_sensor(m997_sensor)


class PrinterStatusSensor(HAGhost5BaseSensor):
    """Sensor to represent the printer's online/offline status."""

    def __init__(self, ip_address):
        super().__init__(ip_address, "printer_online_status")
        self._state = STATE_OFF
        self._last_message_time = None
        self._websocket_started = False
        self._m997_sensor = None

    def attach_m997_sensor(self, m997_sensor):
        """Collega il sensore M997 al sensore online."""
        self._m997_sensor = m997_sensor

    @property
    def name(self):
        return "Printer Online Status"

    @property
    def state(self):
        return self._state

    async def async_update(self):
        """Check if the printer is online and start WebSocket if needed."""
        _LOGGER.debug("Checking printer status...")
        try:
            async with ClientSession() as session:
                async with session.get(f"http://{self._ip_address}:80", timeout=5) as response:
                    if response.status == 200:
                        if self._state != STATE_ON:
                            _LOGGER.info("Printer is online. Starting WebSocket...")
                            self._state = STATE_ON
                            self._websocket_started = True
                            asyncio.create_task(self._start_websocket())
                        return
        except Exception as e:
            _LOGGER.error("Error checking printer status: %s", e)

        if self._state != STATE_OFF:
            _LOGGER.info("Printer is offline.")
            self._state = STATE_OFF

    async def _start_websocket(self):
        """Start the WebSocket connection and process incoming messages."""
        ws_url = f"ws://{self._ip_address}:8081/"
        _LOGGER.info("Connecting to WebSocket at: %s", ws_url)
        while self._state == STATE_ON:
            try:
                async with ClientSession() as session:
                    async with session.ws_connect(ws_url) as ws:
                        async for msg in ws:
                            if msg.type == WSMsgType.TEXT:
                                _LOGGER.debug("WebSocket message received: %s", msg.data)

                                # Pass the message to the M997 sensor for processing
                                if self._m997_sensor:
                                    await self._m997_sensor.process_message(msg.data)

                            elif msg.type in {WSMsgType.CLOSED, WSMsgType.ERROR}:
                                _LOGGER.warning("WebSocket closed or error.")
                                break
            except Exception as e:
                _LOGGER.error("WebSocket error: %s", e)
                await asyncio.sleep(5)  # Retry connection


class PrinterM997Sensor(HAGhost5BaseSensor):
    """Sensor to represent the printer's status from M997 messages."""

    def __init__(self, ip_address):
        super().__init__(ip_address, "printer_m997_status")
        self._state = None

    @property
    def name(self):
        return "Printer M997 Status"

    @property
    def state(self):
        return self._state

    async def process_message(self, message):
        """Process a WebSocket message and extract M997 status."""
        try:
            # Cerca un messaggio che inizia con "M997"
            pattern = r"M997\s+([^\s]+)"
            match = re.search(pattern, message)
            if match:
                self._state = match.group(1)  # Lo stato estratto dal messaggio
                self._attributes = {
                    "last_update": datetime.now().isoformat(),
                    "raw_message": message,
                }
                _LOGGER.debug("Printer M997 Status updated: %s", self._state)
                self.async_write_ha_state()
            else:
                _LOGGER.debug("No M997 status found in message: %s", message)
        except Exception as e:
            _LOGGER.error("Error processing message: %s", e)
