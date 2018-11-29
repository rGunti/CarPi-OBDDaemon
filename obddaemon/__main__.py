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
        # DEFAULT_CONFIG['handlers']['fi'] = {}
        # DEFAULT_CONFIG['handlers']['fi']['class'] = 'logging.handlers.RotatingFileHandler'
        # DEFAULT_CONFIG['handlers']['fi']['level'] = DEBUG
        # DEFAULT_CONFIG['handlers']['fi']['formatter'] = 'f'
        # DEFAULT_CONFIG['handlers']['fi']['filename'] = 'obd.{}.log'.format(datetime.now().strftime('%Y%m%d-%H%M%S'))
        # DEFAULT_CONFIG['handlers']['fi']['maxBytes'] = 1024 * 1024 * 10  # 10 MB
        # DEFAULT_CONFIG['handlers']['fi']['backupCount'] = 64
        DEFAULT_CONFIG['root']['level'] = DEBUG
        # DEFAULT_CONFIG['root']['handlers'] = ['h', 'fi']

    d = DaemonRunner('OBD_DAEMON_CFG', ['obd.ini', '/etc/carpi/obd.ini'])
    d.run(SerialObdDaemon() if '--serial' in argv else ObdDaemon())
