from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from asgi_correlation_id import CorrelationIdMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, log
from app.api.api import api_router

# Configure structured JSON logging
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="Backend API for Supply Chain Intelligence OS"
)

app.include_router(api_router, prefix=settings.API_V1_STR)

# ── CORS ──────────────────────────────────────────────────────────────────────
if settings.CORS_ORIGINS:
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(',')]
    if "http://localhost:5173" not in origins:
        origins.append("http://localhost:5173")
    if "http://localhost:8000" not in origins:
        origins.append("http://localhost:8000")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(CorrelationIdMiddleware)

# ── LIFECYCLE ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    log.info("supply_chain_os_starting")

    # Seed the Neo4j supplier graph on every fresh startup (safe to re-run).
    # The seeder wipes the graph and rebuilds it, so the data is always consistent.
    try:
        from app.services.graph_seeder import seed_supply_graph
        seed_supply_graph()
        log.info("neo4j_graph_seeded_on_startup")
    except Exception as e:
        log.warning("neo4j_seed_skipped_on_startup", error=str(e))


@app.on_event("shutdown")
async def shutdown_event():
    log.info("supply_chain_os_shutting_down")
    try:
        from app.services.kafka_producer import flush_producer
        flush_producer()
    except Exception:
        pass


# ── HEALTH ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["monitoring"])
async def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}


# ── ADMIN ENDPOINTS ───────────────────────────────────────────────────────────
@app.get(f"{settings.API_V1_STR}/admin/seed-graph", tags=["admin"])
async def admin_seed_graph():
    """
    Manually triggers a full wipe + rebuild of the Neo4j supplier graph.
    Use this when Neo4j was offline at startup and you need to seed without
    restarting the server.
    """
    try:
        from app.services.graph_seeder import seed_supply_graph
        seed_supply_graph()
        return {"status": "seeded", "message": "Neo4j graph rebuilt successfully."}
    except Exception as e:
        log.error("admin_seed_graph_failed", error=str(e))
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.BACKEND_PORT, reload=True)
