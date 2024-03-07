from pint import UnitRegistry

# Initialize a UnitRegistry
ureg = UnitRegistry()

# Define custom units
ureg.define('inch_of_mercury = 33.8639 millibar = inHg')  # Define inches of mercury

