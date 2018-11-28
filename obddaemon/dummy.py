"""
CARPI OBD II DAEMON
(C) 2018, Raphael "rGunti" Guntersweiler
Licensed under MIT
"""
from time import sleep
from logging import Logger, DEBUG
from typing import Any

from daemoncommons.daemon import Daemon, DaemonRunner
from carpicommons.log import logger, DEFAULT_CONFIG
from obd.codes import FUEL_STATUS
from redisdatabus.bus import BusWriter
import obddaemon.keys as keys


class Entry:
    TYPE_FUEL_STATUS = 'FUEL_STATUS'
    TYPE_COOLANT_TEMP = 'COOLANT_TEMP'
    TYPE_RPM = 'RPM'
    TYPE_SPEED = 'SPEED'
    TYPE_INTAKE_TEMP = 'INTAKE_TEMP'

    ACCEPTED_TYPES = [
        TYPE_FUEL_STATUS,
        TYPE_COOLANT_TEMP,
        TYPE_RPM,
        TYPE_SPEED,
        TYPE_INTAKE_TEMP
    ]

    def __init__(self,
                 type: str,
                 value: str,
                 timestamp: float):
        self._type = type
        self._value = value
        self._timestamp = timestamp
        self._time_dif: float = 0

    @property
    def val_type(self):
        return self._type

    @property
    def value(self):
        return self._value

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def time_dif(self) -> float:
        return self._time_dif

    @time_dif.setter
    def time_dif(self, value: float):
        self._time_dif = value

    @staticmethod
    def parse_line(line: str):
        l = line.strip().split('|')
        timestamp = float(l[0].strip())
        type = l[1].strip()
        value = l[2].strip()

        return Entry(type=type,
                     value=Entry._parse_value(type, value),
                     timestamp=timestamp) \
            if type in Entry.ACCEPTED_TYPES \
            else None

    @staticmethod
    def _parse_value(v_type: str, value: str) -> Any:
        if v_type == Entry.TYPE_FUEL_STATUS:
            v = eval(value)  # type: tuple
            if type(v) is tuple and v[0] in FUEL_STATUS:
                return FUEL_STATUS.index(v[0])
            else:
                return -1

        v = value.split(' ')[0]  # type: str
        if v_type == Entry.TYPE_COOLANT_TEMP \
                or v_type == Entry.TYPE_SPEED \
                or v_type == Entry.TYPE_INTAKE_TEMP:
            return int(v)
        elif v_type == Entry.TYPE_RPM:
            return int(float(v))
        else:
            return None

    def __str__(self) -> str:
        return "{} ({:.3f}): {} = {}".format(self._timestamp,
                                             self._time_dif,
                                             self._type,
                                             self._value)


class ObdDummyDaemon(Daemon):
    def __init__(self, file: str):
        super().__init__("OBD Dummy Daemon ({})".format(file))
        self._log: Logger = None
        self._bus: BusWriter = None
        self._running = False
        self._file = file

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
        entry_mapping = {
            Entry.TYPE_INTAKE_TEMP: keys.KEY_INTAKE_TEMP,
            Entry.TYPE_SPEED: keys.KEY_SPEED,
            Entry.TYPE_RPM: keys.KEY_RPM,
            Entry.TYPE_COOLANT_TEMP: keys.KEY_COOLANT_TEMP,
            Entry.TYPE_FUEL_STATUS: keys.KEY_FUEL_STATUS
        }

        log.info("Loading file into memory ...")
        entries = []
        with open(self._file, 'r') as f:
            last_e = None
            for line in f.readlines():
                e = Entry.parse_line(line)
                if e:
                    entries.append(e)
                    if last_e:
                        e.time_dif = e.timestamp - last_e.timestamp
                    log.debug(e)
                    last_e = e

        e_len = len(entries)
        e_dur = sum([e.time_dif for e in entries])

        log.info("Loaded %s entries (playback time: about %.3f sec), playing back now ...",
                 e_len, e_dur)

        self._running = True
        while self._running:
            log.info("Playback started")

            i = 0
            t = float(0)
            lt = 0
            for e in entries:
                self._publish(entry_mapping[e.val_type], str(e.value))

                if e.time_dif > 30:
                    log.warning("Skipped frame sleep %s as it waits too long (%.1f sec), only sleeping 0.1 sec", i, e.time_dif)
                    sleep(0.1)
                    t += e.time_dif
                    continue
                elif e.time_dif >= 1:
                    log.debug("Longer time dif detected: Entry %s, sleeps for %.2f sec", i, e.time_dif)

                sleep(e.time_dif)

                t += e.time_dif
                i += 1
                if int(t) % 5 == 0 and lt != int(t):
                    log.debug("Played back %s / %s frames (%.1f / %.1f sec)", i, e_len, t, e_dur)
                    lt = int(t)

            log.info("Playback completed, repeating in 5 seconds ...")
            sleep(5)

    def _publish(self, channel: str, val: str):
        self._bus.publish(channel, val)

    def shutdown(self):
        super().shutdown()
        self._running = False


if __name__ == '__main__':
    DEFAULT_CONFIG['root']['level'] = DEBUG
    d = DaemonRunner('OBD_DAEMON_CFG', ['obd.ini', '/etc/carpi/obd.ini'])
    d.run(ObdDummyDaemon('dummy.txt'))
