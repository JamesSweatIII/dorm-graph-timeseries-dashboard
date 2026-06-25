import re


FALLBACK = object()


def route_query(text, service):
    text_lower = text.lower().strip()
    results = []

    # ── Complex / multi-clause queries → send to LLM ───────────────────────────────
    word_count = len(text_lower.split())
    has_conjunction = bool(re.search(r"\b(?:and|but|or|also|additionally|meanwhile|however)\b", text_lower))
    has_multiple_topics = len(re.findall(r"\b(room\d*|ac\d*|sensor\d+|t\d+|occ\d+)\b", text_lower)) > 1
    if has_conjunction or has_multiple_topics or word_count > 10:
        return [FALLBACK]

    # ── Mutations: add / delete / remove ─────────────────────────────────────────
    mutation = _try_mutation(text, service)
    if mutation:
        return mutation

    # ── Location questions ────────────────────────────────────────────────────────
    if re.search(r"where (?:are|is|can I find)", text_lower):
        name_ac = re.search(r"\bac\s*[\s#]*(\d+)", text_lower)
        name_room = re.search(r"\broom\s*[\s#]*(\d+)", text_lower)
        if name_ac:
            aid = "AC" + name_ac.group(1)
            info = service.get_ac_unit(aid)
            loc = info.get("located_in") if info else None
            return [f"**{aid}** is located in **{loc}**" if loc else f"**{aid}** has no location set."]
        if name_room:
            rid = "Room" + name_room.group(1) if not name_room.group(1).startswith("Room") else name_room.group(1)
            # Redirect to "tell me about room" flow — just do it inline
            room = service.get_room(rid)
            if room:
                return [f"**{room['name']}** ({'Dorm' if room['type'] == 'dorm' else 'Mechanical Room'})"]
            return [f"Room '{rid}' not found."]
        if "ac" in text_lower or "unit" in text_lower:
            acs = service.get_all_ac_units()
            lines = []
            for aid in acs:
                info = service.get_ac_unit(aid)
                loc = info.get("located_in") if info else None
                lines.append(f"**{aid}** is located in **{loc}**" if loc else f"**{aid}** has no location set")
            return lines or ["No AC units found."]
        if "room" in text_lower:
            rooms = service.get_all_rooms()
            return [f"There are {len(rooms)} rooms: **{', '.join(r['id'] for r in rooms)}**."]
        if "sensor" in text_lower:
            sensors = service.get_all_sensors()
            return [f"There are {len(sensors)} sensors."]

    # ── "What rooms have..." / "rooms that have" ─────────────────────────────────
    if re.search(r"(?:what|which)\s+rooms?\s+(?:have|contain|has|contains)", text_lower):
        if "ac" in text_lower or "unit" in text_lower:
            acs = service.get_all_ac_units()
            room_set = set()
            for aid in acs:
                info = service.get_ac_unit(aid)
                for r in (info.get("rooms_served") or []):
                    room_set.add(r)
            if room_set:
                return [f"Rooms served by AC: **{', '.join(sorted(room_set))}**"]
            return ["No rooms are served by AC units."]
        if "sensor" in text_lower:
            sensor_type = "temperature" if "temp" in text_lower else None
            sensor_type = "occupancy" if "occup" in text_lower else sensor_type
            if sensor_type:
                rooms = service.get_rooms_with_sensor_type(sensor_type)
                return [f"Rooms with {sensor_type} sensors: **{', '.join(rooms)}**"]
            rooms = service.search_nodes("Room")
            return [f"There are {len(rooms)} rooms."]

    # ── "rooms with AC" / "rooms that have AC" / "room has AC" ───────────────────
    if re.search(r"rooms?\s+(?:that\s+)?(?:have|has|with|contain)", text_lower):
        if "ac" in text_lower or "unit" in text_lower:
            acs = service.get_all_ac_units()
            room_set = set()
            for aid in acs:
                info = service.get_ac_unit(aid)
                for r in (info.get("rooms_served") or []):
                    room_set.add(r)
            if room_set:
                return [f"Rooms served by AC: **{', '.join(sorted(room_set))}**"]
            return ["No rooms are served by AC units."]

    # ── "without AC" / "no AC" / "don't have AC" ─────────────────────────────────
    if re.search(r"(?:without|no |no\.|not have|don't have|do not have|no ac|no ac)", text_lower):
        if "ac" in text_lower or "unit" in text_lower:
            all_rooms = service.get_all_rooms()
            acs = service.get_all_ac_units()
            rooms_served = set()
            for aid in acs:
                info = service.get_ac_unit(aid)
                for r in (info.get("rooms_served") or []):
                    rooms_served.add(r)
            without = sorted([r["id"] for r in all_rooms if r["id"] not in rooms_served])
            if without:
                return [f"Rooms without AC service: **{', '.join(without)}**"]
            return ["All rooms have AC service."]

    # ── "List all" / "Show all" ──────────────────────────────────────────────────
    list_all = re.search(r"(list|show|get)\s+all", text_lower)
    if list_all and not re.search(r"(?:without|no |not have|don't have|do not have|no\.)", text_lower):
        if "room" in text_lower:
            rooms = service.get_all_rooms()
            dorms = sum(1 for r in rooms if r["type"] == "dorm")
            mech = sum(1 for r in rooms if r["type"] == "mechanical_room")
            return [f"**All Rooms** ({len(rooms)} total — {dorms} dorm, {mech} mechanical)",
                    ", ".join(r["id"] for r in rooms)]
        if "ac" in text_lower or "unit" in text_lower:
            acs = service.get_all_ac_units()
            return [f"**All AC Units** ({len(acs)} total)", ", ".join(acs)]
        if "sensor" in text_lower:
            sensors = service.get_all_sensors()
            temps = sum(1 for s in sensors if s["type"] == "temperature")
            occs = sum(1 for s in sensors if s["type"] == "occupancy")
            return [f"**All Sensors** ({len(sensors)} total — {temps} temperature, {occs} occupancy)",
                    ", ".join(f"{s['id']} ({s['type']})" for s in sensors)]

    # ── Aggregation: averages / readings ────────────────────────────────────────
    avg = re.search(r"average\s+(?:the\s+)?(\w+)", text_lower)
    if avg:
        metric = avg.group(1)
        metric_map = {"temperature": "temperature", "temp": "temperature",
                      "humidity": "humidity", "power": "power_kw",
                      "load": "load_pct"}
        mapped = metric_map.get(metric)
        node = _extract_node_name(text)

        # Handle ranges: "room 1-4", "rooms 1 to 4", "room 1 through 4"
        range_m = re.search(r"rooms?\s*(\d+)\s*(?:to|through|-|–|,)\s*(\d+)", text_lower)
        if range_m and mapped:
            start, end = int(range_m.group(1)), int(range_m.group(2))
            dm = {"power_kw": "Power (kW)", "load_pct": "Load (%)", "temperature": "Temperature", "humidity": "Humidity", "value": "Value"}.get(mapped, mapped)
            lines = []
            for i in range(start, end + 1):
                rid = f"Room{i:02d}"
                result = service.get_aggregate_reading(rid, mapped)
                if "error" not in result:
                    lines.append(f"**{result['node']}** — **{result['average']}** (min: {result['min']}, max: {result['max']})")
            if lines:
                return [f"Average {dm} for rooms {start}–{end}:"] + lines

        if mapped and node:
            result = service.get_aggregate_reading(node, mapped)
            if "error" not in result:
                display_metric = {"power_kw": "Power (kW)", "load_pct": "Load (%)", "temperature": "Temperature", "humidity": "Humidity", "value": "Value"}.get(mapped, mapped.replace("_", " ").title())
                return [f"**{result['node']}** — average {display_metric}: **{result['average']}** (min: {result['min']}, max: {result['max']}, over {result['readings']} readings)"]
        if mapped and not node:
            # "average temperature of all rooms" → needs LLM
            return [FALLBACK]
        if node and not mapped and node:
            # "average of Room01" → figure out metrics
            node_info = service.resolve_node(node)
            if node_info:
                return [FALLBACK]
        if not mapped and not node:
            if "sensor" in text_lower or "per room" in text_lower:
                avg_s = service.get_average_sensors_per_room()
                return [f"Average number of sensors per room: **{avg_s}**"]

    # ── Time series: chart/readings for a specific node ─────────────────────────
    ts = _try_time_series(text_lower, service)
    if ts:
        return ts

    if re.search(r"(how many|count|total number)", text_lower):
        parts = []
        if "room" in text_lower:
            rooms = service.get_all_rooms()
            dorms = sum(1 for r in rooms if r["type"] == "dorm")
            mech = sum(1 for r in rooms if r["type"] == "mechanical_room")
            parts.append(f"{len(rooms)} rooms ({dorms} dorm, {mech} mechanical)")
        if "ac" in text_lower or "unit" in text_lower:
            acs = service.get_all_ac_units()
            parts.append(f"{len(acs)} AC units")
        if "sensor" in text_lower:
            sensors = service.get_all_sensors()
            parts.append(f"{len(sensors)} sensors")
        if parts:
            return [", ".join(parts)]
        rooms = service.get_all_rooms()
        acs = service.get_all_ac_units()
        sensors = service.get_all_sensors()
        return [f"{len(rooms)} rooms, {len(acs)} AC units, {len(sensors)} sensors"]

    # ── "with X but without Y" pattern ─────────────────────────────────────────
    with_without = re.search(
        r"(?:find|get|show|list|rooms?)\s*(.*?)(?:with|that have|having)\s+(\w+(?:\s+\w+)?)"
        r"\s*(?:but|and)\s*(?:without|no|not having)\s+(\w+(?:\s+\w+)?)",
        text_lower
    )
    if with_without:
        has_type = with_without.group(2).strip()
        without_type = with_without.group(3).strip()
        has_sensor = _resolve_sensor_type(has_type)
        without_sensor = _resolve_sensor_type(without_type)
        if has_sensor and without_sensor:
            rooms = service.find_rooms_with(has_sensor_type=has_sensor, without_sensor_type=without_sensor)
        elif has_sensor:
            rooms = service.find_rooms_with(has_sensor_type=has_sensor)
        else:
            rooms = service.find_rooms_with()
        if rooms:
            names = ", ".join(r["id"] for r in rooms)
            return [f"Rooms with {has_type} but without {without_type}: **{names}**"]
        return [f"No rooms found with {has_type} but without {without_type}."]

    # ── "without" / "missing" ──────────────────────────────────────────────────
    without_match = re.search(r"(?:without|no|missing|not have)\s+(\w+(?:\s+\w+)?)", text_lower)
    if without_match:
        sensor_type = _resolve_sensor_type(without_match.group(1).strip())
        if sensor_type:
            rooms = service.get_rooms_without_sensor_type(sensor_type)
            if rooms:
                return [f"Rooms without {sensor_type} sensors: **{', '.join(rooms)}**"]
            return [f"All rooms have {sensor_type} sensors."]
        rooms = service.get_rooms_without_sensors()
        if rooms:
            return [f"Rooms with no sensors at all: **{', '.join(rooms)}**"]
        return ["All rooms have at least one sensor."]

    # ── "with" sensor type ─────────────────────────────────────────────────────
    with_match = re.search(r"(?:with|that have|having)\s+(\w+(?:\s+\w+)?)", text_lower)
    if with_match:
        sensor_type = _resolve_sensor_type(with_match.group(1).strip())
        if sensor_type:
            rooms = service.get_rooms_with_sensor_type(sensor_type)
            if rooms:
                return [f"Rooms with {sensor_type} sensors: **{', '.join(rooms)}**"]
            return [f"No rooms found with {sensor_type} sensors."]

    # ── "more details" / "detail" ──────────────────────────────────────────────
    if re.search(r"(detail|more|full|info|describe)", text_lower):
        return [None]

    # ── "served by" / "serves" ─────────────────────────────────────────────────
    served = re.search(r"(?:served by|serves|connected to)\s+(\w+)", text_lower)
    if served:
        target = served.group(1).upper().strip()
        target_id = "AC" + target if not target.startswith("AC") else target
        all_acs = set(service.get_all_ac_units())
        if target_id in all_acs:
            ac = service.get_ac_unit(target_id)
            rooms = service.get_rooms_served_by(target_id)
            return [f"**{ac['name']}** serves rooms: **{', '.join(rooms) if rooms else 'none'}**"]
        if not re.search(r"\btell\b|\babout\b|\bwhat\b|\bwhich\b", text_lower):
            return [f"AC unit '{target_id}' not found."]

    # ── "located in" ──────────────────────────────────────────────────────────
    loc_in = re.search(r"(?:located in|in room)\s+(\w+)", text_lower)
    if loc_in:
        room_id = loc_in.group(1).upper().strip().replace("room", "Room")
        all_ids = {r["id"].upper() for r in service.get_all_rooms()}
        if room_id not in all_ids:
            # might be a question word like "which" or "what" — skip
            if room_id in {"WHICH", "WHAT"}:
                pass
            else:
                return [f"Room '{room_id}' not found."]
        else:
            ac_id = service.get_ac_located_in(room_id)
            sensors = service.get_monitored_by(room_id)
            parts = []
            if ac_id:
                parts.append(f"AC Unit: **{ac_id}**")
            if sensors:
                parts.append(f"Sensors: **{', '.join(sensors)}**")
            if parts:
                return ["; ".join(parts)]
            return [f"No equipment found in {room_id}."]

    # ── Search by name/number ─────────────────────────────────────────────────
    name_match = re.search(r"\b(room|ac)\s*[\s#]*(\d+)", text_lower)
    if name_match:
        # If text suggests mutation, skip name lookup and let LLM handle
        if re.search(r"\b(connect|link|attach|disconnect|unlink|remove|make\s+\w+\s+connect|add relationship)\b", text_lower):
            return [FALLBACK]
    if name_match:
        entity_type = name_match.group(1)
        entity_id = name_match.group(2).upper().strip()
        if "room" in entity_type:
            entity_id = "Room" + entity_id if not entity_id.startswith("ROOM") else "Room" + entity_id[4:]
            room = service.get_room(entity_id)
            if room:
                return [f"**{room['name']}** ({'Dorm' if room['type'] == 'dorm' else 'Mechanical Room'})"]
            return [f"Room '{entity_id}' not found."]
        elif "ac" in entity_type:
            entity_id = "AC" + entity_id if not entity_id.startswith("AC") else entity_id
            ac = service.get_ac_unit(entity_id)
            if ac:
                loc = ac.get("located_in")
                is_location_q = re.search(r"\b(where\b|located|inside|within)", text_lower) or \
                                re.search(r"\bin\b", text_lower) and re.search(r"\broom\b", text_lower)
                is_serve_q = re.search(r"\b(serve|service|cool|cools)\b", text_lower)
                if loc and is_location_q and not is_serve_q:
                    return [f"**{ac['name']}** is located in **{loc}**"]
                rooms = service.get_rooms_served_by(entity_id)
                return [f"**{ac['name']}** serves: **{', '.join(rooms) if rooms else 'none'}**"]
            return [f"AC unit '{entity_id}' not found."]
        elif "sensor" in entity_type:
            sensor = service.get_sensor(entity_id)
            if sensor:
                return [f"**{sensor['name']}** ({sensor['type']} sensor)"]
            return [f"Sensor '{entity_id}' not found."]

    # ── Generic search fallback → tell caller to try LLM ──────────────────────
    return [FALLBACK]


def _try_time_series(text, service):
    ts_keywords = r"(temperature|temp|humidity|power|load|reading|chart|graph|data|timeseries|time series|show me)"
    m = re.search(ts_keywords, text)
    if not m:
        return None

    node_name = _extract_node_name(text)
    if not node_name:
        return [{"text": "Which node would you like to see time series data for?"}]

    ts = service.get_time_series_for_node(node_name)
    if not ts:
        return [f"No time series data available for **{node_name}**."]

    data = ts["data"]
    value_cols = [c for c in ts.get("columns", []) if c not in ("time", "timestamp")]
    parts = [f"### Time Series — {node_name} ({ts['label']})"]

    # Build a data table
    val_summaries = []
    for col in value_cols:
        vals = [row[col] for row in data if col in row]
        if vals:
            avg = round(sum(vals) / len(vals), 1)
            lo, hi = min(vals), max(vals)
            val_summaries.append(f"{col}: avg {avg}, min {lo}, max {hi}")
    if val_summaries:
        parts.append("_" + "; ".join(val_summaries) + "_")

    col_widths = {}
    for col in ts["columns"]:
        items = [str(row.get(col, "")) for row in data[:24]]
        col_widths[col] = max(len(col), max(len(i) for i in items))
    header = " | ".join(c.ljust(col_widths[c]) for c in ts["columns"])
    sep = " | ".join("-" * col_widths[c] for c in ts["columns"])
    rows = [" | ".join(str(row.get(c, "")).ljust(col_widths[c]) for c in ts["columns"]) for row in data[:24]]
    parts.append(f"```\n{header}\n{sep}\n" + "\n".join(rows) + "\n```")

    parts.append({"chart": ts})
    return parts


def _extract_node_name(text):
    patterns = [
        r"(?:for|of|from|in|on)\s+(room\s*\d+|ac\s*\d+|t\d+|occ\d+)",
        r"\b(room\s*\d+|ac\s*\d+|t\d+|occ\d+)\b"
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            raw = re.sub(r"\s+", "", m.group(1))
            raw = raw[0].upper() + raw[1:] if raw[0].islower() else raw
            m2 = re.match(r"(Room|AC|T|Occ)(\d+)$", raw, re.IGNORECASE)
            if m2:
                prefix = m2.group(1)
                num = int(m2.group(2))
                if prefix.upper() == "ROOM":
                    return f"Room{num:02d}"
                elif prefix.upper() == "AC":
                    return f"AC{num}"
                else:
                    return f"{prefix.upper()}{num}"
            return raw
    return None


def _resolve_sensor_type(word):
    w = word.lower().strip()
    if w in ("temperature", "temp", "temperature sensor", "temp sensor"):
        return "temperature"
    if w in ("occupancy", "occ", "occupancy sensor", "occ sensor"):
        return "occupancy"
    return None


def _try_mutation(text, service):
    # ── Remove relationship (check BEFORE node delete) ──────────────────────────
    m = re.search(r"(?:disconnect|unlink|remove)\s+(\w+)\s+(?:from|and)\s+(\w+)", text, re.IGNORECASE)
    if m:
        a, b = m.group(1).strip(), m.group(2).strip()
        result = service.delete_relationship(a, "SERVICES", b)
        if result["ok"]:
            return [result["msg"]]
        # If no SERVICES relationship, try removing node instead — fall through

    # ── Delete / Remove node ──────────────────────────────────────────────────
    m = re.search(r"(?:delete|remove|destroy)\s+(?:the\s+)?(?:room\s+|ac\s+)?[\"']?(room\d+|ac\d+|t\d+|occ\d+|sensor\d+)[\"']?", text, re.IGNORECASE)
    if m:
        raw_name = m.group(1)
        result = service.delete_node(raw_name)
        return [result["msg"]]

    # ── Add / Create ──────────────────────────────────────────────────────────
    m = re.search(
        r"(?:add|create|new)\s+(?:a\s+|an\s+)?(room|ac(?:\s+unit)?|sensor)"
        r"\s*(?:called\s+|named\s+|\:\s*)?[\"']?(\w+)?[\"']?",
        text, re.IGNORECASE
    )
    if m:
        kind = m.group(1).strip()
        custom_id = m.group(2).strip() if m.group(2) else None
        kind = kind.lower()

        if custom_id and "ac" in kind:
            custom_id = custom_id.upper()
            if not custom_id.startswith("AC"):
                custom_id = "AC" + custom_id

        if "room" in kind:
            room_type = "dorm"
            if "mechanical" in text:
                room_type = "mechanical_room"
            result = service.add_room(custom_id, room_type)
            return [result["msg"]]

        if "ac" in kind:
            if custom_id and not custom_id.startswith("AC"):
                custom_id = "AC" + custom_id
            result = service.add_ac_unit(custom_id)
            return [result["msg"]]

        if "sensor" in kind:
            sensor_type = "temperature"
            if "occupancy" in text:
                sensor_type = "occupancy"
            result = service.add_sensor(custom_id, sensor_type)
            return [result["msg"]]

    # ── Add relationship ──────────────────────────────────────────────────────
    m = re.search(
        r"(?:connect|link|attach|add relationship)\s+(\w+)\s+(?:to|with)\s+(\w+)"
        r"(?:\s+as\s+(\w+))?",
        text, re.IGNORECASE
    )
    if m:
        a, b = m.group(1).upper(), m.group(2).upper()
        rel = (m.group(3) or "SERVICES").upper()
        # Normalize IDs: AC2 → AC2, room5 → ROOM05
        if a.upper().startswith("ROOM"):
            num = a[4:]
            a = "Room" + f"{int(num):02d}" if num.isdigit() else a
        if b.upper().startswith("ROOM"):
            num = b[4:]
            b = "Room" + f"{int(num):02d}" if num.isdigit() else b
        result = service.add_relationship(a, rel, b)
        if result["ok"]:
            return [f"Connected **{a}** → **{rel}** → **{b}**."]
        return [result["msg"]]

    return None
