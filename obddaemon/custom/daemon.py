"""
CARPI OBD II DAEMON
(C) 2018, Raphael "rGunti" Guntersweiler
Licensed under MIT
"""
from logging import Logger
from math import isnan
from os.path import exists
from pprint import pprint
from time import sleep

from carpicommons.errors import CarPiExitException

import obddaemon.keys as ObdKeys

from carpicommons.log import logger
from daemoncommons.daemon import Daemon
from redisdatabus.bus import BusWriter
from serial import Serial, SerialException

import obddaemon.custom.errors as errors
from obddaemon.custom.Obd2DataParser import parse_obj, parse_value


class SerialObdDaemon(Daemon):
    INIT_SEQUENCE = [
        'ATZ',   # reset all settings
        'ATE0',  # don't echo input
        'ATS0',  # print no spaces
        'AT@1',  # print device description
        'ATSI',  # perform slow initialization
    ]

    FETCH_SEQUENCE = [
        'ATRV',  # Battery Voltage
        '0103',  # Fuel System
        # '0105',  # Engine Coolant Temp
        '010B',  # Intake MAP
        '010C',  # RPM
        '010D',  # Speed
        '010F'   # Intake Air Temp
    ]

    OBD_MAPPING = {
        'ATRV': ObdKeys.KEY_VOLTAGE,
        '0103': ObdKeys.KEY_FUEL_STATUS,
        '010B': ObdKeys.KEY_INTAKE_PRESSURE,
        '010C': ObdKeys.KEY_RPM,
        '010D': ObdKeys.KEY_SPEED,
        '010F': ObdKeys.KEY_INTAKE_TEMP
    }

    def __init__(self):
        super().__init__("SerOBD Daemon")
        self._log: Logger = None
        self._bus: BusWriter = None
        self._serial: Serial = None
        self._running = False

    def _build_bus_writer(self) -> BusWriter:
        self._log.info("Connecting to Redis instance ...")
        return BusWriter(host=self._get_config('Redis', 'Host', '127.0.0.1'),
                         port=self._get_config_int('Redis', 'Port', 6379),
                         db=self._get_config_int('Redis', 'DB', 0),
                         password=self._get_config('Redis', 'Password', None))

    def startup(self):
        self._log = log = logger(self.name)
        log.info("Starting up %s ...", self.name)

        self._bus = bus = self._build_bus_writer()

        device = self._get_config('OBD', 'Path', None)
        baudrate = self._get_config_int('OBD', 'Baudrate', 9600)
        timeout = self._get_config_float('OBD', 'Timeout', 1)

        if not device:
            log.error("No device configured!")
            raise errors.SerialObdConfigurationError.no_device_configured()

        if baudrate not in Serial.BAUDRATES:
            log.error("Invalid baudrate supplied: %s", baudrate)

        if not exists(device):
            log.error("Device %s could not be found!", device)
            raise errors.SerialObdDeviceNotFound()

        retries = 5
        while retries > 0:
            try:
                log.info("Connecting ...")
                with Serial(device,
                            baudrate=baudrate,
                            timeout=timeout) as ser:
                    self._serial = ser
                    # sio = TextIOWrapper(BufferedRWPair(ser, ser))

                    ser.write(b'\r')
                    # log.debug("Awaiting response ...")
                    # ser.read_until(b'\r')

                    log.debug("Connection established, running initialization ...")
                    log.info("Running initialization ...")
                    for cmd in SerialObdDaemon.INIT_SEQUENCE:
                        self.send_and_wait(ser, cmd)

                    log.info("Initialization completed, starting data fetching ...")
                    try:
                        while True:
                            d = dict()
                            for c in SerialObdDaemon.FETCH_SEQUENCE:
                                v = self.send_and_wait(ser, c)
                                p = parse_obj({c: v})
                                d[c] = p[c]

                                val = d[c]
                                if val is not None:
                                    bus.publish(SerialObdDaemon.OBD_MAPPING[c], val)

                            if self._get_config_bool('Console', 'DoPprint', False):
                                pprint(d)
                            sleep(0.5)
                    except (KeyboardInterrupt, SystemExit) as e:
                        log.info("Terminating connection upon user request")
                        ser.close()
                        raise e

                self._serial = None
            except CarPiExitException as e:
                raise e
            except SerialException as e:
                log.error("Serial connection error")
            except Exception as e:
                log.error("Error while communicating with Serial device", e)

            retries -= 1
            log.info("Retrying in 5 seconds, repeating %s more times", retries)
            if retries:
                sleep(5)

    def send_and_wait(self, ser: Serial, cmd: str) -> str:
        self._log.debug(" - Sending: %s", cmd)

        enc = str.encode("{}\r".format(cmd))

        ser.write(enc)
        ser.flush()
        resp = ser.read_until(b'\r>')

        if not resp or resp.startswith(b'\xff'):
            self._log.warning(" - [%s] =x Empty or invalid response, connection might be failing soon")
            return None
        else:
            resp = resp.decode('utf-8') \
                .replace('\r', '\n') \
                .replace('>', '') \
                .strip()

        self._log.debug(" - [%s] => %s", cmd, resp)
        return resp

    def shutdown(self):
        super().shutdown()
