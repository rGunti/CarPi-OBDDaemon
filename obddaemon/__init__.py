"""
CARPI OBD II DAEMON
(C) 2018, Raphael "rGunti" Guntersweiler
Licensed under MIT
"""
from daemoncommons.daemon import DaemonRunner

from obddaemon.daemon import ObdDaemon

if __name__ == '__main__':
    d = DaemonRunner('OBD_DAEMON_CFG', ['gps.ini', '/etc/carpi/gps.ini'])
    d.run(ObdDaemon())
