# Copyright (c) 2004,2018 Python-Metar Developers.
# Distributed under the terms of the BSD 2-Clause License.
# SPDX-License-Identifier: BSD-2-Clause
"""Python module to provide station information from the ICAO identifiers."""
import os
from shapely.geometry import Point
from numpy import nan
import json


class station:
    """An object representing a weather station."""

    def __init__(
        self, id, name = None, state=None, country=None, latitude=nan, longitude=nan
    ):
        self.id = id
        self.name = name
        self.state = state
        self.country = country
        self.position = Point(float(longitude), float(latitude))



current_dir = os.path.dirname(__file__)
station_file_name = os.path.join(current_dir, ".stations.json")

stations = {}

# open json file
with open(station_file_name) as f:
    data = json.load(f)
    # set stations with data from json file
    for set in data:
        stations[set['icaoId']] = station(set['icaoId'], set['site'], set['state'], set['country'], set['lat'], set['lon'])
    
