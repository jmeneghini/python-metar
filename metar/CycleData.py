"""This module defines the AllCyclesData class, which is used to store and manipulate 24-hour weather data.
"""
from metar.Metar import Metar, QUANTITY_ATTRS
from metar.Units import ureg
from metar.Datatypes import metar_types
from metar.Station import stations
from shapely.geometry import Point
from numpy import nan
import geopandas as gpd
import aiohttp
import asyncio
import pandas as pd
import pint_pandas
import pickle
import time
from multiprocessing import Pool, cpu_count
from functools import partial


# Helper function to split a list of strings into sublists, using empty strings as delimiters
def _split_list_on_empty_string(lst):
    result = []
    current_sublist = []
    for item in lst:
        if item == "":
            if current_sublist:  # Avoid adding empty sub-lists
                result.append(current_sublist)
                current_sublist = []
        else:
            current_sublist.append(item)
    if current_sublist:  # Add the last sublist if it's not empty
        result.append(current_sublist)
    return result

class CycleData(object):
    """An object representing a 24-hour period of weather data."""
    def __init__(self, dataframe, start_time, end_time, tz):
        self.dataframe = dataframe
        self.start_time = start_time
        self.end_time = end_time
        self.tz = tz
        
    def __repr__(self):
        # Provides a detailed, unambiguous representation
        return (f'AllCyclesData(dataframe={self.dataframe.__repr__()}, '
                f'start_time={repr(self.start_time)}, '
                f'end_time={repr(self.end_time)}, '
                f'tz={repr(self.tz)})')

    def __str__(self):
        # Provides a readable summary of the object
        df_summary = f'Data points: {len(self.dataframe)}, ' \
                     f'Columns: {list(self.dataframe.columns)}'
        return (f'Weather Data from {self.start_time} to {self.end_time} in {self.tz} timezone.\n'
                f'{df_summary}')
        
    def save_instance(self, filename):
        with open(filename, "wb") as file:
            pickle.dump(self, file)
            
        
    @classmethod
    def load_instance(cls, filename):
        with open(filename, "rb") as file:
            instance = pickle.load(file)
        return instance
        
    @classmethod
    async def create_instance(cls, start_time = pd.Timestamp.now(tz = "UTC") - pd.Timedelta(days=1),
                 end_time = pd.Timestamp.now(tz = "UTC"), tz = "UTC"):
        
        start_time, end_time = cls._handle_time_input(start_time, end_time)
        start_cycle, end_cycle = cls._get_cycle_range(start_time, end_time)
        
        
        print(f"Fetching cycles {start_cycle.hour} to {end_cycle.hour}...")
        cycles_txt_list = await cls._fetch_cycle_txt_list(start_cycle, end_cycle)
        print("Cycle data has been fetched!")
        
        cycles_txt_series = cls._process_cycles_txt_list_to_series(cycles_txt_list)
        print(f"Processing {len(cycles_txt_series)} METAR reports...")
        
        metar_series = cls._extract_metar_reports(cycles_txt_series)
        decoded_metar_df = cls._decode_metar_series(metar_series)
        decoded_metar_df = cls._convert_units(decoded_metar_df)
        decoded_metar_df = cls._set_timezone_and_sort_dataframe(decoded_metar_df, start_time, end_time, tz)
        decoded_metar_df = cls._add_position_column(decoded_metar_df)
        print("Data has been processed!")
        
        return cls(decoded_metar_df, start_time, end_time, tz)
    
    @staticmethod
    def _handle_time_input(start_time, end_time):
        # ensure that start_time and end_time are in the same timezone, and that end_time is after start_time
        start_time = start_time.tz_convert(tz = "UTC")
        end_time = end_time.tz_convert(tz = "UTC")
        if start_time > end_time:
            raise ValueError("start_time must be before end_time")
        # ensure that start_time and end_time are not in the future
        if start_time > pd.Timestamp.now(tz = "UTC"):
            raise ValueError("start_time must not be in the future")
        if end_time > pd.Timestamp.now(tz = "UTC"):
            raise ValueError("end_time must not be in the future")
        # ensure that start_time and end_time are not more than 24 hours apart. Add a second since end_time is calculated after start_time
        if end_time - start_time > pd.Timedelta(days=1, seconds=1):
            raise ValueError("start_time and end_time must not be more than 24 hours apart")
        # ensure that start_time is not more than 24 hours before now
        if pd.Timestamp.now(tz = "UTC") - start_time > pd.Timedelta(days=1, seconds=1):
            raise ValueError("start_time must not be more than 24 hours before now")
        return start_time, end_time

    @staticmethod
    def _get_cycle_range(start_time, end_time):
        """Get the range of cycles that contain the given time range."""
        start_cycle = start_time.replace(minute=0, second=0, microsecond=0)
        end_cycle = end_time.replace(minute=0, second=0, microsecond=0)
        if start_time.minute >= 45:
            start_cycle += pd.Timedelta(hours=1)
        if end_time.minute >= 45:
            end_cycle += pd.Timedelta(hours=1)
        # handle the case where the start and end times are in the same hour (when 24 hrs), or when the start_time cycle == current cycle
        if start_cycle.hour == end_cycle.hour or start_cycle.hour == CycleData._get_current_cycle().hour:
            end_cycle += pd.Timedelta(hours=1)
        return start_cycle, end_cycle
    
    @staticmethod
    def _get_current_cycle():
        """Get the current cycle."""
        cycle = pd.Timestamp.now(tz = "UTC").replace(minute=0, second=0, microsecond=0)
        if cycle.minute >= 45:
            cycle += pd.Timedelta(hours=1)
        return cycle
        
    @staticmethod
    async def _fetch_cycle_data(session, cycle):
        """Asynchronously fetch a cycle of METAR data."""
        url = f"https://tgftp.nws.noaa.gov/data/observations/metar/cycles/{cycle:02}Z.TXT"
        async with session.get(url) as response:
            return await response.text(errors="ignore")

    @staticmethod
    async def _fetch_cycle_txt_list(start_cycle, end_cycle):
        """Fetch METAR cycles data asynchronously."""
        async with aiohttp.ClientSession() as session:
            tasks = [CycleData._fetch_cycle_data(session, cycle.hour) for cycle in pd.date_range(start_cycle, end_cycle, freq="h")]
            cycles_txt_list = await asyncio.gather(*tasks)
        return cycles_txt_list
    
    @staticmethod
    def _metar_to_value_dict(metar_encoded_str):
        """Convert a Metar object to a dictionary of values."""
        metar = Metar(metar_encoded_str, strict=False)
        dict = metar.__dict__.copy()
        for key, value in dict.items():
            if type(value) in metar_types:
                dict[key] = value.value()
        return dict
    
    @staticmethod
    def _process_cycles_txt_list_to_series(cycles_txt_list):
        cycles_txt_series = pd.Series(cycles_txt_list).str.split("\n")
        cycles_txt_series = cycles_txt_series.apply(_split_list_on_empty_string).explode().reset_index(drop=True)
        return cycles_txt_series
    
    @staticmethod
    def _extract_metar_reports(cycles_txt_series):
        return cycles_txt_series.str[1].str.strip().drop_duplicates().reset_index(drop=True)
    
    @staticmethod
    def _split_series(series, n_chunks):
        """Split a Pandas Series into smaller Series chunks, handling uneven lengths."""
        total_len = len(series)
        # Ensure we do not exceed the number of chunks than the series length
        n_chunks = min(n_chunks, total_len)
        # Calculate the base chunk size and how many elements will be in the larger chunks
        base_chunk_size = total_len // n_chunks
        larger_chunks_count = total_len % n_chunks
        
        chunks = []
        start_idx = 0
        for i in range(n_chunks):
            # Determine the size of this chunk
            chunk_size = base_chunk_size + (1 if i < larger_chunks_count else 0)
            end_idx = start_idx + chunk_size
            # Create the chunk and add it to the list
            chunks.append(series.iloc[start_idx:end_idx])
            # Update the start index for the next chunk
            start_idx = end_idx

        return chunks
    @staticmethod
    def _apply_function_to_chunk(chunk, f):
        """Apply a function to each element in a chunk of a Pandas Series."""
        # Use Series.apply to apply `func` to the chunk
        return chunk.apply(f)

    @staticmethod
    def _parallel_process_series(series, f, n_chunks=cpu_count()):
        """Process a Pandas Series in parallel by splitting it into chunks.
        Hopefully this will be faster than .apply() for large Series."""
        series_chunks = CycleData._split_series(series, n_chunks)
        worker_with_func = partial(CycleData._apply_function_to_chunk, f=f)
        
        with Pool() as pool:
            processed_chunks = pool.map(worker_with_func, series_chunks)
        
        # Concatenate the processed chunks back into a single Series
        return pd.concat(processed_chunks)
        
    @staticmethod
    def _decode_metar_series(metar_series):
        decoded_metar_series = CycleData._parallel_process_series(metar_series, CycleData._metar_to_value_dict)
        decoded_metar_df = pd.DataFrame(decoded_metar_series.tolist())
        return decoded_metar_df # consider removing columns with all NaNs (check if this ever happens)
    
    @staticmethod
    def _convert_units(decoded_metar_df):
        for column in QUANTITY_ATTRS:
             # mask for non-NaN values, which will always be Quantity objects
            quantity_mask = ~decoded_metar_df[column].isna()
            if quantity_mask.any():
                unit = decoded_metar_df[column][quantity_mask].apply(lambda x: x.units).value_counts().idxmax()
                decoded_metar_df.loc[quantity_mask, column] = decoded_metar_df.loc[quantity_mask, column].apply(lambda x: x.to(unit).magnitude)
                decoded_metar_df[column] = pint_pandas.PintArray(decoded_metar_df[column], dtype=unit)
        return decoded_metar_df
    
    @staticmethod
    def _set_timezone_and_sort_dataframe(decoded_metar_df, start_time, end_time, tz):
        # convert to tz if not UTC
        if tz.upper() != "UTC" and tz.upper() != "UNIVERSAL":
            decoded_metar_df["time"] = decoded_metar_df["time"].dt.tz_convert(tz)
        # get all the rows that are within the time range
        time_mask = (decoded_metar_df["time"] >= start_time) & (decoded_metar_df["time"] <= end_time)
        decoded_metar_df = decoded_metar_df[time_mask]
        # sort by time
        decoded_metar_df = decoded_metar_df.sort_values("time").reset_index(drop=True)
        return decoded_metar_df
    
    @staticmethod
    def _get_position(station_id):
        try:
            return stations[station_id].position
        except KeyError:
            return Point(nan, nan)
    
    @staticmethod
    def _add_position_column(decoded_metar_df):
        position_series = decoded_metar_df["station_id"].apply(CycleData._get_position)
        decoded_metar_df = gpd.GeoDataFrame(decoded_metar_df, geometry=position_series)
        decoded_metar_df.crs = "EPSG:4326"
        return decoded_metar_df
    
    
    
    
    
    
    
    
    
    
        
    