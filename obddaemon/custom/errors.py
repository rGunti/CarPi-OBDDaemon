"""
CARPI OBD II DAEMON
(C) 2018, Raphael "rGunti" Guntersweiler
Licensed under MIT
"""
from carpicommons.errors import CarPiExitException


class SerialObdError(CarPiExitException):
    DEFAULT_EXIT_CODE = 0xFC00

    REASON_CONNECTION_ERROR = 0x01
    REASON_NO_DEVICE = 0x04

    REASON_CONFIG_ERROR_BASE = 0x10

    def __init__(self, reason_code: int = 0):
        super().__init__(SerialObdError.DEFAULT_EXIT_CODE + reason_code)
        self._reason = reason_code

    @property
    def reason(self):
        return self._reason


class SerialObdConnectionError(SerialObdError):
    def __init__(self):
        super().__init__(SerialObdError.REASON_CONNECTION_ERROR)


class SerialObdDeviceNotFound(SerialObdError):
    def __init__(self):
        super().__init__(SerialObdError.REASON_NO_DEVICE)


class SerialObdConfigurationError(SerialObdError):
    SUBREASON_CONFIG_INVALID_BAUDRATE = 0x11
    SUBREASON_CONFIG_NO_DEVICE = 0x14

    def __init__(self, sub_reason: int = 0):
        super().__init__(SerialObdError.REASON_CONFIG_ERROR_BASE + sub_reason)
        self._sub_reason = sub_reason

    @property
    def sub_reason(self):
        return self._sub_reason

    @staticmethod
    def no_device_configured():
        return SerialObdConfigurationError(
            SerialObdConfigurationError.SUBREASON_CONFIG_NO_DEVICE)

    @staticmethod
    def invalid_baudrate():
        return SerialObdConfigurationError(
            SerialObdConfigurationError.SUBREASON_CONFIG_INVALID_BAUDRATE)
