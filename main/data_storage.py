import os
import json
from llama_index.core.schema import Document
from datetime import datetime
from time_series_generator import convert_timestamps

# --- FUNCTIONS ---

def save_sensor_data_to_mongo(sensor_data, collection):
    """
    Save sensor data to MongoDB.

    Args:
        sensor_data (list): List of sensor data documents.
        collection (pymongo.collection.Collection): MongoDB collection to save the data.
    """
    # Validate input
    if not isinstance(sensor_data, list) or len(sensor_data) == 0:
        raise ValueError("sensor_data must be a non-empty list of dictionaries.")
    if not all(isinstance(doc, dict) for doc in sensor_data):
        raise ValueError("All items in sensor_data must be dictionaries.")
    # Insert all documents into MongoDB
    collection.insert_many(sensor_data)

def json_serial(obj):
    """
    Helper to serialize datetime objects for JSON dumping.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def fetch_mongo_documents(collection):
    """
    Fetch all documents from MongoDB and wrap them as LlamaIndex Document objects.
    """
    docs = []
    for doc in collection.find({}):
        room_id = doc["room_id"]
        data_type = doc["type"]
        data = doc["data"]  # list of records, possibly with datetimes

        # Serialize data to JSON with datetime support
        text = (
            f"Room ID: {room_id}\n"
            f"Type: {data_type}\n"
            f"Data:\n{json.dumps(data, default=json_serial, indent=2)}"
        )
        # Wrap as LlamaIndex Document
        docs.append(Document(text=text, metadata={"room_id": room_id, "type": data_type}))
    return docs

def combine_documents_by_room(mongo_docs):
    """
    Combine temperature readings from MongoDB by room and by day,
    creating a LlamaIndex Document for each room-day combination.
    """
    import pandas as pd
    from llama_index.core.schema import Document

    # Gather all temperature readings from all docs
    all_readings = []
    for doc in mongo_docs:
        if isinstance(doc, dict) and doc.get("type") == "temperature" and isinstance(doc.get("data"), list):
            for reading in doc["data"]:
                if "room_id" not in reading:
                    reading["room_id"] = doc.get("room_id")
                all_readings.append(reading)

    # Group readings by room_id
    rooms = {}
    for reading in all_readings:
        room_id = reading.get("room_id")
        if not room_id:
            continue
        rooms.setdefault(room_id, []).append(reading)

    room_documents = []
    for room_id, readings in rooms.items():
        df = pd.DataFrame(readings)
        if 'temperature_celsius' not in df.columns or df.empty:
            continue

        # Group by date for daily summaries
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        for day, day_df in df.groupby('date'):
            # Calculate daily stats
            avg_temp = day_df['temperature_celsius'].mean()
            min_temp = day_df['temperature_celsius'].min()
            max_temp = day_df['temperature_celsius'].max()
            profile = day_df['room_profile'].iloc[0] if 'room_profile' in day_df.columns else "Unknown"
            exposure = day_df['exposure'].iloc[0] if 'exposure' in day_df.columns else "Unknown"
            daily_base_temp = day_df['daily_base_temp'].iloc[0] if 'daily_base_temp' in day_df.columns else "Unknown"

            # Build document text
            room_text = f"Room ID: {room_id}\nDate: {day}\n"
            room_text += f"Room profile: {profile}\n"
            room_text += f"Exposure: {exposure}\n"
            room_text += f"Daily base temperature: {daily_base_temp}\n\n"
            room_text += "TEMPERATURE DATA:\n"
            room_text += f"Average temperature: {avg_temp:.2f}°C\n"
            room_text += f"Minimum temperature: {min_temp:.2f}°C\n"
            room_text += f"Maximum temperature: {max_temp:.2f}°C\n\n"
            room_text += "Sample temperature readings:\n"

            # Sample up to 10 readings evenly distributed
            sample_indices = list(range(0, len(day_df), max(1, len(day_df)//10)))[:10]
            for idx in sample_indices:
                row = day_df.iloc[idx]
                timestamp = row.get('timestamp', 'Unknown time')
                temp = row.get('temperature_celsius', 'Unknown')
                status = row.get('temperature_status', '')
                ac = row.get('ac_status', '')
                room_text += f"Time: {timestamp}, Temp: {temp:.2f}°C"
                if status:
                    room_text += f", Status: {status}"
                if ac:
                    room_text += f", AC: {ac}"
                room_text += "\n"

            # Create a Document for each room-day
            doc = Document(
                text=room_text,
                metadata={"room_id": room_id, "type": "sensor", "date": str(day)}
            )
            room_documents.append(doc)
    return room_documents

def prepare_sensor_data_for_mongo(sensor_data):
    """
    Prepare sensor data for MongoDB insertion.
    Converts DataFrames to lists of dicts for each room and sensor type.
    """
    prepared = []
    for room_id, room_data in sensor_data.items():
        # Occupancy data
        if "occupancy" in room_data:
            occ_records = room_data["occupancy"].to_dict(orient="records")
            prepared.append({
                "room_id": room_id,
                "type": "occupancy",
                "data": occ_records
            })
        # Temperature data
        if "temperature" in room_data:
            temp_records = room_data["temperature"].to_dict(orient="records")
            prepared.append({
                "room_id": room_id,
                "type": "temperature",
                "data": temp_records
            })
    return prepared

# --- Helper: Check if sensor data exists in MongoDB ---
def has_valid_sensor_data(collection):
    """
    Check if there is any sensor data in the MongoDB collection.
    Returns True if at least one document exists.
    """
    return collection.count_documents({}) > 0
