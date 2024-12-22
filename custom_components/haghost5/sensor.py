import logging
import re
import asyncio
from aiohttp import ClientSession, WSMsgType
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from datetime import datetime, timedelta
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Variabile globale per tracciare l'ultimo messaggio ricevuto
LAST_WEBSOCKET_MESSAGE = None

async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the HAGhost5 sensor platform."""
    ip_address = config_entry.data.get("ip_address")

    sensors = [
        NozzleTemperatureRealSensor(ip_address),
        NozzleTemperatureSetpointSensor(ip_address),
        BedTemperatureRealSensor(ip_address),
        BedTemperatureSetpointSensor(ip_address),
        PrinterOnlineStatusSensor(ip_address),  # Binary Sensor
        PrinterStateSensor(ip_address),         # Stato Operativo
    ]
    async_add_entities(sensors, update_before_add=True)

    async def websocket_listener():
        """Central WebSocket listener for all sensors."""
        ws_url = f"ws://{ip_address}:8081/"
        _LOGGER.debug("Connecting to WebSocket at: %s", ws_url)
        while True:
            try:
                async with ClientSession() as session:
                    async with session.ws_connect(ws_url) as ws:
                        _LOGGER.info("Connected to WebSocket at: %s", ws_url)
                        async for msg in ws:
                            if msg.type == WSMsgType.TEXT:
                                _LOGGER.debug("WebSocket message received: %s", msg.data)
                                for sensor in sensors:
                                    # Controlla se il sensore ha il metodo `process_message`
                                    if hasattr(sensor, "process_message"):
                                        await sensor.process_message(msg.data)
                            elif msg.type == WSMsgType.ERROR:
                                _LOGGER.error("WebSocket error: %s", msg)
                                break
            except Exception as e:
                _LOGGER.error("Error in WebSocket connection: %s", e)
                await asyncio.sleep(5)  # Wait before reconnecting
    
    # Start the WebSocket listener as a background task
    hass.loop.create_task(websocket_listener())         
  

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
        return {
            "identifiers": {(DOMAIN, self._ip_address)},
            "name": "HAGhost5 3D Printer",
            "manufacturer": "HAGhost5",
            "model": "3D Printer Sensors",
            "sw_version": "1.0",
        }


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
                                _LOGGER.debug("WebSocket message received: %s", msg.data)
                                for sensor in sensors:
                                    await sensor.process_message(msg.data)
                            elif msg.type == WSMsgType.ERROR:
                                _LOGGER.error("WebSocket error: %s", msg)
                                break
            except Exception as e:
                _LOGGER.error("Error in WebSocket connection: %s", e)
                await asyncio.sleep(5)  # Wait before reconnecting

class NozzleTemperatureRealSensor(HAGhost5BaseSensor):
    """Sensor for the real nozzle temperature."""

    def __init__(self, ip_address: str):
        super().__init__(ip_address, "nozzle_temperature_real")

    @property
    def unique_id(self):
        return f"{self._ip_address}_nozzle_temperature_real"
    
    @property
    def name(self):
        return "Nozzle Temperature (Real)"

    @property
    def unit_of_measurement(self):
        return "°C"

    @property
    def icon(self):
        return "mdi:thermometer"
    
    @property
    def state(self):
        """Return the current state."""
        return self._state        

    async def process_message(self, message: str):
        global LAST_WEBSOCKET_MESSAGE
        LAST_WEBSOCKET_MESSAGE = datetime.now()  # Aggiorna il timestamp
        
        if "T:" in message:  # Verifica che il messaggio contenga informazioni sulle temperature
            try:
                parts = message.split()  # Suddivide il messaggio in parti
                for part in parts:
                    if part.startswith("T:"):  # Cerca il prefisso "T:"
                        temperature_parts = part.split(":")[1].split("/")
                        if len(temperature_parts) > 0:  # Verifica che ci sia almeno 1 valore
                            self._state = float(temperature_parts[0])
                            _LOGGER.debug("Updated Nozzle Temperature (Real): %s", self._state)
                            self.async_write_ha_state()
                        else:
                            _LOGGER.warning("Unexpected temperature format for Nozzle Real: %s", part)
            except (IndexError, ValueError) as e:
                _LOGGER.error("Error parsing nozzle real temperature: %s | Message: %s", e, message)




class NozzleTemperatureSetpointSensor(HAGhost5BaseSensor):
    """Sensor for the nozzle temperature setpoint."""

    def __init__(self, ip_address: str):
        super().__init__(ip_address, "nozzle_temperature_setpoint")

    @property
    def unique_id(self):
        return f"{self._ip_address}_nozzle_temperature_setpoint"
    
    @property
    def name(self):
        return "Nozzle Temperature (Setpoint)"

    @property
    def unit_of_measurement(self):
        return "°C"

    @property
    def icon(self):
        return "mdi:thermometer"

    @property
    def state(self):
        """Return the current state."""
        return self._state 

    async def process_message(self, message: str):
        # Verifica che il messaggio inizi con "T:"
        if not message.startswith("T:"):
            return
    
        pattern = r"T:\s*([\d\.]+)\s*/\s*([\d\.]+)"
        match = re.search(pattern, message)
        if match:
            try:
                self._state = float(match.group(2))
                _LOGGER.debug("Updated Nozzle Temperature (Setpoint): %s", self._state)
                self.async_write_ha_state()
            except ValueError:
                _LOGGER.error("Error parsing nozzle setpoint temperature | Message: %s", message)
        else:
            _LOGGER.warning("No valid temperature found in message: %s", message)

class BedTemperatureRealSensor(HAGhost5BaseSensor):
    """Sensor for the bed real temperature."""

    def __init__(self, ip_address: str):
        super().__init__(ip_address, "bed_temperature_real")

    @property
    def unique_id(self):
        return f"{self._ip_address}_bed_temperature_real"
    
    @property
    def name(self):
        return "Bed Temperature (Real)"

    @property
    def unit_of_measurement(self):
        return "°C"

    @property
    def icon(self):
        return "mdi:thermometer"

    @property
    def state(self):
        """Return the current state."""
        return self._state 

    async def process_message(self, message: str):
        # Verifica che il messaggio contenga "B:"
        if "B:" not in message:
            return
    
        pattern = r"B:\s*([\d\.]+)\s*/"
        match = re.search(pattern, message)
        if match:
            try:
                self._state = float(match.group(1))  # La temperatura reale è il primo valore
                _LOGGER.debug("Updated Bed Temperature (Real): %s", self._state)
                self.async_write_ha_state()
            except ValueError:
                _LOGGER.error("Error parsing bed real temperature | Message: %s", message)
        else:
            _LOGGER.warning("No valid temperature found in message: %s", message)


class BedTemperatureSetpointSensor(HAGhost5BaseSensor):
    """Sensor for the bed temperature setpoint."""

    def __init__(self, ip_address: str):
        super().__init__(ip_address, "bed_temperature_setpoint")

    @property
    def unique_id(self):
        return f"{self._ip_address}_bed_temperature_setpoint"
    
    @property
    def name(self):
        return "Bed Temperature (Setpoint)"

    @property
    def unit_of_measurement(self):
        return "°C"

    @property
    def icon(self):
        return "mdi:thermometer"

    @property
    def state(self):
        """Return the current state."""
        return self._state 

    async def process_message(self, message: str):
        # Verifica che il messaggio contenga "B:"
        if "B:" not in message:
            return
    
        pattern = r"B:\s*[\d\.]+\s*/\s*([\d\.]+)"
        match = re.search(pattern, message)
        if match:
            try:
                self._state = float(match.group(1))  # Il setpoint è il valore dopo lo slash
                _LOGGER.debug("Updated Bed Temperature (Setpoint): %s", self._state)
                self.async_write_ha_state()
            except ValueError:
                _LOGGER.error("Error parsing bed setpoint temperature | Message: %s", message)
        else:
            _LOGGER.warning("No valid temperature found in message: %s", message)

class PrinterOnlineStatusSensor(HAGhost5BaseSensor, BinarySensorEntity):
    """Binary sensor for the printer online status."""

    def __init__(self, ip_address: str):
        super().__init__(ip_address, "printer_online_status")
        self._last_message_time = None  # Timestamp dell'ultimo messaggio ricevuto

    @property
    def unique_id(self):
        return f"{self._ip_address}_printer_online_status"

    @property
    def name(self):
        return "Printer Online Status"

    @property
    def icon(self):
        return "mdi:wifi"

    @property
    def is_on(self):
        """Return True if the printer is online."""
        if self._last_message_time:
            # Calcola la differenza tra l'ora attuale e l'ultimo messaggio
            return datetime.now() - self._last_message_time < timedelta(seconds=5)
        return False

    async def process_message(self, message: str):
        """Aggiorna il timestamp quando arriva un messaggio valido."""
        self._last_message_time = datetime.now()  # Aggiorna l'ora dell'ultimo messaggio
        _LOGGER.debug("Updated Printer Online Status timestamp: %s", self._last_message_time)
        self.async_write_ha_state()

class PrinterStateSensor(HAGhost5BaseSensor):
    """Sensor for the printer operational state."""

    def __init__(self, ip_address: str):
        super().__init__(ip_address, "printer_state")
        self._state = "UNKNOWN"  # Stato iniziale

    @property
    def unique_id(self):
        return f"{self._ip_address}_printer_state"

    @property
    def name(self):
        return "Printer State"

    @property
    def icon(self):
        return "mdi:printer-3d"

    @property
    def state(self):
        """Return the current printer state."""
        return self._state

    async def process_message(self, message: str):
        """Processa solo messaggi con prefisso Mxxx."""
        if not message.startswith("M997"):
            return  # Ignora messaggi che non iniziano con "M"

        # Logica per determinare lo stato della stampante
        if "M997 PRINTING" in message:
            self._state = "PRINTING"
        elif "M997 IDLE" in message:
            self._state = "IDLE"
        else:
            self._state = message  # Usa il messaggio completo come stato sconosciuto

        _LOGGER.debug("Updated Printer State: %s", self._state)
        self.async_write_ha_state()


