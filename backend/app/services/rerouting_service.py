import math
from typing import List, Dict, Any

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates the great-circle distance between two points on Earth in km."""
    R = 6371  # Earth radius
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_redistribution(warehouses: List[Dict[str, Any]], demand_map: Dict[str, float]) -> Dict[str, Any]:
    """
    Core Decision Engine for Stock Redistribution.
    Compares Supply vs Demand and suggests transfers based on proximity.
    """
    results = []
    surplus_pool = []
    deficit_pool = []
    
    # Step 1: Identify Deficits and Surpluses
    for wh in warehouses:
        name = wh["name"]
        stock = wh["stock"]
        demand = demand_map.get(name, 0)
        net = stock - demand
        
        status = "OK"
        if net < -100: status = "DEFICIT"
        elif net > 100: status = "SURPLUS"
        
        node = {
            **wh,
            "net": net,
            "demand": demand,
            "status": status,
            "color": "red" if status == "DEFICIT" else ("blue" if status == "SURPLUS" else "green")
        }
        results.append(node)
        
        if status == "SURPLUS": surplus_pool.append(node)
        elif status == "DEFICIT": deficit_pool.append(node)
        
    # Step 2: Decision Engine (Shift stock from nearest surplus to deficit)
    transfers = []
    
    # Sort deficit by severity-to-address (largest gap first)
    deficit_pool.sort(key=lambda x: x["net"])
    
    for def_node in deficit_pool:
        needed = abs(def_node["net"])
        
        # Find all available surplus nodes and sort by distance to this deficit node
        candidates = []
        for sur_node in surplus_pool:
            if sur_node["net"] <= 0: continue
            dist = haversine_distance(def_node["lat"], def_node["lon"], sur_node["lat"], sur_node["lon"])
            candidates.append({"node": sur_node, "dist": dist})
        
        candidates.sort(key=lambda x: x["dist"])
        
        for cand in candidates:
            if needed <= 0: break
            sur_node = cand["node"]
            available = sur_node["net"]
            
            transfer_qty = min(needed, available)
            if transfer_qty <= 0: continue
            
            # Transit Time (Avg fleet speed: 60km/h)
            transit_hours = cand["dist"] / 60
            eta_str = f"{round(transit_hours, 1)}h" if transit_hours < 24 else f"{round(transit_hours/24, 1)}d"
            
            # Simulated weather based on distance logic (demonstration)
            weather = "Heavy Rain" if cand["dist"] > 1000 else ("Cloudy" if cand["dist"] > 500 else "Clear")

            transfers.append({
                "from": sur_node["name"],
                "to": def_node["name"],
                "quantity": int(transfer_qty),
                "distance_km": round(cand["dist"], 1),
                "eta": eta_str,
                "weather": weather,
                "reason": f"Deficit at {def_node['name']} ({int(def_node['demand'])} demand) matched with proximal surplus at {sur_node['name']}."
            })
            
            sur_node["net"] -= transfer_qty
            needed -= transfer_qty
            
    return {
        "nodes": results,
        "transfers": transfers
    }
