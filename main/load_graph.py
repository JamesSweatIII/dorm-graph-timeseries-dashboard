from neo4j import GraphDatabase
from llama_index.core.schema import Document

from neo4j import GraphDatabase

def load_dorm_graph(uri, user, password):
    print("Connecting to Neo4j...")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        # FULL WIPE: Remove all nodes + relationships
        session.run("MATCH (n) DETACH DELETE n")

        print("Creating clean dorm graph...")
        queries = """
        UNWIND [
          {id: 'Room01', type: 'dorm'},
          {id: 'Room02', type: 'dorm'},
          {id: 'Room03', type: 'dorm'},
          {id: 'Room04', type: 'dorm'},
          {id: 'Room05', type: 'dorm'},
          {id: 'Room06', type: 'dorm'},
          {id: 'Room07', type: 'mechanical_room'},
          {id: 'Room08', type: 'mechanical_room'}
        ] AS room
        CREATE (:Room {room_id: room.id, room_type: room.type});

        CREATE (ac1:ACUnit {ac_id: 'AC1'});
        CREATE (ac2:ACUnit {ac_id: 'AC2'});

        MATCH (ac1:ACUnit {ac_id: 'AC1'}), (r7:Room {room_id: 'Room07'})
        CREATE (ac1)-[:LOCATED_IN]->(r7);

        MATCH (ac2:ACUnit {ac_id: 'AC2'}), (r8:Room {room_id: 'Room08'})
        CREATE (ac2)-[:LOCATED_IN]->(r8);

        MATCH (ac1:ACUnit {ac_id: 'AC1'}), (r1:Room {room_id: 'Room01'}), (r2:Room {room_id: 'Room02'}), (r3:Room {room_id: 'Room03'})
        CREATE (ac1)-[:SERVICES]->(r1),
               (ac1)-[:SERVICES]->(r2),
               (ac1)-[:SERVICES]->(r3);

        MATCH (ac2:ACUnit {ac_id: 'AC2'}), (r4:Room {room_id: 'Room04'}), (r5:Room {room_id: 'Room05'}), (r6:Room {room_id: 'Room06'})
        CREATE (ac2)-[:SERVICES]->(r4),
               (ac2)-[:SERVICES]->(r5),
               (ac2)-[:SERVICES]->(r6);

        UNWIND ['Room01', 'Room02', 'Room03', 'Room04', 'Room05', 'Room06'] AS dorm
        MATCH (r:Room {room_id: dorm})
        CREATE (r)-[:HAS_SENSOR]->(:Sensor {sensor_id: 'Temp_' + dorm, type: 'temperature'}),
               (r)-[:HAS_SENSOR]->(:Sensor {sensor_id: 'Occ_' + dorm, type: 'occupancy'});

        UNWIND ['Room01', 'Room02', 'Room03', 'Room04', 'Room05', 'Room06'] AS dorm
        MATCH (r:Room {room_id: dorm})<-[:SERVICES]-(ac:ACUnit), (s:Sensor {sensor_id: 'Temp_' + dorm})
        CREATE (s)-[:MONITORS]->(ac);
        """.strip().split(';')

        for query in queries:
            if query.strip():
                session.run(query.strip())

        # Verify rooms
        results = session.run("MATCH (r:Room) RETURN r.room_id AS id, r.room_type AS type ORDER BY r.room_id")

    driver.close()
    print("Graph creation completed.")


def fetch_graph_data(neo4j_uri, neo4j_user, neo4j_password):
    """
    Fetches all relevant graph relationships from Neo4j and returns them as Document objects.
    """
    graph_docs = []
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    with driver.session() as session:
        query = """
        MATCH (r:Room)-[:HAS_SENSOR]->(s:Sensor)
        RETURN r.room_id AS source, 'HAS_SENSOR' AS relationship, s.sensor_id AS target
        UNION
        MATCH (s:Sensor)-[:MONITORS]->(ac:ACUnit)
        RETURN s.sensor_id AS source, 'MONITORS' AS relationship, ac.ac_id AS target
        UNION
        MATCH (ac:ACUnit)-[:SERVICES]->(r:Room)
        RETURN ac.ac_id AS source, 'SERVICES' AS relationship, r.room_id AS target
        UNION
        MATCH (ac:ACUnit)-[:LOCATED_IN]->(r:Room)
        RETURN ac.ac_id AS source, 'LOCATED_IN' AS relationship, r.room_id AS target
        """
        results = session.run(query)

        for record in results:
            graph_docs.append(
                Document(
                    text=f"Source: {record['source']}, Relationship: {record['relationship']}, Target: {record['target']}",
                    metadata={"type": "graph"}
                )
            )
    driver.close()
    return graph_docs
