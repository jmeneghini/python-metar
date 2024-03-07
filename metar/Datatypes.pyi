from typing import Literal, Optional, Union
from metar.Units import Quantity

GreaterOrLess = Literal[">", "<"]
Value = Union[str, float]

TemperatureUnit = Literal["F", "C", "K", "f", "c", "k"]

def _add_units(instance: object) -> None: ...

def _get_unit_string(instance: object, unit_str: str, precision: int = 1) -> str: ...

class temperature:
    _units: TemperatureUnit
    _value: Quantity

    def __init__(self, value: Value, units: TemperatureUnit = "C") -> None: ...
    def __str__(self) -> str: ...
    def value(self) -> Quantity: ...
    def string(self, units: Optional[TemperatureUnit] = None) -> str: ...

PressureUnit = Literal["MB", "HPA", "IN", "mb", "hPa", "in"]

class pressure:
    _units: PressureUnit
    _value: Quantity

    def __init__(self, value: Value, units: PressureUnit = "MB") -> None: ...
    def __str__(self) -> str: ...
    def value(self) -> Quantity: ...
    def string(self, units: Optional[PressureUnit] = None) -> str: ...

SpeedUnit = Literal["KT", "MPS", "KMH", "MPH", "kt", "mps", "kmh", "mph"]

class speed:
    _units: SpeedUnit
    _value: Quantity
    _gtlt: GreaterOrLess

    def __init__(
        self,
        value: Value,
        units: Optional[SpeedUnit] = None,
        gtlt: Optional[GreaterOrLess] = None,
    ) -> None: ...
    def __str__(self) -> str: ...
    def value(self) -> Quantity: ...
    def string(self, units: Optional[SpeedUnit] = None) -> str: ...

DistanceUnit = Literal[
    "SM", "MI", "M", "KM", "FT", "IN", "sm", "mi", "m", "km", "ft", "in"
]

class distance:
    _units: DistanceUnit
    _value: Quantity
    _gtlt: GreaterOrLess
    _num: Optional[int]
    _den: Optional[int]

    def __init__(
        self,
        value: Value,
        units: Optional[DistanceUnit] = None,
        gtlt: Optional[GreaterOrLess] = None,
    ) -> None: ...
    def __str__(self) -> str: ...
    def value(self) -> Quantity: ...
    def string(self, units: Optional[DistanceUnit] = None) -> str: ...

CompassDirection = Literal[
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
]

class direction:
    _compass: Optional[CompassDirection]
    _degrees: Quantity

    def __init__(
        self,
        d: Union[CompassDirection, Value],
    ): ...
    def __str__(self) -> str: ...
    def value(self) -> Quantity: ...
    def string(self) -> str: ...
    def compass(self) -> CompassDirection: ...

PrecipitationUnit = Literal["IN", "CM", "in", "cm"]

class precipitation(object):
    _units: PrecipitationUnit
    _value: Quantity
    _gtlt: GreaterOrLess
    _istrace: bool

    def __init__(
        self,
        value: Value,
        units: Optional[PrecipitationUnit] = None,
        gtlt: Optional[GreaterOrLess] = None,
    ) -> None: ...
    def __str__(self) -> str: ...
    def value(self) -> Quantity: ...
    def string(self, units: Optional[PrecipitationUnit] = None) -> str: ...
    def istrace(self) -> bool: ...

class position:
    latitude: Optional[float]
    longitude: Optional[float]

    def __init__(
        self, latitude: Optional[float] = None, longitude: Optional[float] = None
    ): ...
    def __str__(self) -> str: ...
    def getdirection(self, position2: "position") -> direction: ...
