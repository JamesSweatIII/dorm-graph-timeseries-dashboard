from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from utils import ROOMS, PROFILES, ROOM_PROFILES, SUNNY_ROOMS, enrich_timestamp

# --- FUNCTIONS ---

def generate_occupancy(room, start, end, interval):
    """
    Generate simulated occupancy data for a room with more natural variation.

    Args:
        room (str): The room ID.
        start (datetime): Start time for the simulation.
        end (datetime): End time for the simulation.
        interval (timedelta): Time interval between data points.

    Returns:
        pd.DataFrame: A DataFrame containing simulated occupancy data.
    """
    timestamps = []
    profile_type = ROOM_PROFILES[room]  # Get the room's profile type (e.g., night_student)
    exposure = "sunny" if room in SUNNY_ROOMS else "shaded"  # Determine if the room is sunny or shaded
    profile = PROFILES[profile_type]  # Get the occupancy profile for the room type
    t = start

    last_occupied = 0
    streak = 0  # How long the current state has lasted

    while t < end:
        # Determine if we're in a likely occupied period
        in_profile = any(start_h <= t.hour < end_h for start_h, end_h in profile)
        # Add inertia: more likely to stay in the same state as previous interval
        if in_profile:
            # During profile hours, more likely to stay occupied if already occupied
            if last_occupied:
                prob = 0.97  # Stay occupied
            else:
                prob = 0.85  # Become occupied
        else:
            # Outside profile hours, more likely to stay vacant if already vacant
            if last_occupied:
                prob = 0.15  # Become vacant
            else:
                prob = 0.95  # Stay vacant

        occupied = np.random.choice([1, 0], p=[prob, 1 - prob])
        last_occupied = occupied

        # Add timestamp and metadata for downstream analytics
        meta = enrich_timestamp(t)  # Generate additional time-based metadata (e.g., day of week, hour)
        timestamps.append({
            "timestamp": t,  # The current timestamp for this data point
            "occupancy": occupied,  # 1 if occupied, 0 if vacant
            "occupancy_status": "Occupied" if occupied else "Vacant",  # Human-readable status
            "room_id": room,  # Room identifier
            "room_profile": profile_type,  # Occupancy profile type (e.g., night_student)
            "exposure": exposure,  # Whether the room is sunny or shaded
            **meta  # Unpack additional time-based metadata (e.g., day, hour, etc.)
        })
        t += interval  # Move to the next time interval

    return pd.DataFrame(timestamps)

def generate_temperature(room, start, end, interval):
    """
    Generate simulated temperature data for a room.

    Args:
        room (str): The room ID.
        start (datetime): Start time for the simulation.
        end (datetime): End time for the simulation.
        interval (timedelta): Time interval between data points.

    Returns:
        pd.DataFrame: A DataFrame containing simulated temperature data.
    """
    timestamps = []
    t = start
    exposure = "sunny" if room in SUNNY_ROOMS else "shaded"
    profile_type = ROOM_PROFILES[room]
    base_temp_nominal = 23 if exposure == "sunny" else 20  # Sunny rooms are generally warmer
    amplitude = 3.5  # Controls daily temperature swing; reduced for realism
    current_day = None
    day_base_temp = None

    AC_THRESHOLD = 24.5  # AC turns on at this temperature for comfort
    COOLING_EFFECT = 0.7  # How much the AC cools per interval
    ac_cooldown = 0       # Tracks how long the AC stays on after activation

    last_temp = None      # Used for inertia to make temperature changes gradual

    while t < end:
        # Update daily base temperature at the start of a new day
        if t.date() != current_day:
            current_day = t.date()
            # Add seasonal effect (warmer in summer, cooler in winter) and daily randomness
            month = t.month
            seasonal = 1.5 * np.sin((month - 1) / 12 * 2 * np.pi)
            day_base_temp = base_temp_nominal + seasonal + np.random.normal(0, 1.2)

        # Simulate daily temperature cycle using a sine wave
        minutes = t.hour * 60 + t.minute
        temp = day_base_temp + amplitude * np.sin(2 * np.pi * minutes / 1440)

        # Add inertia: blend with previous value for smoothness, plus a little noise
        if last_temp is not None:
            temp = 0.7 * temp + 0.3 * last_temp + np.random.normal(0, 0.12)
        else:
            temp += np.random.normal(0, 0.25)
        last_temp = temp

        # AC logic: if temp is high or AC is already on, cool and keep AC on for a few intervals
        ac_status = "OFF"
        if temp >= AC_THRESHOLD or ac_cooldown > 0:
            temp -= COOLING_EFFECT
            ac_status = "ON"
            ac_cooldown = 2  # AC stays on for 2 intervals after activation
        if ac_cooldown > 0:
            ac_cooldown -= 1

        temp = round(temp, 2)

        # Categorize temperature for downstream analytics
        category = "Hot" if temp >= 24 else "Cold" if temp <= 18 else "Comfortable"

        # Add timestamp and metadata for downstream analytics
        meta = enrich_timestamp(t)
        timestamps.append({
            "timestamp": t,
            "temperature_celsius": temp,
            "temperature_status": category,
            "ac_status": ac_status,
            "room_id": room,
            "room_profile": profile_type,
            "exposure": exposure,
            "daily_base_temp": round(day_base_temp, 2),
            **meta
        })
        t += interval

    return pd.DataFrame(timestamps)

def get_sensor_data(start_date, days, interval_minutes):
    """
    Generate simulated sensor data for multiple rooms over a specified time period.

    Args:
        start_date (str): The start date for the simulation (YYYY-MM-DD).
        days (int): Number of days to simulate.
        interval_minutes (int): Time interval between data points in minutes.

    Returns:
        dict: A dictionary containing occupancy and temperature data for each room.
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")  # Parse the start date
    end = start + timedelta(days=days)  # Calculate the end date
    interval = timedelta(minutes=interval_minutes)  # Define the time interval

    data = {}
    for room in ROOMS:
        # Generate occupancy and temperature data for each room
        occ_df = generate_occupancy(room, start, end, interval)
        temp_df = generate_temperature(room, start, end, interval)
        data[room] = {"occupancy": occ_df, "temperature": temp_df}

    return data

def convert_timestamps(data):
    """
    Convert all Timestamp objects in the data to ISO 8601 strings.
    This is useful for exporting data to JSON or other formats that require string timestamps.
    """
    for record in data:
        for key, value in record.items():
            if isinstance(value, pd.Timestamp):  # Check if the value is a pandas.Timestamp
                record[key] = value.isoformat()  # Convert to ISO 8601 string
    return data