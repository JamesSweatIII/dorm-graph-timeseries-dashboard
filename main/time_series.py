import random
import pandas as pd
from datetime import datetime, timedelta

random.seed(42)

_generated = {}

def generate_time_series(node_id, node_type, subtype=None):
    if node_id in _generated:
        return _generated[node_id]

    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    times = [now - timedelta(hours=i) for i in range(24)]
    times.reverse()

    if node_type == "Room":
        if subtype == "mechanical_room":
            base_temp = random.uniform(18, 22)
            base_humidity = random.uniform(35, 50)
        else:
            base_temp = random.uniform(22, 28)
            base_humidity = random.uniform(40, 60)
        data = []
        for i, t in enumerate(times):
            hour_factor = 1 + 0.15 * (i / 24)
            noise = random.uniform(-1.5, 1.5)
            data.append({
                "time": t.strftime("%H:%M"), "temperature": round(base_temp + noise + 2 * (i / 24), 1),
                "humidity": round(base_humidity + random.uniform(-5, 5) + 5 * (i / 24), 1),
                "timestamp": t.isoformat()
            })
        _generated[node_id] = {
            "type": "Room", "label": "Temperature & Humidity",
            "columns": ["time", "temperature", "humidity"],
            "data": data
        }

    elif node_type == "ACUnit":
        data = []
        for i, t in enumerate(times):
            load = random.uniform(40, 95) + random.uniform(-10, 10)
            power = round(500 + load * 15 + random.uniform(-100, 100), 0)
            data.append({
                "time": t.strftime("%H:%M"), "power_kw": power,
                "load_pct": round(min(100, max(0, load)), 1),
                "timestamp": t.isoformat()
            })
        _generated[node_id] = {
            "type": "ACUnit", "label": "Power & Load",
            "columns": ["time", "power_kw", "load_pct"],
            "data": data
        }

    elif node_type == "Sensor":
        if subtype == "temperature":
            base = random.uniform(22, 27)
            data = []
            for i, t in enumerate(times):
                v = round(base + random.uniform(-2, 2) + 3 * (i / 24), 1)
                data.append({"time": t.strftime("%H:%M"), "value": v, "timestamp": t.isoformat()})
            _generated[node_id] = {
                "type": "Sensor", "label": "Temperature Reading (°C)",
                "columns": ["time", "value"],
                "data": data
            }
        else:
            base = random.uniform(0, 30)
            data = []
            for i, t in enumerate(times):
                v = round(min(100, max(0, base + random.uniform(-10, 10) + 20 * (i / 24))), 1)
                data.append({"time": t.strftime("%H:%M"), "value": v, "timestamp": t.isoformat()})
            _generated[node_id] = {
                "type": "Sensor", "label": "Occupancy (%)",
                "columns": ["time", "value"],
                "data": data
            }

    else:
        _generated[node_id] = {
            "type": "Unknown", "label": "Readings",
            "columns": ["time", "value"],
            "data": [{"time": t.strftime("%H:%M"), "value": round(random.uniform(0, 100), 1)} for t in times]
        }

    return _generated[node_id]


def generate_for_all_nodes(nodes_dict):
    for nid, data in nodes_dict.items():
        props = data["props"]
        labels = data["labels"]
        if "Room" in labels:
            generate_time_series(nid, "Room", props.get("room_type"))
        elif "ACUnit" in labels:
            generate_time_series(nid, "ACUnit")
        elif "Sensor" in labels:
            generate_time_series(nid, "Sensor", props.get("type", "").lower())
    return _generated
