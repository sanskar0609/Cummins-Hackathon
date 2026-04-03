from app.db.neo4j import neo4j_db
from app.core.logging import log

def seed_supply_graph():
    """
    Clears the entire Neo4j database and natively reconstructs a 20-node 
    Multi-Tier mock supply network graph including Products and Routes.
    Called externally (e.g., startup script or API trigger) for scaffolding.
    """
    session = neo4j_db.get_session()
    if not session:
        log.warning("neo4j_session_unavailable_cannot_seed")
        return

    try:
        # 1. Wipe current schema entirely
        session.run("MATCH (n) DETACH DELETE n")
        log.info("neo4j_graph_wiped")

        # 2. Build multi-level node matrix using robust Cypher queries
        cypher_nodes = """
        // ── CORE COMPANY (The OEM)
        CREATE (oem:Company {id: 'OEM-001', name: 'Global Supply Co.', type: 'OEM', tier: 'T0'})

        // ── TIER 1 SUPPLIERS
        CREATE (s1:Supplier {id: 'SUP-T1-A', name: 'Foxx Assembly', tier: 'T1', location: 'Taiwan', health: 'GOOD'})
        CREATE (s2:Supplier {id: 'SUP-T1-B', name: 'EuroMotor Parts', tier: 'T1', location: 'Germany', health: 'GOOD'})
        CREATE (s3:Supplier {id: 'SUP-T1-C', name: 'AmeriCasting', tier: 'T1', location: 'USA', health: 'WARNING'})

        // ── TIER 2 SUPPLIERS (Components & Semiconductors)
        CREATE (s4:Supplier {id: 'SUP-T2-A', name: 'TSMC Advanced', tier: 'T2', location: 'Taiwan', health: 'GOOD'})
        CREATE (s5:Supplier {id: 'SUP-T2-B', name: 'Nvidia IC', tier: 'T2', location: 'USA', health: 'GOOD'})
        CREATE (s6:Supplier {id: 'SUP-T2-C', name: 'Bosch Sensors', tier: 'T2', location: 'Germany', health: 'GOOD'})
        CREATE (s7:Supplier {id: 'SUP-T2-D', name: 'Shenzhen Circuits', tier: 'T2', location: 'China', health: 'WARNING'})

        // ── TIER 3 SUPPLIERS (Raw Materials)
        CREATE (s8:Supplier {id: 'SUP-T3-A', name: 'Aus Mining', tier: 'T3', location: 'Australia', health: 'GOOD'})
        CREATE (s9:Supplier {id: 'SUP-T3-B', name: 'Chile Copper Ltd', tier: 'T3', location: 'Chile', health: 'CRITICAL'})
        CREATE (s10:Supplier {id: 'SUP-T3-C', name: 'DRC Cobalt', tier: 'T3', location: 'DRC', health: 'WARNING'})
        CREATE (s11:Supplier {id: 'SUP-T3-D', name: 'Lithium Corp', tier: 'T3', location: 'Bolivia', health: 'GOOD'})

        // ── PRODUCTS
        CREATE (p1:Product {id: 'PROD-001', name: 'Autonomous Server Rig'})
        CREATE (p2:Product {id: 'PROD-002', name: 'Battery Array'})
        CREATE (p3:Product {id: 'PROD-003', name: 'Sensor Module M1'})
        CREATE (p4:Product {id: 'PROD-004', name: 'Raw Lithium'})
        CREATE (p5:Product {id: 'PROD-005', name: 'Raw Copper'})
        CREATE (p6:Product {id: 'PROD-006', name: 'Silicon Wafer'})

        // ── TRANSIT LAKES / ROUTES
        CREATE (r1:Route {id: 'SUEZ-ROTTERDAM', name: 'Suez Canal Route', type: 'Maritime'})
        CREATE (r2:Route {id: 'PANAMA-LA', name: 'Panama Canal Route', type: 'Maritime'})
        CREATE (r3:Route {id: 'TAIWAN-LA', name: 'Taiwan Strait Express', type: 'AirFreight'})

        // ── RELATIONSHIP BINDINGS
        // Product Line Bindings
        CREATE (oem)-[:DEPENDS_ON]->(p1)
        CREATE (oem)-[:DEPENDS_ON]->(p2)

        // T1 to OEM
        CREATE (s1)-[:SUPPLIES_TO {lead_days: 15}]->(oem)
        CREATE (s2)-[:SUPPLIES_TO {lead_days: 4}]->(oem)
        CREATE (s3)-[:SUPPLIES_TO {lead_days: 2}]->(oem)
        
        // T2 to T1
        CREATE (s4)-[:SUPPLIES_TO {lead_days: 30}]->(s1)
        CREATE (s5)-[:SUPPLIES_TO {lead_days: 25}]->(s1)
        CREATE (s6)-[:SUPPLIES_TO {lead_days: 10}]->(s2)
        CREATE (s7)-[:SUPPLIES_TO {lead_days: 45}]->(s3)

        // T3 to T2 (Raw to Component)
        CREATE (s8)-[:SUPPLIES_TO {lead_days: 60}]->(s6)
        CREATE (s9)-[:SUPPLIES_TO {lead_days: 90}]->(s6)
        CREATE (s10)-[:SUPPLIES_TO {lead_days: 40}]->(s7)
        CREATE (s11)-[:SUPPLIES_TO {lead_days: 60}]->(s4)

        // Route logistics associations (Who ships via where)
        CREATE (s1)-[:SHIPS_VIA]->(r3)
        CREATE (s7)-[:SHIPS_VIA]->(r2)
        CREATE (s8)-[:SHIPS_VIA]->(r1)
        CREATE (s9)-[:SHIPS_VIA]->(r2)
        CREATE (s4)-[:SHIPS_VIA]->(r3)
        """
        session.run(cypher_nodes)
        log.info("neo4j_graph_seeded_successfully", nodes_created=20)
        
    except Exception as e:
        log.error("neo4j_seed_failed", error=str(e))
    finally:
        session.close()

if __name__ == "__main__":
    seed_supply_graph()
