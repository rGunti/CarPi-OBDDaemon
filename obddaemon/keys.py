"""
CARPI OBD II DAEMON
(C) 2018, Raphael "rGunti" Guntersweiler
Licensed under MIT
"""
from redisdatabus.bus import TypedBusListener

KEY_BASE = 'carpi.obd.'


def build_key(type, name):
    global KEY_BASE
    return "{}{}{}".format(type, KEY_BASE, name)


KEY_VOLTAGE = build_key(TypedBusListener.TYPE_PREFIX_FLOAT, "voltage")
KEY_FUEL_STATUS = build_key(TypedBusListener.TYPE_PREFIX_INT, "fuel_status")
KEY_COOLANT_TEMP = build_key(TypedBusListener.TYPE_PREFIX_INT, "coolant_temp")
KEY_INTAKE_PRESSURE = build_key(TypedBusListener.TYPE_PREFIX_INT, "intake_pressure")
KEY_RPM = build_key(TypedBusListener.TYPE_PREFIX_INT, "rpm")
KEY_SPEED = build_key(TypedBusListener.TYPE_PREFIX_INT, "speed")
KEY_INTAKE_TEMP = build_key(TypedBusListener.TYPE_PREFIX_INT, "temperature")


ALL_KEYS = [
    KEY_VOLTAGE,
    KEY_FUEL_STATUS,
    KEY_COOLANT_TEMP,
    KEY_INTAKE_PRESSURE,
    KEY_RPM,
    KEY_SPEED,
    KEY_INTAKE_TEMP
]
