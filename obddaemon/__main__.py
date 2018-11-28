"""
CARPI OBD II DAEMON
(C) 2018, Raphael "rGunti" Guntersweiler
Licensed under MIT
"""
from logging import DEBUG

from carpicommons.log import DEFAULT_CONFIG
from daemoncommons.daemon import DaemonRunner

from obddaemon.daemon import ObdDaemon

if __name__ == '__main__':
    d = DaemonRunner('OBD_DAEMON_CFG', ['obd.ini', '/etc/carpi/obd.ini'])
    d.run(ObdDaemon())
