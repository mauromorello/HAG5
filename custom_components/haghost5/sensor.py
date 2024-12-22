import logging
import asyncio
from aiohttp import ClientSession, WSMsgType
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the HAGhost5 sensor platform."""
    ip_address = config_entry.data.get("ip_address")
    sensors = [
        PrintFileSensor(ip_address),
        PrinterStateSensor(ip_address),
        ElapsedTimeSensor(ip_address),
        NozzleTemperatureRealSensor(ip_address),
        NozzleTemperatureSetpointSensor(ip_address),
        BedTemperatureRealSensor(ip_address),
        BedTemperatureSetpointSensor(ip_address),
        PrintPercentageSensor(ip_address),
        PrinterOnlineStatusSensor(ip_address),
    ]
    async_add_entities(sensors, update_before_add=True)
    hass.loop.create_task(sensors[0].listen_to_websocket(sensors))

class HAGhost5BaseSensor(SensorEntity):
    """Base class for HAGhost5 sensors."""

    def __init__(self, ip_address: str):
        """Initialize the sensor."""
        self._ip_address = ip_address
        self._state = None
        self._attributes = {}
        self._is_listening = False

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    async def listen_to_websocket(self, sensors):
        """Maintain a persistent connection to the WebSocket."""
        ws_url = f"ws://{self._ip_address}:8081/"
        self._is_listening = True
        _LOGGER.debug("Connecting to WebSocket at: %s", ws_url)
        while self._is_listening:
            try:
                async with ClientSession() as session:
                    async with session.ws_connect(ws_url) as ws:
                        _LOGGER.info("Connected to WebSocket at: %s", ws_url)
                        async for msg in ws:
                            if msg.type == WSMsgType.TEXT:
                                for sensor in sensors:
                                    await sensor.process_message(msg.data)
                            elif msg.type == WSMsgType.ERROR:
                                _LOGGER.error("WebSocket error: %s", msg)
                                break
            except Exception as e:
                _LOGGER.error("Error in WebSocket connection: %s", e)
                await asyncio.sleep(5)  # Wait before reconnecting

class PrintFileSensor(HAGhost5BaseSensor):
    """Sensor for the file being printed."""

    @property
    def name(self):
        return "Print File"

    @property
    def icon(self):
        return "mdi:file-document"

    async def process_message(self, message: str):
        if "M994" in message:
            self._state = message.split("M994 ")[1].strip()
            self.async_write_ha_state()

class PrinterStateSensor(HAGhost5BaseSensor):
    """Sensor for the printer state."""

    @property
    def name(self):
        return "Printer State"

    @property
    def icon(self):
        return "mdi:printer-3d"

    async def process_message(self, message: str):
        if "M997" in message:
            self._state = message.split("M997 ")[1].strip()
            self.async_write_ha_state()

class ElapsedTimeSensor(HAGhost5BaseSensor):
    """Sensor for the elapsed printing time."""

    @property
    def name(self):
        return "Elapsed Time"

    @property
    def icon(self):
        return "mdi:timer"

    async def process_message(self, message: str):
        if "M992" in message:
            self._state = message.split("M992 ")[1].strip()
            self.async_write_ha_state()

class NozzleTemperatureRealSensor(HAGhost5BaseSensor):
    """Sensor for the real nozzle temperature."""

    @property
    def name(self):
        return "Nozzle Temperature (Real)"

    @property
    def unit_of_measurement(self):
        return "°C"

    @property
    def icon(self):
        return "mdi:thermometer"

    async def process_message(self, message: str):
        if "T:" in message:
            parts = message.split()
            for part in parts:
                if part.startswith("T:"):
                    self._state = float(part.split(":")[1].split("/")[0])
                    self.async_write_ha_state()

class NozzleTemperatureSetpointSensor(HAGhost5BaseSensor):
    """Sensor for the nozzle temperature setpoint."""

    @property
    def name(self):
        return "Nozzle Temperature (Setpoint)"

    @property
    def unit_of_measurement(self):
        return "°C"

    @property
    def icon(self):
        return "mdi:thermometer"

    async def process_message(self, message: str):
        if "T:" in message:
            parts = message.split()
            for part in parts:
                if part.startswith("T:"):
                    self._state = float(part.split(":")[1].split("/")[1])
                    self.async_write_ha_state()

class BedTemperatureRealSensor(HAGhost5BaseSensor):
    """Sensor for the real bed temperature."""

    @property
    def name(self):
        return "Bed Temperature (Real)"

    @property
    def unit_of_measurement(self):
        return "°C"

    @property
    def icon(self):
        return "mdi:thermometer"

    async def process_message(self, message: str):
        if "B:" in message:
            parts = message.split()
            for part in parts:
                if part.startswith("B:"):
                    self._state = float(part.split(":")[1].split("/")[0])
                    self.async_write_ha_state()

class BedTemperatureSetpointSensor(HAGhost5BaseSensor):
    """Sensor for the bed temperature setpoint."""

    @property
    def name(self):
        return "Bed Temperature (Setpoint)"

    @property
    def unit_of_measurement(self):
        return "°C"

    @property
    def icon(self):
        return "mdi:thermometer"

    async def process_message(self, message: str):
        if "B:" in message:
            parts = message.split()
            for part in parts:
                if part.startswith("B:"):
                    self._state = float(part.split(":")[1].split("/")[1])
                    self.async_write_ha_state()

class PrintPercentageSensor(HAGhost5BaseSensor):
    """Sensor for the print percentage."""

    @property
    def name(self):
        return "Print Percentage"

    @property
    def unit_of_measurement(self):
        return "%"

    @property
    def icon(self):
        return "mdi:progress-check"

    async def process_message(self, message: str):
        if "M27" in message:
            self._state = int(message.split("M27 ")[1].strip())
            self.async_write_ha_state()

class PrinterOnlineStatusSensor(HAGhost5BaseSensor):
    """Sensor for the printer online status."""

    @property
    def name(self):
        return "Printer Online"

    @property
    def icon(self):
        return "mdi:wifi"

    async def process_message(self, message: str):
        self._state = "ONLINE"
        self.async_write_ha_state()

    async def listen_to_websocket(self, sensors):
        """Maintain a persistent connection to the WebSocket."""
        try:
            await super().listen_to_websocket(sensors)
        except Exception:
            self._state = "OFFLINE"
            self.async_write_ha_state()
