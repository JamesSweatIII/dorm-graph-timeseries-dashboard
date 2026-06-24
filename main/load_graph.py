from neo4j import GraphDatabase


def load_dorm_graph(uri, user, password):
    print("Connecting to Neo4j...")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
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

        session.run("MATCH (r:Room) RETURN r.room_id AS id, r.room_type AS type ORDER BY r.room_id")

    driver.close()
    print("Graph creation completed.")
