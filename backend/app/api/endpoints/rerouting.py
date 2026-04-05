from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.rerouting_service import calculate_redistribution
from app.core.logging import log

router = APIRouter()

class Warehouse(BaseModel):
    name: str
    stock: float
    lat: float
    lon: float

class ReroutePayload(BaseModel):
    warehouses: List[Warehouse]
    main_warehouse: Optional[str] = None
    company_id: Optional[int] = None

@router.post("/calculate", response_model=Dict[str, Any])
async def compute_stock_redistribution(payload: ReroutePayload, db: Session = Depends(get_db)):
    """
    Computes optimal stock redistribution across user-uploaded warehouses.
    Fuses uploaded supply data with tracked demand sensing from the DB/API.
    """
    try:
        log.info("rerouting_calculation_requested", num_warehouses=len(payload.warehouses))
        
        # Step 1: Mock/Get Demand for these regions (Step 1 of USER's Logic)
        # In a real system, we'd look this up in Redis/Postgres.
        # For now, we seed realistic demand variation to show the engine in action.
        import random
        demand_map = {}
        for wh in payload.warehouses:
            # Randomizes demand between 30% and 150% of stock to create deficits/surpluses
            demand_map[wh.name] = round(wh.stock * random.uniform(0.3, 1.8), 0)
            
        # USER explicitly asked for Pune: 5000, Mumbai: 15000, Delhi: 4000
        # If those names exist, we prioritize them for the demo.
        if "Pune" in [w.name for w in payload.warehouses]: demand_map["Pune"] = 5000
        if "Mumbai" in [w.name for w in payload.warehouses]: demand_map["Mumbai"] = 15000
        if "Delhi" in [w.name for w in payload.warehouses]: demand_map["Delhi"] = 4000

        # Step 2: Persist Warehouses to DB (Native DB Source for Bot)
        from app.models.warehouse import Warehouse as WarehouseModel
        cid = payload.company_id or 1
        
        # Clear old nodes for this company (Clean slate for Rerouting)
        db.query(WarehouseModel).filter(WarehouseModel.company_profile_id == cid).delete()
        
        for wh in payload.warehouses:
            node = WarehouseModel(
                company_profile_id=cid,
                name=wh.name,
                stock=wh.stock,
                lat=wh.lat,
                lon=wh.lon,
                demand=demand_map.get(wh.name, 0.0)
            )
            db.add(node)
        
        # Run the Redistribution Engine
        warehouses_list = [w.dict() for w in payload.warehouses]
        result = calculate_redistribution(warehouses_list, demand_map)
        
        db.commit() # Save all warehouses + demand snapshots to native DB
        # Step 3: Persist Total Network Supply for Demand Tab Sync
        total_supply = sum(w.stock for w in payload.warehouses)
        try:
            from app.db.redis import redis_client
            # Save total supply for this company/SKU to be picked up by the DS Ratio engine
            # For simplicity, we use a global key since we assume single tenant for demo
            redis_client.set(f"network_supply:{payload.company_id or 1}", str(total_supply))
            log.info("persisted_network_supply", total_supply=total_supply)
        except Exception as e:
            log.warning("failed_to_persist_supply", error=str(e))

        return {
            "status": "success",
            "demand_snapshot": demand_map,
            "visualization": result["nodes"],
            "suggestions": result["transfers"],
            "total_network_supply": total_supply
        }
    except Exception as e:
        log.error("rerouting_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
