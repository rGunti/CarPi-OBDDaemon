"""
CARPI OBD II DAEMON
(C) 2018, Raphael "rGunti" Guntersweiler
Licensed under MIT
"""

from carpicommons.errors import CarPiExitException


class ObdConnectionError(CarPiExitException):
    DEFAULT_EXIT_CODE = 0xFB00

    REASON_UNKNOWN = 0x0
    REASON_NO_DEVICE = 0x1
    REASON_DEVICE_FAILURE = 0x2

    REASON_NO_DATA_CONNECTION = 0x10

    def __init__(self, reason_code: int = 0):
        super().__init__(ObdConnectionError.DEFAULT_EXIT_CODE + reason_code)
        self._reason = reason_code

    @property
    def reason(self):
        return self._reason
