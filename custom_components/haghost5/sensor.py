import logging
import re
import asyncio

from aiohttp import ClientSession, WSMsgType
from datetime import datetime, timedelta
from .const import DOMAIN

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,       # Opzionale, se vuoi indicare il "tipo" di stato (measurement, total, ecc.)
)
from homeassistant.const import (
    UnitOfTime,
    UnitOfTemperature,
    STATE_OFF,
    STATE_ON,
    PERCENTAGE,             # Per indicare il simbolo/label della percentuale
)

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
            "identifiers": {(DOMAIN, self._ip_address)},
            "name": f"Printer ({self._ip_address})",
            "manufacturer": "HAGhost5",
            "model": "3D Printer",
            "sw_version": "1.0",
        }
        
    async def async_update(self):
        """Default update method for HAGhost5 sensors."""
        _LOGGER.debug("async_update called for %s, no custom implementation.", self._sensor_name)        

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the HAGhost5 sensor platform."""
    ip_address = config_entry.data["ip_address"]



    # Crea i sensori
    m992_sensor = PrinterM992Sensor(ip_address)
    # online_sensor = PrinterStatusSensor(ip_address)
    m997_sensor = PrinterM997Sensor(ip_address)
    m27_sensor = PrinterM27Sensor(ip_address)
    m994_sensor = PrinterM994Sensor(ip_address)
    tnozzle_sensor = TNozzleSensor(ip_address)
    tbed_sensor = TBedSensor(ip_address)

    online_sensor = PrinterStatusSensor(ip_address)
    hass.data[DOMAIN]["printer_status_sensor"] = online_sensor
    #async_add_entities([online_sensor]) 
    
    
    # Aggiungi i sensori a Home Assistant
    async_add_entities([online_sensor, m997_sensor, m27_sensor, m994_sensor, m992_sensor, tbed_sensor, tnozzle_sensor])

    # Collega i sensori M997 e M27 al sensore online
    online_sensor.attach_m997_sensor(m997_sensor)
    online_sensor.attach_m27_sensor(m27_sensor)
    online_sensor.attach_m994_sensor(m994_sensor)
    online_sensor.attach_m992_sensor(m992_sensor)
    online_sensor.attach_tbed_sensor(tbed_sensor)
    online_sensor.attach_tnozzle_sensor(tnozzle_sensor)

    # Forza un aggiornamento immediato per ciascun sensore
    await online_sensor.async_update()
    await m997_sensor.async_update()
    await m27_sensor.async_update()
    await m994_sensor.async_update()
    await m992_sensor.async_update()
    await tbed_sensor.async_update()
    await tnozzle_sensor.async_update()

class PrinterStatusSensor(HAGhost5BaseSensor):
    """Sensor to represent the printer's online/offline status."""

    def __init__(self, ip_address):
        super().__init__(ip_address, "printer_online_status")
        self._state = STATE_OFF
        self._last_message_time = None
        self._websocket_started = False
        self._m997_sensor = None
        self._m27_sensor = None
        self._m994_sensor = None
        self._m992_sensor = None
        self._tbed_sensor = None
        self._tnozzle_sensor = None
        self._idle_state = False  # Indica se la stampante è in stato IDLE

    def attach_m997_sensor(self, m997_sensor):
        """Collega il sensore M997 al sensore online."""
        self._m997_sensor = m997_sensor
        
    def attach_m27_sensor(self, m27_sensor):
        """Collega il sensore M27 al sensore online."""
        self._m27_sensor = m27_sensor

    def attach_m994_sensor(self, m994_sensor):
        """Collega il sensore M994 al sensore online."""
        self._m994_sensor = m994_sensor
        
    def attach_m992_sensor(self, m992_sensor):
        """Collega il sensore M992 al sensore online."""
        self._m992_sensor = m992_sensor

    def attach_tbed_sensor(self, tbed_sensor):
        """Collega il sensore tbed al sensore online."""
        self._tbed_sensor = tbed_sensor

    def attach_tnozzle_sensor(self, tnozzle_sensor):
        """Collega il sensore tnozzle al sensore online."""
        self._tnozzle_sensor = tnozzle_sensor    

    @property
    def name(self):
        return "Status printer"

    @property
    def state(self):
        return self._state

    @property
    def device_info(self):
        """Return device information for Home Assistant."""
        return {
            "identifiers": {(DOMAIN, self._ip_address)},
            "name": f"Printer ({self._ip_address})",
            "manufacturer": "HAGhost5",
            "model": "3D Printer",
            "sw_version": "1.0",
        }

    @property
    def unique_id(self):
        """Return a truly unique ID for the sensor."""
        return f"{self._ip_address}_printer_online_status"

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
                            self._idle_state = False
                            asyncio.create_task(self._start_websocket())
                        return
        except Exception as e:
            _LOGGER.debug("Error checking printer status: %s", e)
    
        if self._state != STATE_OFF:
            _LOGGER.info("Printer is offline.")
            self._state = STATE_OFF
            self._reset_all_sensors()

    def set_idle_state(self, is_idle: bool):
        """Set the printer's idle state and update sensors accordingly."""
        self._idle_state = is_idle
        if is_idle:
            _LOGGER.info("Printer is in IDLE state. Updating sensors...")
            self._reset_non_temperature_sensors()
        else:
            _LOGGER.info("Printer is active. Restoring sensor updates...")

    def _reset_all_sensors(self):
        """Reset all sensors to 0."""
        if self._m997_sensor:
            self._m997_sensor.reset()
        if self._m27_sensor:
            self._m27_sensor.reset()
        if self._m994_sensor:
            self._m994_sensor.reset()
        if self._m992_sensor:
            self._m992_sensor.reset()
        if self._tbed_sensor:
            self._tbed_sensor.reset()
        if self._tnozzle_sensor:
            self._tnozzle_sensor.reset()
        _LOGGER.info("All sensors have been reset to 0 due to printer being offline.")

    def _reset_non_temperature_sensors(self):
        """Reset all sensors except temperature sensors."""
        if self._m997_sensor:
            self._m997_sensor.reset()
        if self._m27_sensor:
            self._m27_sensor.reset()
        if self._m994_sensor:
            self._m994_sensor.reset()
        if self._m992_sensor:
            self._m992_sensor.reset()
        _LOGGER.info("Non-temperature sensors have been reset to 0 due to printer being in IDLE state.")

    def send_ws_command(self, command: str):
        """Send a command over the WebSocket."""
        if not self._websocket_started:
            _LOGGER.error("Cannot send command; WebSocket is not started.")
            return
    
        asyncio.create_task(self._send_command_via_ws(command))
    
    async def _send_command_via_ws(self, command: str):
        """Helper to send a command asynchronously via WebSocket."""
        ws_url = f"ws://{self._ip_address}:8081/"
        try:
            async with ClientSession() as session:
                async with session.ws_connect(ws_url) as ws:
                    await ws.send_str(command)
                    _LOGGER.info("Sent WebSocket command: %s", command)
        except Exception as e:
            _LOGGER.error("Error sending WebSocket command: %s", e)

    async def _start_websocket(self):
        """Start the WebSocket connection and process incoming messages."""
        if self._websocket_started:
            _LOGGER.warning("WebSocket is already started. Skipping...")
            return  # Evita di riaprire il WebSocket se è già avviato
    
        self._websocket_started = True
        ws_url = f"ws://{self._ip_address}:8081/"
        _LOGGER.info("Connecting to WebSocket at: %s", ws_url)

        # Avvia il polling dei comandi in parallelo
        asyncio.create_task(self._start_polling_commands())
    
        while self._state == STATE_ON:
            try:
                async with ClientSession() as session:
                    async with session.ws_connect(ws_url) as ws:
                        async for msg in ws:
                            if msg.type == WSMsgType.TEXT:
                                # Process WebSocket messages and update state
                                if "IDLE" in msg.data:
                                    self.set_idle_state(True)
                                else:
                                    self.set_idle_state(False)
                                    
                                _LOGGER.debug("WebSocket message received: %s", msg.data)
                                
                                # Process file list messages
                                if "Begin file list" in msg.data or msg.data.endswith(".gcode") or "End file list" in msg.data:
                                    self.process_file_list_message(msg.data)

                                if self._m997_sensor:
                                    await self._m997_sensor.process_message(msg.data)
                                if self._m27_sensor:
                                    await self._m27_sensor.process_message(msg.data)
                                if self._m994_sensor:
                                    await self._m994_sensor.process_message(msg.data)
                                if self._m992_sensor:
                                    await self._m992_sensor.process_message(msg.data)
                                if self._tbed_sensor:
                                    await self._tbed_sensor.process_message(msg.data)
                                if self._tnozzle_sensor:
                                    await self._tnozzle_sensor.process_message(msg.data)
                                    
                            elif msg.type in {WSMsgType.CLOSED, WSMsgType.ERROR}:
                                _LOGGER.warning("WebSocket closed or error.")
                                break

            except Exception as e:
                _LOGGER.error("WebSocket error: %s", e)
                await asyncio.sleep(5)  # Retry connection
    
        self._websocket_started = False  # WebSocket chiuso, pronto per riaprirlo

    async def _start_polling_commands(self):
        """Start polling commands to the printer every 5 seconds."""
        _LOGGER.info("Starting polling commands to the printer.")
        while self._state == STATE_ON:
            try:
                if self._websocket_started:                   
                    await self._send_command_via_ws("M27\nM992\nM994\nM991\nM997\n")
                await asyncio.sleep(5)  # Aspetta 5 secondi prima di inviare di nuovo i comandi
            except Exception as e:
                _LOGGER.error("Error during polling commands: %s", e)
                break
        _LOGGER.info("Polling commands stopped because the printer is offline.")

    def process_file_list_message(self, message):
        """Elabora i messaggi della lista file e gestisce timeout per completare la lista."""
        if not hasattr(self, '_file_list'):
            self._file_list = []
            self._file_list_timer = None

        if message.startswith("Begin file list"):
            self._file_list = []  # Inizializza una nuova lista
            if self._file_list_timer:
                self._file_list_timer.cancel()
                self._file_list_timer = None
            _LOGGER.info("Started processing file list.")

        elif message.endswith(".gcode"):
            self._file_list.append(message.strip())
            _LOGGER.info("Added file to list: %s", message.strip())

        elif message.startswith("End file list"):
            if self._file_list_timer:
                self._file_list_timer.cancel()
                self._file_list_timer = None
            self.save_gcode_file_list(self._file_list)
            self._file_list = []  # Reset della lista
            _LOGGER.info("Completed processing file list.")

        else:
            # In caso di timeout
            if self._file_list_timer:
                self._file_list_timer.cancel()
            self._file_list_timer = asyncio.get_event_loop().call_later(10, self._handle_file_list_timeout)

    def _handle_file_list_timeout(self):
        """Gestisce il timeout per il completamento della lista file."""
        if self._file_list:
            self.save_gcode_file_list(self._file_list)  # Salva i file accumulati finora
            _LOGGER.warning("File list processing timed out. Saved incomplete list.")
        self._file_list = []  # Reset della lista

    def save_gcode_file_list(self, file_list):
        """Salva l'elenco dei file in un file JSON."""
        files_dir = os.path.join("www", "community", "haghost5")
        json_path = os.path.join(files_dir, "files.json")
        try:
            os.makedirs(files_dir, exist_ok=True)
            with open(json_path, "w") as json_file:
                json.dump(file_list, json_file)
            _LOGGER.info("File list saved to %s", json_path)
        except Exception as e:
            _LOGGER.error("Failed to save file list to JSON: %s", e)


class PrinterM997Sensor(HAGhost5BaseSensor):
    """Sensor to represent the printer's status from M997 messages."""

    def __init__(self, ip_address):
        super().__init__(ip_address, "printer_m997_status")
        self._state = None

    def reset(self):
        """Reimposta il sensore allo stato iniziale."""
        self._state = 0
        _LOGGER.info("PrinterM997Sensor reset to 0.")

    @property
    def name(self):
        return "Operation"

    @property
    def state(self):
        return self._state
        
    @property
    def extra_state_attributes(self):
        """Eventuali attributi extra da visualizzare in HA."""
        return self._attributes        

    @property
    def device_info(self):
        """Return device information for Home Assistant."""
        return {
            "identifiers": {(DOMAIN, self._ip_address)},
            "name": f"Printer ({self._ip_address})",
            "manufacturer": "HAGhost5",
            "model": "3D Printer",
            "sw_version": "1.0",
        }   
        
    @property
    def unique_id(self):
        """Return a truly unique ID for the sensor."""
        return f"{self._ip_address}_printer_m997_status"
        
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
        except Exception as e:
            _LOGGER.error("Error processing message: %s", e)

class PrinterM27Sensor(HAGhost5BaseSensor):
    """Sensor to represent the printer's status from M27 messages."""

    def __init__(self, ip_address):
        super().__init__(ip_address, "printer_m27_status")
        self._state = None

    def reset(self):
        """Reimposta il sensore allo stato iniziale."""
        self._state = 0
        _LOGGER.info("PrinterM997Sensor reset to 0.")
    
    @property
    def name(self):
        return "Print Progress"

    @property
    def device_class(self):
        return None    

    @property
    def native_value(self):
        """
        Con il nuovo modello di sensori, si usa `native_value` al posto di `state`.
        Se preferisci mantenere la vecchia nomenclatura, puoi fare `@property def state(self): ...`.
        """
        return self._state

    @property
    def native_unit_of_measurement(self):
        """Mostra la percentuale in HA."""
        return PERCENTAGE    

    @property
    def icon(self):
        """Icona personalizzata (mdi:printer-3d, ad esempio)."""
        return "mdi:printer-3d"    

    @property
    def state_class(self):
        """
        Aggiunge maggiori info sulle funzionalità del sensore:
        - SensorStateClass.MEASUREMENT (valore "istantaneo")
        - SensorStateClass.TOTAL
        - SensorStateClass.TOTAL_INCREASING
        - ...
        Qui, essendo una “misura” di avanzamento, potresti usare MEASUREMENT.
        """
        return SensorStateClass.MEASUREMENT    

    @property
    def device_info(self):
        """Return device information for Home Assistant."""
        return {
            "identifiers": {(DOMAIN, self._ip_address)},
            "name": f"Printer ({self._ip_address})",
            "manufacturer": "HAGhost5",
            "model": "3D Printer",
            "sw_version": "1.0",
        }   
        
    @property
    def unique_id(self):
        """Return a truly unique ID for the sensor."""
        return f"{self._ip_address}_printer_m27_status"
        
    async def process_message(self, message):
        """Process a WebSocket message and extract M27 status."""
        try:
            # Cerca un messaggio che inizia con "M27"
            pattern = r"M27\s+([^\s]+)"
            match = re.search(pattern, message)
            if match:
                self._state = match.group(1)  # Lo stato estratto dal messaggio
                self._attributes = {
                    "last_update": datetime.now().isoformat(),
                    "raw_message": message,
                }
                _LOGGER.debug("Printer M27 Status updated: %s", self._state)
                self.async_write_ha_state()  # Assicurati che venga chiamato
        except Exception as e:
            _LOGGER.error("Error processing message: %s", e)


class PrinterM994Sensor(HAGhost5BaseSensor):
    """Sensor to capture the file name in print (from M994 messages)."""

    def __init__(self, ip_address):
        super().__init__(ip_address, "printer_m994_status")
        self._ip_address = ip_address
        self._state = None
        self._attributes = {}

    def reset(self):
        """Reimposta il sensore allo stato iniziale."""
        self._state = 0
        _LOGGER.info("PrinterM997Sensor reset to 0.")    
    
    @property
    def name(self):
        """Nome visualizzato nel frontend di Home Assistant."""
        return "Printing File Name"

    @property
    def device_class(self):
        """Se non c'è una device_class specifica, restituisci None."""
        return None
    
    @property
    def native_value(self):
        """
        Con il nuovo modello di sensori, si usa `native_value`.
        Sarà il 'nome del file' in stampa.
        """
        return self._state

    @property
    def native_unit_of_measurement(self):
        """
        In questo caso non abbiamo un'unità di misura (es. °C, %, ecc.),
        quindi restituiamo None.
        """
        return None

    @property
    def icon(self):
        """
        Icona personalizzata: potresti usare `mdi:file-code`, 
        `mdi:file-document`, `mdi:file-document-box` o simili.
        """
        return "mdi:file-document"

    @property
    def state_class(self):
        """
        Non è un valore di tipo 'measurement' (non stiamo misurando un contatore),
        quindi possiamo ritornare None.
        """
        return None

    @property
    def extra_state_attributes(self):
        """Eventuali attributi extra da visualizzare in HA."""
        return self._attributes

    @property
    def device_info(self):
        """Return device information for Home Assistant."""
        return {
            "identifiers": {(DOMAIN, self._ip_address)},
            "name": f"Printer ({self._ip_address})",
            "manufacturer": "HAGhost5",
            "model": "3D Printer",
            "sw_version": "1.0",
        }

    @property
    def unique_id(self):
        """Return a truly unique ID for the sensor."""
        return f"{self._ip_address}_printer_m994_status"

    async def process_message(self, message):
        """
        Elabora un messaggio WebSocket che inizia con M994.
        Esempio di messaggio: 
           M994 1:/FBG5_stampo2.2.gcode;-788190462
        """
        try:
            # Cerchiamo una stringa che inizi con "M994", seguita da uno spazio,
            # poi un blocco (es. "1:/FBG5_stampo2.2.gcode") e un separatore ";",
            # infine un valore numerico.
            pattern = r"M994\s+([^;]+);([^\s]+)"
            match = re.search(pattern, message)
            if match:
                file_part = match.group(1)   # "1:/FBG5_stampo2.2.gcode"
                size_part = match.group(2)  # "-788190462" (o qualunque numero)

                # Se preferisci "ripulire" l'eventuale prefisso "1:/", puoi farlo qui.
                # Esempio:
                if file_part.startswith("1:/"):
                    file_part = file_part[3:]

                self._state = file_part  # Memorizziamo come stato il nome del file
                self._attributes = {
                    "last_update": datetime.now().isoformat(),
                    "raw_message": message,
                    "possible_size": size_part,  # Sconosciuto, ma lo salviamo
                }
                _LOGGER.debug("Printer M994 filename updated: %s", self._state)
                self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Error processing M994 message: %s", e)


class PrinterM992Sensor(HAGhost5BaseSensor):
    """Sensor that captures the time elapsed (M992) converting HH:mm:ss to seconds."""

    def __init__(self, ip_address):
        super().__init__(ip_address, "printer_m992_status")
        self._ip_address = ip_address
        self._state = None  # qui memorizzeremo i secondi (int)
        self._attributes = {}

    @property
    def name(self):
        return "Elapsed Print Time"

    def reset(self):
        """Reimposta il sensore allo stato iniziale."""
        self._state = 0
        _LOGGER.info("PrinterM997Sensor reset to 0.")    
    
    @property
    def native_value(self):
        """
        Restituiamo un int che rappresenta il tempo in secondi.
        """
        return self._state

    @property
    def native_unit_of_measurement(self):
        """
        Indica che stiamo fornendo il tempo in secondi.
        """
        return UnitOfTime.SECONDS  # "s" se preferisci la stringa classica

    @property
    def icon(self):
        return "mdi:timer"

    @property
    def state_class(self):
        """
        Indica che si tratta di un valore di misura 'istantaneo'.
        Potresti anche considerare 'total_increasing', 
        ma di solito MEASUREMENT è sufficiente.
        """
        return SensorStateClass.MEASUREMENT

    @property
    def extra_state_attributes(self):
        return self._attributes

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._ip_address)},
            "name": f"Printer ({self._ip_address})",
            "manufacturer": "HAGhost5",
            "model": "3D Printer",
            "sw_version": "1.0",
        }

    @property
    def unique_id(self):
        return f"{self._ip_address}_printer_elapsed_time"

    async def process_message(self, message):
        """
        Esempio di messaggio: 
           M992 00:46:49
        """
        try:
            pattern = r"M992\s+(\d{2}:\d{2}:\d{2})"
            match = re.search(pattern, message)
            if match:
                time_string = match.group(1)  # "00:46:49"

                # Converti la stringa in un oggetto datetime (fittizio) 
                # e poi calcola i secondi totali
                t = datetime.strptime(time_string, "%H:%M:%S")
                # Di default, la data sarà 1900-01-01; 
                # usiamo total_seconds rispetto a mezzanotte:
                seconds_elapsed = t.hour * 3600 + t.minute * 60 + t.second

                self._state = seconds_elapsed
                self._attributes = {
                    "last_update": datetime.now().isoformat(),
                    "raw_message": message,
                    "formatted_time": time_string  # manteniamo l'HH:mm:ss negli attributi
                }
                _LOGGER.debug(
                    "Printer M992 time updated: %s (%s seconds)",
                    time_string, self._state
                )
                if self.hass is not None:
                    self.async_write_ha_state()
                else:
                    _LOGGER.warning("Sensor not yet added to HA. Skipping state update...")
        except Exception as e:
            _LOGGER.error("Error processing M992 message: %s", e)

class TBedSensor(HAGhost5BaseSensor):
    """Sensor for the bed temperature (extracts the value after B:)."""

    def __init__(self, ip_address):
        super().__init__(ip_address, "tbed_sensor")
        self._ip_address = ip_address
        self._state = None
        self._attributes = {}

    @property
    def name(self):
        return "Bed Temperature"

    @property
    def device_class(self):
        return SensorDeviceClass.TEMPERATURE

    @property
    def native_unit_of_measurement(self):
        return UnitOfTemperature.CELSIUS

    @property
    def icon(self):
        return "mdi:thermometer"

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Valore dello stato (temperatura)."""
        return self._state

    @property
    def device_info(self):
        """Raggruppa il sensore sotto il device della stampante."""
        return {
            "identifiers": {(DOMAIN, self._ip_address)},
            "name": f"Printer ({self._ip_address})",
            "manufacturer": "HAGhost5",
            "model": "3D Printer",
            "sw_version": "1.0",
        }

    @property
    def unique_id(self):
        """ID univoco per il sensore bed."""
        return f"{self._ip_address}_bed_temp"

    async def process_message(self, message):
        """
        Cerca la temperatura del bed subito dopo 'B:'.
        Esempio di stringa: "T:199 /200 B:60 /60 T0:199 /200 T1:0 /0 @:0 B@:0"
        """
        try:
            pattern = r"B:([\d\.]+)"
            match = re.search(pattern, message)
            if match:
                bed_temp = float(match.group(1))
                self._state = bed_temp
                self._attributes = {
                    "last_update": datetime.now().isoformat(),
                    "raw_message": message,
                }
                _LOGGER.debug("Bed temperature updated: %s", bed_temp)

                if self.hass is not None:
                    self.async_write_ha_state()
                else:
                    _LOGGER.warning("Bed sensor not yet in HA. Skipping state update...")

        except Exception as e:
            _LOGGER.error("Error processing bed temperature message: %s", e)

class TNozzleSensor(HAGhost5BaseSensor):
    """Sensor for the nozzle temperature (extracts the value after T:)."""

    def __init__(self, ip_address):
        super().__init__(ip_address, "tnozzle_sensor")
        self._ip_address = ip_address
        self._state = None
        self._attributes = {}

    @property
    def name(self):
        """Nome visualizzato in Home Assistant."""
        return "Nozzle Temperature"

    @property
    def device_class(self):
        """Tipo di sensore per HA (temperatura)."""
        return SensorDeviceClass.TEMPERATURE

    @property
    def native_unit_of_measurement(self):
        """Unità di misura (°C)."""
        return UnitOfTemperature.CELSIUS

    @property
    def icon(self):
        """Icona personalizzata."""
        return "mdi:thermometer"

    @property
    def state_class(self):
        """Misurazione istantanea (Measurement)."""
        return SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Valore dello stato (temperatura)."""
        return self._state

    @property
    def device_info(self):
        """Raggruppa il sensore sotto il device della stampante."""
        return {
            "identifiers": {(DOMAIN, self._ip_address)},
            "name": f"Printer ({self._ip_address})",
            "manufacturer": "HAGhost5",
            "model": "3D Printer",
            "sw_version": "1.0",
        }

    @property
    def unique_id(self):
        """ID univoco per il sensore nozzle."""
        return f"{self._ip_address}_nozzle_temp"

    async def process_message(self, message):
        """
        Cerca la temperatura nozzle subito dopo 'T:'.
        Esempio di stringa: "T:199 /200 B:60 /60 T0:199 /200 T1:0 /0 @:0 B@:0"
        """
        try:
            pattern = r"T:([\d\.]+)"
            match = re.search(pattern, message)
            if match:
                nozzle_temp = float(match.group(1))
                self._state = nozzle_temp
                self._attributes = {
                    "last_update": datetime.now().isoformat(),
                    "raw_message": message,
                }
                _LOGGER.debug("Nozzle temperature updated: %s", nozzle_temp)

                if self.hass is not None:
                    self.async_write_ha_state()
                else:
                    _LOGGER.warning("Nozzle sensor not yet in HA. Skipping state update...")

        except Exception as e:
            _LOGGER.error("Error processing nozzle temperature message: %s", e)

