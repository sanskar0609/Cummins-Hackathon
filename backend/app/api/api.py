from fastapi import APIRouter
from app.api.endpoints import alerts, reports

api_router = APIRouter()
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])

try:
    from app.api.endpoints import ais, flights, risk, demand, route_risk, supply, suppliers, simulation, agents, copilot
    api_router.include_router(ais.router, prefix="/ais", tags=["AIS"])
    api_router.include_router(flights.router, prefix="/flights", tags=["Flights"])
    api_router.include_router(risk.router, prefix="/risk", tags=["Risk Intelligence"])
    api_router.include_router(route_risk.router, prefix="/risk", tags=["Route Intelligence"])
    api_router.include_router(demand.router, prefix="/demand", tags=["Demand Forecasting"])
    api_router.include_router(supply.router, prefix="/supply", tags=["Supply Optimization"])
    api_router.include_router(suppliers.router, prefix="/suppliers", tags=["Supplier Graph & Intelligence"])
    api_router.include_router(simulation.router, prefix="/simulate", tags=["Monte Carlo Engine"])
    api_router.include_router(agents.router, prefix="/agents", tags=["Autonomous AI Agents"])
    api_router.include_router(copilot.router, prefix="/copilot", tags=["AI Copilot Websockets"])
except ImportError as e:
    print(f'Warning: optional endpoint failed to load: {e}')
