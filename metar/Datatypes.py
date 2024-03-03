# Copyright (c) 2004,2018 Python-Metar Developers.
# Distributed under the terms of the BSD 2-Clause License.
# SPDX-License-Identifier: BSD-2-Clause
"""Python classes to represent dimensioned quantities used in weather reports.
"""
import re
from math import sin, cos, atan2, sqrt
import numpy as np
import pint

# exceptions

ureg = pint.UnitRegistry()

class UnitsError(Exception):
    """Exception raised when unrecognized units are used."""

    pass


# regexp to match fractions (used by distance class)
# [Note: numerator of fraction must be single digit.]

FRACTION_RE = re.compile(r"^((?P<int>\d+)\s*)?(?P<num>\d)/(?P<den>\d+)$")

# classes representing dimensioned values in METAR reports


class temperature(object):
    """A class representing a temperature value."""

    legal_units = ["F", "C", "K"]

    def __init__(self, value, units="C"):
        if not units.upper() in temperature.legal_units:
            raise UnitsError("unrecognized temperature unit: '" + units + "'")
        self._units = units.upper()
        try:
            self._value = float(value) * ureg(self._units)
        except ValueError:
            if value.startswith("M"):
                self._value = -float(value[1:])
            else:
                raise ValueError("temperature must be integer: '" + str(value) + "'")

    def __str__(self):
        return self.string()

    def string(self, units=None):
        """Return a string representation of the temperature, using the given units."""
        if units is None:
            units = self._units
        else:
            if not units.upper() in temperature.legal_units:
                raise UnitsError("unrecognized temperature unit: '" + units + "'")
            units = units.upper()
        return f"{self._value.to(units):.1f}"


class pressure(object):
    """A class representing a barometric pressure value."""

    legal_units = ["MB", "HPA", "IN"]

    def __init__(self, value, units="MB"):
        if not units.upper() in pressure.legal_units:
            raise UnitsError("unrecognized pressure unit: '" + units + "'")
        self._value = float(value) * ureg(units)
        self._units = units.upper()

    def __str__(self):
        return self.string()

    def string(self, units=None):
        """Return a string representation of the pressure, using the given units."""
        if not units:
            units = self._units
        else:
            if units.upper() not in pressure.legal_units:
                raise UnitsError("unrecognized pressure unit: '" + units + "'")
            units = units.upper()
        return f"{self._value.to(units):.1f}"


class speed(object):
    """A class representing a wind speed value."""

    legal_units = ["KT", "MPS", "KMH", "MPH"]
    legal_gtlt = [">", "<"]

    def __init__(self, value, units=None, gtlt=None):
        if not units:
            self._units = "MPS"
        else:
            if units.upper() not in speed.legal_units:
                raise UnitsError("unrecognized speed unit: '" + units + "'")
            self._units = units.upper()
        if gtlt and gtlt not in speed.legal_gtlt:
            raise ValueError(
                "unrecognized greater-than/less-than symbol: '" + gtlt + "'"
            )
        self._gtlt = gtlt
        self._value = float(value) * ureg(self._units)

    def __str__(self):
        return self.string()

    def string(self, units=None):
        """Return a string representation of the speed in the given units."""
        if not units:
            units = self._units
        else:
            if units.upper() not in speed.legal_units:
                raise UnitsError("unrecognized speed unit: '" + units + "'")
            units = units.upper()
        text = f"{self._value.to(units):.1f}"
        if self._gtlt == ">":
            text = "greater than " + text
        elif self._gtlt == "<":
            text = "less than " + text
        return text


class distance(object):
    """A class representing a distance value."""

    legal_units = ["SM", "MI", "M", "KM", "FT", "IN"]
    legal_gtlt = [">", "<"]

    def __init__(self, value, units=None, gtlt=None):
        if not units:
            self._units = "M"
        else:
            if units.upper() not in distance.legal_units:
                raise UnitsError("unrecognized distance unit: '" + units + "'")
            self._units = units.upper()

        try:
            if value.startswith("M"):
                value = value[1:]
                gtlt = "<"
            elif value.startswith("P"):
                value = value[1:]
                gtlt = ">"
        except:
            pass
        if gtlt and gtlt not in distance.legal_gtlt:
            raise ValueError(
                "unrecognized greater-than/less-than symbol: '" + gtlt + "'"
            )
        self._gtlt = gtlt
        try:
            self._value = float(value) * ureg(self._units)
            self._num = None
            self._den = None
        except ValueError:
            mf = FRACTION_RE.match(value)
            if not mf:
                raise ValueError("distance is not parseable: '" + str(value) + "'")
            df = mf.groupdict()
            self._num = int(df["num"])
            self._den = int(df["den"])
            self._value = float(self._num) / float(self._den)
            if df["int"]:
                self._value += float(df["int"])
            self._value = self._value * ureg(self._units)

    def __str__(self):
        return self.string()

    def string(self, units=None):
        """Return a string representation of the distance in the given units."""
        if not units:
            units = self._units
        else:
            if not units.upper() in distance.legal_units:
                raise UnitsError("unrecognized distance unit: '" + units + "'")
            units = units.upper()
        text = f"{self._value.to(units):.1f}"
        if self._gtlt == ">":
            text = "greater than " + text
        elif self._gtlt == "<":
            text = "less than " + text
        return text


class direction(object):
    """A class representing a compass direction."""

    compass_dirs = {
        "N": 0.0,
        "NNE": 22.5,
        "NE": 45.0,
        "ENE": 67.5,
        "E": 90.0,
        "ESE": 112.5,
        "SE": 135.0,
        "SSE": 157.5,
        "S": 180.0,
        "SSW": 202.5,
        "SW": 225.0,
        "WSW": 247.5,
        "W": 270.0,
        "WNW": 292.5,
        "NW": 315.0,
        "NNW": 337.5,
    }

    def __init__(self, d):
        if d in direction.compass_dirs:
            self._compass = d
            self._degrees = direction.compass_dirs[d]
        else:
            self._compass = None
            value = float(d) * ureg.deg
            if value.magnitude < 0.0 or value.magnitude > 360.0:
                raise ValueError("direction must be 0..360: '" + str(value) + "'")
            self._degrees = value

    def __str__(self):
        return self.string()

    def value(self):
        """Return the numerical direction, in degrees."""
        return self._degrees

    def string(self):
        """Return a string representation of the numerical direction."""
        return "%.0f degrees" % self._degrees

    def compass(self):
        """Return the compass direction, e.g., "N", "ESE", etc.)."""
        if not self._compass:
            degrees = 22.5 * round(self._degrees / 22.5)
            if degrees == 360.0:
                self._compass = "N"
            else:
                for name, d in direction.compass_dirs.items():
                    if d == degrees:
                        self._compass = name
                        break
        return self._compass


class precipitation(object):
    """A class representing a precipitation value."""

    legal_units = ["IN", "CM"]
    legal_gtlt = [">", "<"]

    def __init__(self, value, units=None, gtlt=None):
        if not units:
            self._units = "IN"
        else:
            if not units.upper() in precipitation.legal_units:
                raise UnitsError("unrecognized precipitation unit: '" + units + "'")
            self._units = units.upper()

        try:
            if value.startswith("M"):
                value = value[1:]
                gtlt = "<"
            elif value.startswith("P"):
                value = value[1:]
                gtlt = ">"
        except:
            pass
        if gtlt and gtlt not in precipitation.legal_gtlt:
            raise ValueError(
                "unrecognized greater-than/less-than symbol: '" + gtlt + "'"
            )
        self._gtlt = gtlt
        self._value = float(value)
        # In METAR world, a string of just four or three zeros denotes trace
        self._istrace = value in ["0000", "000"]

    def __str__(self):
        return self.string()

    def value(self, units=None):
        """Return the precipitation in the specified units."""
        if not units:
            return self._value
        else:
            if not units.upper() in precipitation.legal_units:
                raise UnitsError("unrecognized precipitation unit: '" + units + "'")
            units = units.upper()
        if units == self._units:
            return self._value
        if self._units == "CM":
            i_value = self._value * 2.54
        else:
            i_value = self._value
        if units == "CM":
            return i_value * 2.54
        else:
            return i_value

    def string(self, units=None):
        """Return a string representation of the precipitation in the given units."""
        if not units:
            units = self._units
        else:
            if not units.upper() in precipitation.legal_units:
                raise UnitsError("unrecognized precipitation unit: '" + units + "'")
            units = units.upper()
        # A trace is a trace in any units
        if self._istrace:
            return "Trace"
        text = "%.2f" % self.value(units)
        if units == "CM":
            text += "cm"
        else:
            text += "in"
        if self._gtlt == ">":
            text = "greater than " + text
        elif self._gtlt == "<":
            text = "less than " + text
        return text

    def istrace(self):
        """Return a boolean on if this precipitation was a trace"""
        return self._istrace


class position(object):
    """A class representing a location on the earth's surface."""

    def __init__(self, latitude=None, longitude=None):
        self.latitude = latitude
        self.longitude = longitude

    def __str__(self):
        return self.string()

    def getdirection(self, position2):
        """
        Calculate the initial direction to another location.  (The direction
        typically changes as you trace the great circle path to that location.)
        See <http://www.movable-type.co.uk/scripts/LatLong.html>.
        """
        lat1 = self.latitude
        long1 = self.longitude
        lat2 = position2.latitude
        long2 = position2.longitude
        s = -sin(long1 - long2) * cos(lat2)
        c = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(long1 - long2)
        d = atan2(s, c) * 180.0 / math.pi
        if d < 0.0:
            d += 360.0
        return direction(d)
