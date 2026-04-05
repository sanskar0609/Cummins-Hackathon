from fastapi import APIRouter
from app.api.endpoints import alerts, reports

api_router = APIRouter()
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])

try:
    from app.api.endpoints import ais
    api_router.include_router(ais.router, prefix="/ais", tags=["AIS"])
except ImportError: print("Warning: AIS not loaded")

try:
    from app.api.endpoints import flights
    api_router.include_router(flights.router, prefix="/flights", tags=["Flights"])
except ImportError: print("Warning: Flights not loaded")

try:
    from app.api.endpoints import risk
    api_router.include_router(risk.router, prefix="/risk", tags=["Risk Intelligence"])
except ImportError: print("Warning: Risk not loaded")

try:
    from app.api.endpoints import route_risk
    api_router.include_router(route_risk.router, prefix="/risk", tags=["Route Intelligence"])
except ImportError: print("Warning: RouteRisk not loaded")

try:
    from app.api.endpoints import demand
    api_router.include_router(demand.router, prefix="/demand", tags=["Demand Forecasting"])
except ImportError: print("Warning: Demand not loaded")

try:
    from app.api.endpoints import onboarding
    api_router.include_router(onboarding.router, prefix="/onboarding", tags=["Supplier & Company Onboarding"])
except ImportError as e: print(f"Warning: Onboarding not loaded: {e}")

try:
    from app.api.endpoints import supply
    api_router.include_router(supply.router, prefix="/supply", tags=["Supply Optimization"])
except ImportError: print("Warning: Supply not loaded")

try:
    from app.api.endpoints import suppliers
    api_router.include_router(suppliers.router, prefix="/suppliers", tags=["Supplier Graph & Intelligence"])
except ImportError: print("Warning: Suppliers not loaded")

try:
    from app.api.endpoints import simulation
    api_router.include_router(simulation.router, prefix="/simulate", tags=["Monte Carlo Engine"])
except ImportError: print("Warning: Simulation not loaded")

try:
    from app.api.endpoints import agents
    api_router.include_router(agents.router, prefix="/agents", tags=["Autonomous AI Agents"])
except ImportError: print("Warning: Agents not loaded")

try:
    from app.api.endpoints import rerouting
    api_router.include_router(rerouting.router, prefix="/rerouting", tags=["Rerouting Intelligence"])
except ImportError: print("Warning: Rerouting not loaded")

try:
    from app.api.endpoints import copilot
    api_router.include_router(copilot.router, prefix="/copilot", tags=["AI Copilot Websockets"])
except ImportError: print("Warning: Copilot not loaded")
