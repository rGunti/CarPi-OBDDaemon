"""
CARPI OBD II DAEMON
(C) 2018, Raphael "rGunti" Guntersweiler
Licensed under MIT
"""
from logging import Logger
from time import sleep

from obd import OBD, Async, commands
from carpicommons.errors import CarPiExitException
from carpicommons.log import logger
from daemoncommons.daemon import Daemon
from redisdatabus.bus import BusWriter

from obddaemon import keys


class ObdConnectionError(CarPiExitException):
    DEFAULT_EXIT_CODE = 0xFB00

    REASON_UNKNOWN = 0x0
    REASON_NO_DEVICE = 0x1
    REASON_DEVICE_FAILURE = 0x2

    def __init__(self, reason_code: int = 0):
        super().__init__(ObdConnectionError.DEFAULT_EXIT_CODE + reason_code)
        self._reason = reason_code

    @property
    def reason(self):
        return self._reason


class ObdDaemon(Daemon):
    def __init__(self):
        super().__init__("OBD II Daemon")
        self._log: Logger = None
        self._obd: Async = None
        self._bus: BusWriter = None
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

        retries = 5

        self._bus = bus = self._build_bus_writer()
        cmds = [
            (commands.FUEL_STATUS, self._create_callback(keys.KEY_FUEL_STATUS)),
            (commands.COOLANT_TEMP, self._create_callback(keys.KEY_COOLANT_TEMP)),
            (commands.INTAKE_PRESSURE, self._create_callback(keys.KEY_INTAKE_PRESSURE)),
            (commands.RPM, self._create_callback(keys.KEY_RPM)),
            (commands.SPEED, self._create_callback(keys.KEY_SPEED)),
            (commands.INTAKE_TEMP, self._create_callback(keys.KEY_INTAKE_TEMP))
        ]

        while retries > 0:
            log.info("Connecting to OBD II interface ...")
            self._obd = obd = Async()

            if obd.is_connected():
                for cmd in cmds:
                    obd.watch(cmd)

                obd.start()
                self._running = True
                while self._running:
                    sleep(1)
            else:
                log.warning("Failed to connect to OBD II interface, retrying %s more times ...", retries)
                retries -= 1
                if retries <= 0:
                    log.error("Could not establish a connection to an OBD II interface!\n"
                              "Check if an OBD II device is connected via a serial interface "
                              "and try again.\n"
                              "If you use auto-config, try specifying the device in the configuration file.")
                    raise ObdConnectionError()

            sleep(5)

        self._log.info("The OBD II daemon is shutting down ...")

    def _create_callback(self, channel: str):
        return lambda v: self._publish_message(channel, v)

    def _publish_message(self, channel: str, value):
        self._bus.publish(channel, value)

    def shutdown(self):
        self._log.info("Shutting down %s ...", self.name)
        self._running = False

        if self._obd and self._obd.is_connected():
            self._log.info("Terminating OBD II connection ...")
            self._obd.stop()
