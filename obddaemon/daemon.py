"""
CARPI OBD II DAEMON
(C) 2018, Raphael "rGunti" Guntersweiler
Licensed under MIT
"""
from logging import Logger
from time import sleep

from carpicommons.log import logger
from daemoncommons.daemon import Daemon
from obd import OBD, Async, commands, OBDResponse, Unit
from obd.codes import FUEL_STATUS
from redisdatabus.bus import BusWriter

from obddaemon.errors import ObdConnectionError
from obddaemon.keys import KEY_FUEL_STATUS, KEY_VOLTAGE, KEY_RPM
from . import keys


class ObdDaemon(Daemon):
    CHECK_DATA_CONNECTION_ON_CHANNELS = [
        KEY_VOLTAGE,
        KEY_RPM
    ]

    def __init__(self):
        super().__init__("OBD II Daemon")
        self._log: Logger = None
        self._obd: OBD = None
        self._bus: BusWriter = None
        self._running = False
        self._missing_data_counter = 0
        self._throw_after_empty_frames = -1

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

        self._bus = self._build_bus_writer()
        cmds = [
            #(commands.ELM_VOLTAGE, self._create_callback(keys.KEY_VOLTAGE)),
            (commands.FUEL_STATUS, self._create_callback(keys.KEY_FUEL_STATUS)),
            (commands.COOLANT_TEMP, self._create_callback(keys.KEY_COOLANT_TEMP)),
            (commands.INTAKE_PRESSURE, self._create_callback(keys.KEY_INTAKE_PRESSURE)),
            (commands.RPM, self._create_callback(keys.KEY_RPM)),
            (commands.SPEED, self._create_callback(keys.KEY_SPEED)),
            (commands.INTAKE_TEMP, self._create_callback(keys.KEY_INTAKE_TEMP))
        ]

        use_async = self._get_config_bool('OBD', 'Async', False)
        self._throw_after_empty_frames = self._get_config_int('OBD', 'StopAfterXEmptyFrames', -1)

        while retries > 0:
            log.info("Connecting to OBD II interface ...")

            port = self._get_config('OBD', 'Port', None)
            baudrate = self._get_config_int('OBD', 'Baudrate', None)
            fast_init = self._get_config_bool('OBD', 'FastInit', True)
            timeout = self._get_config_float('OBD', 'Timeout', 1)

            if port:
                log.debug("Connecting to %s", port)
            else:
                log.debug("Using Autodetect to find OBD device")

            if use_async:
                log.debug("Using Async instance")
                log.warning("Async can DOS your car! Use it at your own risk!")
                log.warning("OBD.StopAfterXEmptyFrames is not supported under Async mode.")
                self._obd = obd_inst = Async(portstr=port,
                                             baudrate=baudrate,
                                             fast=fast_init,
                                             timeout=timeout)
            else:
                log.debug("Using manual instance")
                self._obd = obd_inst = OBD(portstr=port,
                                           baudrate=baudrate,
                                           fast=fast_init,
                                           timeout=timeout)

            if obd_inst.is_connected():
                log.debug("Connected via %s using %s",
                          obd_inst.port_name(),
                          obd_inst.protocol_name())
                log.info("Setting up data fetcher ...")
                if use_async:
                    for cmd in cmds:
                        log.debug("Watching for %s", cmd[0])
                        obd_inst.watch(cmd[0], callback=cmd[1])

                    obd_inst.start()
                    log.info("Started watching")

                self._running = True
                log.info("Entering main loop...")
                while self._running:
                    if not use_async:
                        for cmd in cmds:
                            a = obd_inst.query(cmd[0])
                            cmd[1](a)
                    sleep(1)
            else:
                log.warning("Failed to connect to OBD II interface, retrying %s more times ...", retries)
                retries -= 1
                if retries <= 0:
                    log.error("Could not establish a connection to an OBD II interface!\n"
                              "Check if an OBD II device is connected via a serial interface "
                              "and try again.\n"
                              "If you use auto-config, try specifying the device in the configuration file.")
                    raise ObdConnectionError(ObdConnectionError.REASON_NO_DEVICE)

            sleep(5)

        self._log.info("The OBD II daemon is shutting down ...")

    def _create_callback(self, channel: str):
        return lambda v: self._publish_message(channel, v)

    def _publish_message(self, channel: str, value: OBDResponse):
        if value.is_null():
            v = 0
        else:
            if channel == KEY_FUEL_STATUS:
                v = FUEL_STATUS.index(value.value[0]) \
                    if value.value[0] in FUEL_STATUS \
                    else -1
            elif type(value.value) is Unit.Quantity:
                v = value.value  # type: Unit.Quantity
                v = v.m
            else:
                v = 0

        if channel in ObdDaemon.CHECK_DATA_CONNECTION_ON_CHANNELS:
            self._do_missing_value_check(value.value)

        self._log.debug("%s: %s (%s)", channel, v, value.value)
        self._bus.publish(channel, str(v))

    def _do_missing_value_check(self, val):
        if val is None:
            self._missing_data_counter += 1
            self._log.debug("Counter %s empty data frames", self._missing_data_counter)

            if self._missing_data_counter >= self._throw_after_empty_frames >= 0:
                self._log.warning("Encountered no data for %s frames", self._missing_data_counter)
                raise ObdConnectionError(ObdConnectionError.REASON_NO_DATA_CONNECTION)

            return True
        else:
            self._missing_data_counter = 0
            return False

    def shutdown(self):
        if self._log:
            self._log.info("Shutting down %s ...", self.name)
        self._running = False

        if self._obd and self._obd.is_connected():
            if self._log:
                self._log.info("Terminating OBD II connection ...")

            if self._obd is Async:
                self._obd.stop()
            self._obd.close()
