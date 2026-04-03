import numpy as np
from typing import Dict, Any, List
from app.db.neo4j import neo4j_db
from app.core.logging import log

def fetch_graph_topology() -> List[Dict[str, Any]]:
    """ Pulls exact tier dependencies and transit routes from Neo4j correctly natively. """
    session = neo4j_db.get_session()
    if not session:
        return []
        
    try:
        # Query extracting source-to-target dependencies + what shipping lane they utilize
        deps_result = session.run("""
            MATCH (s:Supplier)-[r:SUPPLIES_TO]->(t)
            OPTIONAL MATCH (s)-[:SHIPS_VIA]->(route:Route)
            RETURN s.id AS source, t.id AS target, r.lead_days AS lead_days, route.id AS route
        """)
        
        topology = []
        for record in deps_result:
            topology.append({
                "source": record["source"],
                "target": record["target"],
                "lead_days": record["lead_days"],
                "route": record["route"]
            })
        return topology
    finally:
        session.close()

def run_whatif_simulation(
    chokepoint_id: str, 
    lock_days: int, 
    supplier_failure_id: str, 
    demand_spike_percent: float
) -> Dict[str, Any]:
    """
    Executes a 1000-iteration Monte Carlo engine evaluating statistical cascades.
    Returns calculated risk probability densities natively.
    """
    topology = fetch_graph_topology()
    if not topology:
        raise ValueError("Neo4j Graph Database is unavailable or strictly empty. Please hit /suppliers/graph to seed first.")
        
    ITERATIONS = 1000
    
    # Statistics Tracking
    stockout_count = 0
    cascading_failures = []
    total_cost_impacts = []
    
    OEM_ID = "OEM-001"
    
    for _ in range(ITERATIONS):
        failed_nodes = set()
        
        # 1. Supplier Direct Failure injection
        if supplier_failure_id:
            # 85% chance the targeted supplier fully defaults during this iteration
            if np.random.rand() < 0.85:
                failed_nodes.add(supplier_failure_id)
                
        # 2. Chokepoint Transit Lock injection
        if chokepoint_id:
            # If a supplier relies on the blocked route, simulate delivery failure against buffer stocks
            for edge in topology:
                if edge["route"] == chokepoint_id:
                    buffer_capacity = np.random.normal(15, 5) # E.g., 15 days of inventory buffering
                    if lock_days > buffer_capacity:
                        # Inventory breached. 60% probability that production totally halts for this supplier
                        if np.random.rand() < 0.6: 
                            failed_nodes.add(edge["source"])
                            
        # 3. Network Cascading Failure simulation
        changed = True
        while changed:
            changed = False
            for edge in topology:
                if edge["source"] in failed_nodes and edge["target"] not in failed_nodes:
                    # If target is missing a part from source, 50% probability target production halts
                    if np.random.rand() < 0.5: 
                        failed_nodes.add(edge["target"])
                        changed = True
                        
        # 4. Spike Demand Stress injection
        if demand_spike_percent > 20.0:
            stress_prob = min((demand_spike_percent - 20) / 100.0, 0.4)
            if np.random.rand() < stress_prob:
                failed_nodes.add(OEM_ID)
                
        # Result Evaluation for Iteration
        if OEM_ID in failed_nodes:
            stockout_count += 1
            cascading_failures.append(len(failed_nodes))
            
            # Parametric cost algorithm scaling with disruption breadth
            cascade_penalty = len(failed_nodes) * 200000 
            lock_penalty = lock_days * 50000 if chokepoint_id else 0
            base_loss = np.random.normal(500000, 100000)
            
            total_cost_impacts.append(base_loss + cascade_penalty + lock_penalty)
            
    # Density aggregation
    stockout_prob = (stockout_count / ITERATIONS) * 100.0
    avg_cascade = float(np.mean(cascading_failures)) if cascading_failures else 0.0
    avg_cost = float(np.mean(total_cost_impacts)) if total_cost_impacts else 0.0
    
    log.info("monte_carlo_complete", iterations=ITERATIONS, stockout_prob=stockout_prob, avg_cascade=avg_cascade)
    
    return {
        "iterations": ITERATIONS,
        "probability_of_stockout_percent": round(stockout_prob, 2),
        "avg_nodes_failed_cascading": round(avg_cascade, 1),
        "estimated_cost_impact_usd": round(avg_cost, 2),
        "parameters": {
            "chokepoint_id": chokepoint_id,
            "lock_days": lock_days,
            "supplier_failure_id": supplier_failure_id,
            "demand_spike_percent": demand_spike_percent
        }
    }
