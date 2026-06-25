import re

FALLBACK = object()


def route_query(text, service):
    text_lower = text.lower().strip()

    # ── Mutations: add / delete / remove ─────────────────────────────────────────
    mutation = _try_mutation(text, service)
    if mutation:
        return mutation

    # Everything else → LLM agent
    return [FALLBACK]


def _try_mutation(text, service):
    # ── Remove relationship (check BEFORE node delete) ──────────────────────────
    m = re.search(r"(?:disconnect|unlink|remove)\s+(\w+)\s+(?:from|and)\s+(\w+)", text, re.IGNORECASE)
    if m:
        a, b = m.group(1).strip(), m.group(2).strip()
        result = service.delete_relationship(a, "SERVICES", b)
        if result["ok"]:
            return [result["msg"]]

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
