import json
import os
import sys
from openai import OpenAI


SYSTEM_PROMPT = """You are a helpful dormitory management assistant. You have access to a Neo4j knowledge graph containing rooms, AC units, and sensors with their relationships.

Available node types:
- Room: has room_id (e.g. "Room01"), room_type ("dorm" or "mechanical_room")
- ACUnit: has ac_id (e.g. "AC1")
- Sensor: has sensor_id (e.g. "T01", "Occ_Room01"), type ("temperature" or "occupancy")

Relationships:
- (ACUnit)-[:SERVICES]->(Room) — AC unit cools a room
- (ACUnit)-[:LOCATED_IN]->(Room) — AC unit is physically located in a room
- (Room)-[:HAS_SENSOR]->(Sensor) — room has a sensor
- (Sensor)-[:MONITORS]->(ACUnit) — sensor monitors an AC unit

Always call the appropriate function to answer the user's question. If you need to get details first before answering, make multiple function calls. For chart data, call get_time_series_for_node and present the data clearly, mentioning what metrics are available."""


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_room",
            "description": "Get details about a room by its room_id (e.g. Room01, Room07)",
            "parameters": {"type": "object", "properties": {
                "room_id": {"type": "string", "description": "Room ID like Room01"}
            }, "required": ["room_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_ac_unit",
            "description": "Get details about an AC unit by its ac_id (e.g. AC1, AC2)",
            "parameters": {"type": "object", "properties": {
                "ac_id": {"type": "string", "description": "AC unit ID like AC1"}
            }, "required": ["ac_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sensor",
            "description": "Get details about a sensor by its sensor_id (e.g. T01, Occ_Room01)",
            "parameters": {"type": "object", "properties": {
                "sensor_id": {"type": "string", "description": "Sensor ID"}
            }, "required": ["sensor_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_nodes",
            "description": "Search for any node by text across all properties",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "Search text"}
            }, "required": ["query"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_rooms_with_sensor_type",
            "description": "Find rooms that have a specific type of sensor",
            "parameters": {"type": "object", "properties": {
                "sensor_type": {"type": "string", "enum": ["temperature", "occupancy"]}
            }, "required": ["sensor_type"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_rooms_without_sensor_type",
            "description": "Find rooms that do NOT have a specific type of sensor",
            "parameters": {"type": "object", "properties": {
                "sensor_type": {"type": "string", "enum": ["temperature", "occupancy"]}
            }, "required": ["sensor_type"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_rooms_without_sensors",
            "description": "Find rooms that have no sensors at all",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_rooms_served_by",
            "description": "Find all rooms served by a specific AC unit",
            "parameters": {"type": "object", "properties": {
                "ac_id": {"type": "string", "description": "AC unit ID like AC1"}
            }, "required": ["ac_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_rooms",
            "description": "Get a list of all rooms with their types and counts",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_ac_units",
            "description": "Get a list of all AC units",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_sensors",
            "description": "Get a list of all sensors with their types",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_average_sensors_per_room",
            "description": "Calculate the average number of sensors per room",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_ac_located_in",
            "description": "Find which AC unit is located in a specific room",
            "parameters": {"type": "object", "properties": {
                "room_id": {"type": "string", "description": "Room ID like Room07"}
            }, "required": ["room_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_monitored_by",
            "description": "Find which sensors monitor a specific room",
            "parameters": {"type": "object", "properties": {
                "room_id": {"type": "string", "description": "Room ID like Room01"}
            }, "required": ["room_id"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_time_series_for_node",
            "description": "Get 24-hour time series readings for a node. Rooms have temperature & humidity. AC units have power_kw & load_pct. Sensors have value (temperature C or occupancy %).",
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string", "description": "Node display name like Room01, AC1, T01, Occ_Room01"}
            }, "required": ["name"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_room",
            "description": "Add a new room to the graph. If no room_id given, auto-increment is used.",
            "parameters": {"type": "object", "properties": {
                "room_id": {"type": "string", "description": "Optional custom room ID like Room09"},
                "room_type": {"type": "string", "enum": ["dorm", "mechanical_room"], "description": "Type of room"}
            }}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_ac_unit",
            "description": "Add a new AC unit to the graph. If no ac_id given, auto-increment is used.",
            "parameters": {"type": "object", "properties": {
                "ac_id": {"type": "string", "description": "Optional custom AC ID like AC3"}
            }}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_sensor",
            "description": "Add a new sensor to the graph. If no sensor_id given, auto-increment is used.",
            "parameters": {"type": "object", "properties": {
                "sensor_id": {"type": "string", "description": "Optional custom sensor ID like T07"},
                "sensor_type": {"type": "string", "enum": ["temperature", "occupancy"]}
            }}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_node",
            "description": "Delete a node from the graph by its display name",
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string", "description": "Node display name like Room09, AC3, T07"}
            }, "required": ["name"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_relationship",
            "description": "Delete a relationship between two nodes by type",
            "parameters": {"type": "object", "properties": {
                "node_a": {"type": "string", "description": "Source node name"},
                "rel_type": {"type": "string", "description": "Relationship type like SERVICES, LOCATED_IN, HAS_SENSOR, MONITORS"},
                "node_b": {"type": "string", "description": "Target node name"}
            }, "required": ["node_a", "rel_type", "node_b"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_sensors_to_rooms",
            "description": "Add sensors to multiple rooms at once and link them with HAS_SENSOR. Use this instead of calling add_sensor separately for each room.",
            "parameters": {"type": "object", "properties": {
                "room_ids": {"type": "array", "items": {"type": "string"}, "description": "List of room IDs like ['Room07', 'Room08']"},
                "sensor_type": {"type": "string", "enum": ["temperature", "occupancy"]}
            }, "required": ["room_ids"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_relationship",
            "description": "Create a relationship between two existing nodes. Use for connecting rooms to AC units (SERVICES), placing AC units in rooms (LOCATED_IN), or linking sensors to rooms (HAS_SENSOR) or AC units (MONITORS).",
            "parameters": {"type": "object", "properties": {
                "node_a": {"type": "string", "description": "Source node name like Room09, AC2"},
                "rel_type": {"type": "string", "description": "Relationship type: SERVICES, LOCATED_IN, HAS_SENSOR, MONITORS"},
                "node_b": {"type": "string", "description": "Target node name like AC2, Room01, T01"}
            }, "required": ["node_a", "rel_type", "node_b"]}
        }
    }
]


class Agent:
    def __init__(self, dorm_service, model=None, base_url=None, api_key=None):
        self.service = dorm_service
        self.model = model or os.getenv("LLM_MODEL", "qwen2.5:7b")
        base_url = base_url or os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
        api_key = api_key or os.getenv("LLM_API_KEY", "ollama")
        try:
            self.client = OpenAI(base_url=base_url, api_key=api_key)
        except Exception:
            self.client = None
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def is_available(self):
        return self.client is not None

    def _call_function(self, name, args):
        print(f"[AGENT] Calling: {name}({args})", file=sys.stderr, flush=True)
        fn = getattr(self.service, name, None)
        if not fn:
            print(f"[AGENT] Function {name} not found!", file=sys.stderr, flush=True)
            return f"Error: function {name} not found"
        try:
            result = fn(**args)
            print(f"[AGENT] Result: {json.dumps(result, default=str)[:200]}", file=sys.stderr, flush=True)
            return json.dumps(result, default=str)
        except Exception as e:
            print(f"[AGENT] Error: {e}", file=sys.stderr, flush=True)
            return json.dumps({"error": str(e)})

    def ask(self, user_input):
        if not self.client:
            return None

        self.messages.append({"role": "user", "content": user_input})
        max_turns = 10

        for _ in range(max_turns):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.1,
                )
            except Exception as e:
                return f"LLM error: {e}"

            msg = response.choices[0].message

            if not msg.tool_calls:
                out = msg.content or ""
                print(f"[AGENT] Final response: {out[:200]}", file=sys.stderr, flush=True)
                self.messages.append({"role": "assistant", "content": out})
                return out

            calls = [(tc.function.name, tc.function.arguments) for tc in msg.tool_calls]
            print(f"[AGENT] LLM requests tools: {calls}", file=sys.stderr, flush=True)
            self.messages.append(msg)

            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}
                result = self._call_function(name, args)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result
                })

        return "I've reached the maximum number of steps. Please try a simpler question."

    def reset(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
