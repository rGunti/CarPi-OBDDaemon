"""
CARPI OBD II DAEMON
(C) 2018, Raphael "rGunti" Guntersweiler
Licensed under MIT
"""
from logging import DEBUG

from carpicommons.log import DEFAULT_CONFIG
from daemoncommons.daemon import DaemonRunner

from obddaemon.daemon import ObdDaemon
from obddaemon.custom.daemon import SerialObdDaemon

from sys import argv

if __name__ == '__main__':
    if '--debug' in argv:
        DEFAULT_CONFIG['root']['level'] = DEBUG

    d = DaemonRunner('OBD_DAEMON_CFG', ['obd.ini', '/etc/carpi/obd.ini'])
    d.run(SerialObdDaemon() if '--serial' in argv else ObdDaemon())
