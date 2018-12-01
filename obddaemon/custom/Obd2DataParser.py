#!/usr/bin/env python
"""
MIT License

Copyright (c) 2017 Raphael "rGunti" Guntersweiler

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

This is a reworked version of https://github.com/rgunti/carpi
Notable changes:
 - Switched logging
 - changed some function names to lower case notation
 - Removed unrequired references
"""

from carpicommons.log import logger

log = logger('OBD DataParser')


UNABLE_TO_CONNECT = 'UNABLE TO CONNECT'


class ObdPidParserUnknownError(Exception):
    def __init__(self, type, val=None):
        """
        :param str type: OBD PID
        :param str val: (optional) value received to parse
        """
        log.warning("Failed to parse OBD message %s, value was %s",
                    type, val)
        self.type = type
        self.val = val


def is_unable_to_connect(v: str):
    return v.endswith(UNABLE_TO_CONNECT)


def trim_obd_value(v):
    """
    Trims unneeded data from an OBD response
    :param str v:
    :return str:
    """
    if not v or len(v) < 4:
        return ''
    else:
        return v[4:]


# def prepare_value(v):
#     """
#     :param str v:
#     :return str:
#     """
#     log.debug('Preparing value {}'.format(v))
#     a = v.split('|')
#     if len(a) >= 2 and a[1] != '>':
#         log.debug('Returning {} for {}'.format(a[1], v))
#         return a[1]
#     else:
#         log.debug('Returning NONE for {}'.format(v))
#         return None


def parse_value(type: str, val: str):
    """
    Parses a given OBD value of a given type (PID)
    and returns the parsed value.
    If the PID is unknown / not implemented a PIDParserUnknownError
    will be raised including the type which was unknown
    :param type:
    :param val:
    :return:
    """
    if type.upper() in PARSER_MAP:
        #prep_val = prepare_value(val)
        out = PARSER_MAP[type](val)
        log.debug('For {} entered {}, got {} out'.format(type, val, out))
        return out
    else:
        raise ObdPidParserUnknownError(type, val)


def parse_obj(o):
    """
    Parses a given dictionary with the key being the OBD PID and the value its
    returned value by the OBD interface
    :param dict o:
    :return:
    """
    r = {}
    for k, v in o.items():
        if is_unable_to_connect(v):
            r[k] = None

        try:
            r[k] = parse_value(k, v)
        except (ObdPidParserUnknownError, AttributeError, TypeError):
            r[k] = None
    return r


# def transform_obj(o):
#     r = {}
#     for k, v in o.items():
#         if v is tuple:
#             keys = OBD_REDIS_MAP[k]
#             r[keys[0]] = v[0]
#             r[keys[1]] = v[1]
#         else:
#             r[OBD_REDIS_MAP[k]] = v
#     return r


def parse_atrv(v):
    """
    Parses the battery voltage and returns it in [Volt] as float with 1 decimal place
    :param str v: e.g. "12.3V"
    :return float:
    """
    try:
        return float(v.replace('V', ''))
    except ValueError:
        return None


def parse_0101(v):
    """
    Parses the DTC status and returns two elements.
    https://en.wikipedia.org/wiki/OBD-II_PIDs#Mode_1_PID_01
    :param v:
    :return bool, int:
    """
    tv = trim_obd_value(v)
    mil_status = None  # type: bool
    num_dtc = None  # type: int

    try:
        byte_a = int(v[:2], 16)
        mil_status = byte_a / 0xF >= 1
        num_dtc = mil_status % 0xF
    except ValueError:
        mil_status = None
        num_dtc = None

    return mil_status, num_dtc


def parse_0103(v):
    """
    Parses the fuel system status and returns an array with two elements (one for
    each fuel system).
    The returned values are converted to decimal integers and returned as is.
    The fuel system values are described here:
    https://en.wikipedia.org/wiki/OBD-II_PIDs#Mode_1_PID_03

    1  Open loop due to insufficient engine temperature

    2  Closed loop, using oxygen sensor feedback to determine fuel mix

    4  Open loop due to engine load OR fuel cut due to deceleration

    8  Open loop due to system failure

    16 Closed loop, using at least one oxygen sensor but there is a fault in the feedback system

    :param str v: e.g. "41030100"
    :return int, int:
    """
    tv = trim_obd_value(v)  # trimmed value
    status_1, status_2 = None, None
    try:
        status_1 = int(v[:2], 16)
    except ValueError:
        status_1 = None

    try:
        status_2 = int(v[2:4], 16)
    except ValueError:
        status_2 = None

    return status_1, status_2


def parse_0104(v):
    """
    Parses the calculated engine load and returns it as an integer from 0 - 100
    :param str v: e.g. "410405"
    :return int: e.g. 2
    """
    try:
        val = int(trim_obd_value(v), 16)
        return val / 2.55
    except ValueError:
        return None


def parse_010b(v):
    """
    Parses Intake MAP and returns it in [kPa] as an integer from 0 - 255
    :param str v:
    :return int:
    """
    try:
        return int(trim_obd_value(v), 16)
    except ValueError:
        return None


def parse_010c(v) -> int:
    """
    Parses Engine RPM and returns it in [RPM] as a float from 0 - 16383.75
    :param str v:
    :return int:
    """
    try:
        val = int(trim_obd_value(v), 16)
        return int(val / 4)
    except ValueError:
        return None


def parse_010d(v):
    """
    Parses Vehicle Speed and returns it in [km/h] as an integer from 0 - 255
    :param str v:
    :return int:
    """
    try:
        return int(trim_obd_value(v), 16)
    except ValueError:
        return None


def parse_010f(v):
    """
    Parses Intake Air Temperature and returns it in [degrees C] as an integer from -40 - 215
    :param str v:
    :return int:
    """
    try:
        val = int(trim_obd_value(v), 16)
        return val - 40
    except ValueError:
        return None


def parse_0134_013b(v):
    """
    Parses the O2 Sensor Value (0134 - 013B) and returns two values parsed from it:
    1. Fuel-Air Equivalence [Ratio] as a float from 0 - 2
    2. Current in [mA] as a float from -128 - 128
    :param str v:
    :return tuple of float, float:
    """
    try:
        trim_val = trim_obd_value(v)
        val_ab = int(trim_val[0:2], 16)
        val_cd = int(trim_val[2:4], 16)
        return (2 / 65536) * val_ab, val_cd - 128
    except ValueError:
        return None, None


PARSER_MAP = {
    'ATRV': parse_atrv,
    '0101': parse_0101,
    '0103': parse_0103,
    '0104': parse_0104,
    '0105': parse_010f,  # 0105 is parsed the same way as 010f
    '010B': parse_010b,
    '010C': parse_010c,
    '010D': parse_010d,
    '010F': parse_010f,
    '0134': parse_0134_013b,
    '0135': parse_0134_013b,
    '0136': parse_0134_013b,
    '0137': parse_0134_013b,
    '0138': parse_0134_013b,
    '0139': parse_0134_013b,
    '013A': parse_0134_013b,
    '013B': parse_0134_013b
}

OBD_REDIS_MAP = {
    'ATRV': None,
    '0101': None,
    '0103': None,
    '0104': None,
    '0105': None,
    '010B': None,
    '010C': None,
    '010D': None,
    '010F': None,
    '0134': None,
    '0135': None,
    '0136': None,
    '0137': None,
    '0138': None,
    '0139': None,
    '013A': None,
    '013B': None,
}

if __name__ == "__main__":
    print("This script is not intended to be run standalone!")
