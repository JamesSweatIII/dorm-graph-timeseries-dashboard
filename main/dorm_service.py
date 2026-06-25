import json
from neo4j import GraphDatabase


class DormSearchService:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_room(self, room_id):
        with self.driver.session() as s:
            r = s.run(
                "MATCH (r:Room) WHERE r.room_id CONTAINS $id RETURN r, labels(r) AS ls",
                id=room_id
            ).single()
            if not r:
                return None
            n = dict(r["r"])
            rid = n.get("room_id")
            sensors = [
                {"sensor_id": row["id"], "type": row["type"]}
                for row in s.run(
                    "MATCH (r:Room {room_id:$id})-[:HAS_SENSOR]->(s:Sensor) RETURN s.sensor_id AS id, s.type AS type",
                    id=rid
                )
            ]
            ac_serving = [
                row["id"] for row in s.run(
                    "MATCH (a:ACUnit)-[:SERVICES]->(r:Room {room_id:$id}) RETURN a.ac_id AS id",
                    id=rid
                )
            ]
            ac_located = s.run(
                "MATCH (a:ACUnit)-[:LOCATED_IN]->(r:Room {room_id:$id}) RETURN a.ac_id AS id",
                id=rid
            ).single()
            return {
                "name": rid,
                "type": n.get("room_type"),
                "sensors": sensors,
                "served_by": ac_serving,
                "ac_located_in_room": ac_located["id"] if ac_located else None
            }

    def get_ac_unit(self, ac_id):
        with self.driver.session() as s:
            r = s.run(
                "MATCH (a:ACUnit) WHERE a.ac_id CONTAINS $id RETURN a, labels(a) AS ls",
                id=ac_id
            ).single()
            if not r:
                return None
            n = dict(r["a"])
            aid = n.get("ac_id")
            rooms_served = [
                row["id"] for row in s.run(
                    "MATCH (a:ACUnit {ac_id:$id})-[:SERVICES]->(r:Room) RETURN r.room_id AS id",
                    id=aid
                )
            ]
            located_in = s.run(
                "MATCH (a:ACUnit {ac_id:$id})-[:LOCATED_IN]->(r:Room) RETURN r.room_id AS id",
                id=aid
            ).single()
            monitored_by = [
                row["id"] for row in s.run(
                    "MATCH (s:Sensor)-[:MONITORS]->(a:ACUnit {ac_id:$id}) RETURN s.sensor_id AS id",
                    id=aid
                )
            ]
            return {
                "name": aid,
                "rooms_served": rooms_served,
                "located_in": located_in["id"] if located_in else None,
                "monitored_by": monitored_by
            }

    def get_sensor(self, sensor_id):
        with self.driver.session() as s:
            r = s.run(
                "MATCH (s:Sensor) WHERE s.sensor_id CONTAINS $id RETURN s, labels(s) AS ls",
                id=sensor_id
            ).single()
            if not r:
                return None
            n = dict(r["s"])
            sid = n.get("sensor_id")
            room = s.run(
                "MATCH (r:Room)-[:HAS_SENSOR]->(s:Sensor {sensor_id:$id}) RETURN r.room_id AS id",
                id=sid
            ).single()
            monitors = s.run(
                "MATCH (s:Sensor {sensor_id:$id})-[:MONITORS]->(a:ACUnit) RETURN a.ac_id AS id",
                id=sid
            ).single()
            return {
                "name": sid,
                "type": n.get("type"),
                "located_in_room": room["id"] if room else None,
                "monitors_ac": monitors["id"] if monitors else None
            }

    def search_nodes(self, query):
        with self.driver.session() as s:
            rows = list(s.run(
                "MATCH (n) WHERE reduce(acc='',k IN keys(n)|acc+toString(n[k])) CONTAINS $q "
                "RETURN elementId(n) AS id, n, labels(n) AS ls LIMIT 20",
                q=query.lower()
            ))
            results = []
            for r in rows:
                p = dict(r["n"])
                results.append({
                    "id": r["id"],
                    "name": p.get("room_id") or p.get("ac_id") or p.get("sensor_id") or "(unnamed)",
                    "label": r["ls"][0] if r["ls"] else "Unknown"
                })
            return results

    def get_rooms_without_sensors(self):
        with self.driver.session() as s:
            rows = list(s.run(
                "MATCH (r:Room) WHERE NOT (r)-[:HAS_SENSOR]->(:Sensor) RETURN r.room_id AS id"
            ))
            return [r["id"] for r in rows]

    def get_rooms_with_sensor_type(self, sensor_type):
        with self.driver.session() as s:
            rows = list(s.run(
                "MATCH (r:Room)-[:HAS_SENSOR]->(s:Sensor {type:$t}) RETURN DISTINCT r.room_id AS id",
                t=sensor_type
            ))
            return [r["id"] for r in rows]

    def get_rooms_served_by(self, ac_id):
        with self.driver.session() as s:
            rows = list(s.run(
                "MATCH (a:ACUnit {ac_id:$id})-[:SERVICES]->(r:Room) RETURN r.room_id AS id",
                id=ac_id
            ))
            return [r["id"] for r in rows]

    def get_average_sensors_per_room(self):
        with self.driver.session() as s:
            r = s.run(
                "MATCH (r:Room) OPTIONAL MATCH (r)-[:HAS_SENSOR]->(s:Sensor) "
                "RETURN count(DISTINCT r) AS rooms, count(s) AS total_sensors"
            ).single()
            rooms = r["rooms"]
            total = r["total_sensors"]
            return round(total / rooms, 1) if rooms else 0

    def get_all_rooms(self):
        with self.driver.session() as s:
            rows = list(s.run("MATCH (r:Room) RETURN r.room_id AS id, r.room_type AS type ORDER BY r.room_id"))
            seen = set()
            result = []
            for row in rows:
                rid = row["id"]
                if rid not in seen:
                    seen.add(rid)
                    result.append({"id": rid, "type": row["type"]})
            return result

    def get_all_ac_units(self):
        with self.driver.session() as s:
            rows = list(s.run("MATCH (a:ACUnit) RETURN a.ac_id AS id ORDER BY a.ac_id"))
            return [r["id"] for r in rows]

    def get_all_sensors(self):
        with self.driver.session() as s:
            rows = list(s.run("MATCH (s:Sensor) RETURN s.sensor_id AS id, s.type AS type ORDER BY s.sensor_id"))
            return [{"id": r["id"], "type": r["type"]} for r in rows]

    def node_detail(self, element_id):
        with self.driver.session() as s:
            r = s.run("MATCH (n) WHERE elementId(n)=$id RETURN n, labels(n) AS ls", id=element_id).single()
            if not r:
                return None
            props = dict(r["n"])
            labels = r["ls"]
            conns = list(s.run(
                "MATCH (n)-[rel]->(m) WHERE elementId(n)=$id RETURN rel.type AS t, m",
                id=element_id
            ))
            connections = []
            for c in conns:
                mp = dict(c["m"])
                connections.append({
                    "relationship": c["t"],
                    "target": mp.get("room_id") or mp.get("ac_id") or mp.get("sensor_id") or ""
                })
            return {"props": props, "labels": labels, "connections": connections}

    def find_rooms_with(self, has_sensor_type=None, without_sensor_type=None, served_by=None):
        with self.driver.session() as s:
            results = list(s.run("MATCH (r:Room) RETURN r.room_id AS id, r.room_type AS type"))
            rooms = [{"id": r["id"], "type": r["type"]} for r in results]

            if has_sensor_type:
                matching = set(self.get_rooms_with_sensor_type(has_sensor_type))
                rooms = [r for r in rooms if r["id"] in matching]

            if without_sensor_type:
                without = set(self.get_rooms_without_sensor_type(without_sensor_type))
                rooms = [r for r in rooms if r["id"] in without]

            if served_by:
                matching = set(self.get_rooms_served_by(served_by))
                rooms = [r for r in rooms if r["id"] in matching]

            return rooms

    def get_rooms_without_sensor_type(self, sensor_type):
        with self.driver.session() as s:
            with_sensor = set(
                r["id"] for r in s.run(
                    "MATCH (r:Room)-[:HAS_SENSOR]->(s:Sensor {type:$t}) RETURN r.room_id AS id",
                    t=sensor_type
                )
            )
            all_rooms = set(r["id"] for r in s.run("MATCH (r:Room) RETURN r.room_id AS id"))
            return list(all_rooms - with_sensor)

    def get_ac_located_in(self, room_id):
        with self.driver.session() as s:
            r = s.run(
                "MATCH (a:ACUnit)-[:LOCATED_IN]->(r:Room {room_id:$id}) RETURN a.ac_id AS id",
                id=room_id
            ).single()
            return r["id"] if r else None

    def get_monitored_by(self, room_id):
        with self.driver.session() as s:
            rows = list(s.run(
                "MATCH (r:Room {room_id:$id})-[:HAS_SENSOR]->(s:Sensor) RETURN s.sensor_id AS id, s.type AS type",
                id=room_id
            ))
            return [{"sensor_id": r["id"], "type": r["type"]} for r in rows]

    def resolve_node(self, name):
        with self.driver.session() as s:
            r = s.run(
                "MATCH (n) WHERE toUpper(coalesce(n.room_id,''))=toUpper($name) "
                "OR toUpper(coalesce(n.ac_id,''))=toUpper($name) "
                "OR toUpper(coalesce(n.sensor_id,''))=toUpper($name) "
                "RETURN elementId(n) AS id, n, labels(n) AS ls LIMIT 1",
                name=name
            ).single()
            if not r:
                return None
            props = dict(r["n"])
            labels = r["ls"]
            node_type = next((t for t in ("Room", "ACUnit", "Sensor") if t in labels), None)
            subtype = None
            if node_type == "Room":
                subtype = props.get("room_type")
            elif node_type == "Sensor":
                subtype = props.get("type", "").lower()
            return {"id": r["id"], "type": node_type, "subtype": subtype, "name": name}

    def get_time_series_for_node(self, name):
        from time_series import generate_time_series
        node = self.resolve_node(name)
        if not node:
            return None
        return generate_time_series(node["id"], node["type"], node["subtype"])

    def query_knowledge_graph(self, cypher_query: str) -> str:
        """Execute arbitrary Cypher against Neo4j and return JSON string of results."""
        try:
            with self.driver.session() as s:
                result = list(s.run(cypher_query))
                data = [dict(r) for r in result]
                return json.dumps(data, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def fetch_time_series_metrics(self, entity_id: str, metric: str = "") -> str:
        """Fetch 24-hour time series readings for a node. Returns JSON with label, metrics list, and readings."""
        try:
            ts = self.get_time_series_for_node(entity_id)
            if not ts:
                return json.dumps({"error": f"Entity '{entity_id}' not found."})
            data = ts["data"]
            cols = ts.get("columns", [])
            if metric and metric != "all" and metric in cols:
                values = [{"time": row["time"], metric: row.get(metric)} for row in data]
            else:
                values = data
            return json.dumps({
                "entity_id": entity_id,
                "label": ts["label"],
                "available_metrics": cols,
                "readings": values
            }, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ── Mutations ────────────────────────────────────────────────────────────────

    def get_aggregate_reading(self, name, metric="temperature"):
        node = self.resolve_node(name)
        if not node:
            return {"error": f"Node '{name}' not found."}
        ts = self.get_time_series_for_node(name)
        if not ts or not ts.get("data"):
            return {"error": f"No time series data for '{name}'."}
        if metric not in ts.get("columns", []):
            return {"error": f"Metric '{metric}' not available for '{name}'. Available: {ts['columns']}"}
        values = [row[metric] for row in ts["data"] if metric in row]
        if not values:
            return {"error": f"No {metric} readings for '{name}'."}
        avg = round(sum(values) / len(values), 1)
        lo = min(values)
        hi = max(values)
        return {
            "node": name, "metric": metric, "average": avg,
            "min": lo, "max": hi, "readings": len(values)
        }

    def add_room(self, room_id=None, room_type="dorm"):
        with self.driver.session() as s:
            if room_id:
                exists = s.run("MATCH (r:Room) WHERE toUpper(r.room_id)=toUpper($id) RETURN r", id=room_id).single()
                if exists:
                    return {"ok": False, "msg": f"Room **{room_id}** already exists."}
                s.run("CREATE (r:Room {room_id:$id, room_type:$t})", id=room_id, t=room_type)
                return {"ok": True, "msg": f"Room **{room_id}** ({room_type}) created."}
            else:
                cnt = s.run("MATCH (r:Room {room_type:$t}) RETURN count(r) AS c", t=room_type).single()["c"] + 1
                rid = f"Room{cnt:02d}"
                s.run("CREATE (r:Room {room_id:$id, room_type:$t})", id=rid, t=room_type)
                return {"ok": True, "msg": f"Room **{rid}** ({room_type}) created."}

    def add_ac_unit(self, ac_id=None):
        with self.driver.session() as s:
            if ac_id:
                exists = s.run("MATCH (a:ACUnit {ac_id:$id}) RETURN a", id=ac_id).single()
                if exists:
                    return {"ok": False, "msg": f"AC unit **{ac_id}** already exists."}
                s.run("CREATE (a:ACUnit {ac_id:$id})", id=ac_id)
                return {"ok": True, "msg": f"AC unit **{ac_id}** created."}
            else:
                cnt = s.run("MATCH (a:ACUnit) RETURN count(a) AS c").single()["c"] + 1
                aid = f"AC{cnt}"
                s.run("CREATE (a:ACUnit {ac_id:$id})", id=aid)
                return {"ok": True, "msg": f"AC unit **{aid}** created."}

    def add_sensor(self, sensor_id=None, sensor_type="temperature"):
        with self.driver.session() as s:
            if sensor_id:
                exists = s.run("MATCH (s:Sensor {sensor_id:$id}) RETURN s", id=sensor_id).single()
                if exists:
                    return {"ok": False, "msg": f"Sensor **{sensor_id}** already exists."}
                s.run("CREATE (s:Sensor {sensor_id:$id, type:$t})", id=sensor_id, t=sensor_type)
                return {"ok": True, "msg": f"Sensor **{sensor_id}** ({sensor_type}) created."}
            else:
                tc = s.run("MATCH (s:Sensor {type:$t}) RETURN count(s) AS c", t=sensor_type).single()["c"]
                prefix = "T" if sensor_type == "temperature" else "O"
                sid = f"{prefix}{tc+1:02d}"
                s.run("CREATE (s:Sensor {sensor_id:$id, type:$t})", id=sid, t=sensor_type)
                return {"ok": True, "msg": f"Sensor **{sid}** ({sensor_type}) created."}

    def add_sensors_to_rooms(self, room_ids, sensor_type="temperature"):
        results = []
        with self.driver.session() as s:
            for rid in room_ids:
                room = s.run("MATCH (r:Room {room_id:$id}) RETURN r", id=rid).single()
                if not room:
                    results.append({"room": rid, "ok": False, "msg": f"Room **{rid}** not found."})
                    continue
                cnt = s.run("MATCH (s:Sensor {type:$t}) RETURN count(s) AS c", t=sensor_type).single()["c"] + 1
                prefix = "T" if sensor_type == "temperature" else "O"
                sid = f"{prefix}{cnt:02d}"
                s.run(
                    "MATCH (r:Room {room_id:$rid}) "
                    "CREATE (s:Sensor {sensor_id:$sid, type:$t}) "
                    "CREATE (r)-[:HAS_SENSOR]->(s)",
                    rid=rid, sid=sid, t=sensor_type
                )
                results.append({"room": rid, "ok": True, "msg": f"**{sid}** ({sensor_type}) added to **{rid}**."})
        return results

    def delete_node(self, name):
        with self.driver.session() as s:
            # Case-insensitive match
            r = s.run(
                "MATCH (n) WHERE toUpper(n.room_id)=toUpper($name) OR toUpper(n.ac_id)=toUpper($name) OR toUpper(n.sensor_id)=toUpper($name) "
                "RETURN elementId(n) AS id, labels(n) AS ls",
                name=name
            ).single()
            if not r:
                return {"ok": False, "msg": f"No node found with name **{name}**."}
            lbl = r["ls"][0] if r["ls"] else "Unknown"
            s.run("MATCH (n) WHERE elementId(n)=$id DETACH DELETE n", id=r["id"])
            return {"ok": True, "msg": f"**{name}** ({lbl}) deleted."}

    def delete_relationship(self, node_a, rel_type, node_b):
        with self.driver.session() as s:
            q = (
                f"MATCH (a)-[r:{rel_type}]-(b) WHERE "
                "(toUpper(coalesce(a.room_id,''))=toUpper($na) OR toUpper(coalesce(a.ac_id,''))=toUpper($na) OR toUpper(coalesce(a.sensor_id,''))=toUpper($na)) AND "
                "(toUpper(coalesce(b.room_id,''))=toUpper($nb) OR toUpper(coalesce(b.ac_id,''))=toUpper($nb) OR toUpper(coalesce(b.sensor_id,''))=toUpper($nb)) "
                "DELETE r RETURN count(r) AS cnt"
            )
            r = s.run(q, na=node_a, nb=node_b).single()
            if r and r["cnt"] > 0:
                return {"ok": True, "msg": f"Removed {rel_type} between **{node_a}** and **{node_b}**."}
            return {"ok": False, "msg": f"No {rel_type} relationship found between **{node_a}** and **{node_b}**."}

    def add_relationship(self, node_a, rel_type, node_b):
        dir_map = {
            "SERVICES": ("ACUnit", "Room"),
            "LOCATED_IN": ("ACUnit", "Room"),
            "HAS_SENSOR": ("Room", "Sensor"),
            "MONITORS": ("Sensor", "ACUnit"),
        }
        src_label, tgt_label = dir_map.get(rel_type, ("", ""))
        with self.driver.session() as s:
            if src_label:
                for (first, first_label, second, second_label) in [
                    (node_a, src_label, node_b, tgt_label),
                    (node_b, src_label, node_a, tgt_label),
                ]:
                    key_a = f"{first_label.lower()}_id" if first_label == "ACUnit" else f"{first_label.lower()}_id"
                    key_b = f"{second_label.lower()}_id" if second_label == "ACUnit" else f"{second_label.lower()}_id"
                    key_a = "ac_id" if first_label == "ACUnit" else ("room_id" if first_label == "Room" else "sensor_id")
                    key_b = "ac_id" if second_label == "ACUnit" else ("room_id" if second_label == "Room" else "sensor_id")
                    r = s.run(
                        f"MATCH (a:{first_label}) WHERE a.{key_a}=$na RETURN a LIMIT 1",
                        na=first
                    ).single()
                    if r:
                        r2 = s.run(
                            f"MATCH (b:{second_label}) WHERE b.{key_b}=$nb RETURN b LIMIT 1",
                            nb=second
                        ).single()
                        if r2:
                            s.run(
                                f"MATCH (a:{first_label} {{{key_a}: $na}}), (b:{second_label} {{{key_b}: $nb}}) "
                                f"MERGE (a)-[:{rel_type}]->(b)",
                                na=first, nb=second
                            )
                            return {"ok": True, "msg": f"Created {rel_type} from **{first}** to **{second}**."}
                return {"ok": False, "msg": f"Could not find matching {src_label} or {tgt_label} for **{node_a}** and **{node_b}**."}
            s.run(
                f"MATCH (a {{ac_id: $na}}), (b {{ac_id: $nb}}) "
                f"MERGE (a)-[:{rel_type}]->(b)",
                na=node_a, nb=node_b
            )
            return {"ok": True, "msg": f"Created {rel_type} from **{node_a}** to **{node_b}**."}
