# 🚀 Supply Chain Intelligence OS — Complete Free Deployment Guide

> **Stack:** React (Vite) + FastAPI (Python) + PostgreSQL + Redis + Neo4j + Kafka + MLFlow + AI Agents + ML Models
> **Goal:** Deploy everything for free with all services working correctly.

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Understanding What Needs Deploying](#understanding-what-needs-deploying)
3. [Free Deployment Strategy](#free-deployment-strategy)
4. [Step 1 — Get Free API Keys](#step-1--get-free-api-keys)
5. [Step 2 — Free Cloud Databases](#step-2--free-cloud-databases)
6. [Step 3 — Deploy Backend (Render.com)](#step-3--deploy-backend-rendercom)
7. [Step 4 — Deploy Frontend (Vercel)](#step-4--deploy-frontend-vercel)
8. [Step 5 — Agents Deployment](#step-5--agents-deployment)
9. [Step 6 — ML Models Deployment](#step-6--ml-models-deployment)
10. [Step 7 — Ingestion Pipeline Deployment](#step-7--ingestion-pipeline-deployment)
11. [Step 8 — Configure Environment Variables](#step-8--configure-environment-variables)
12. [Step 9 — Run DB Migrations](#step-9--run-db-migrations)
13. [Step 10 — Verify Everything Works](#step-10--verify-everything-works)
14. [Troubleshooting](#troubleshooting)
15. [Local Docker (Alternative)](#local-docker-alternative)

---

## 🏗️ Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    FREE CLOUD DEPLOYMENT                         │
│                                                                  │
│  ┌──────────┐   ┌──────────────────────────────────────────┐   │
│  │  Vercel  │──►│           Render.com                     │   │
│  │ (React)  │   │  ┌─────────┐ ┌─────────┐ ┌──────────┐  │   │
│  │  FREE    │   │  │ FastAPI │ │ Agents  │ │ ML Models│  │   │
│  └──────────┘   │  │ Backend │ │ (built- │ │(built-in │  │   │
│                 │  │         │ │  in)    │ │ FastAPI) │  │   │
│                 │  └────┬────┘ └────┬────┘ └────┬─────┘  │   │
│                 └───────┼───────────┼────────────┼─────────┘   │
│                         │           │            │              │
│         ┌───────────────┼───────────┼────────────┼───────┐     │
│         │               │           │            │       │     │
│  ┌──────▼──┐  ┌────────▼─┐  ┌─────▼──┐  ┌─────▼──┐    │     │
│  │ Neon    │  │  Redis   │  │ Neo4j  │  │Upstash │    │     │
│  │(Postgres│  │  Cloud   │  │ AuraDB │  │ Kafka  │    │     │
│  │  FREE   │  │  FREE    │  │  FREE  │  │  FREE  │    │     │
│  └─────────┘  └──────────┘  └────────┘  └────────┘    │     │
└──────────────────────────────────────────────────────────────────┘

Ingestion Pipeline → runs INSIDE the Backend (Kafka consumers auto-start)
AI Agents         → run INSIDE the Backend (called via API endpoints)
ML Models         → run INSIDE the Backend (Prophet, LSTM, scikit-learn)
```

---

## 🧠 Understanding What Needs Deploying

This is the most important section. Your project has **4 code areas**:

| Directory | What It Is | How It Deploys |
|-----------|-----------|----------------|
| `frontend/` | React + Vite UI | ✅ **Vercel** (separate) |
| `backend/` | FastAPI server | ✅ **Render.com** (separate) |
| `agents/` | AI agents (Gemini + Groq powered) | ⚙️ **Called from backend services** |
| `ml/` | ML models (Prophet, LSTM, scikit-learn) | ⚙️ **Run inside backend on startup** |
| `ingestion/` | Kafka consumers + Airflow DAGs | ⚙️ **Kafka: Upstash / Airflow: skip for demo** |

### 🔑 Key Insight

> **You do NOT need to deploy `agents/`, `ml/`, or `ingestion/` separately.**
>
> Here's why:
> - Your `agents/demand_agent.py` is called from **backend API endpoints** (LangGraph/LangChain pipeline inside FastAPI)
> - Your `ml/` models (Prophet, LSTM, scikit-learn) are already loaded in `backend/app/services/ml_demand_forecaster.py`, `ml_chokepoint_scorer.py`, etc.
> - Your `ingestion/` Kafka consumers run as background tasks started by the backend
>
> **Everything runs inside the single Render.com backend service.** ✅

---

## 🆓 Free Deployment Strategy

| Platform | What it hosts | Free Limit |
|----------|--------------|------------|
| **Vercel** | React Frontend | Unlimited (hobby) |
| **Render.com** | FastAPI + Agents + ML | 750 hrs/month |
| **Neon.tech** | PostgreSQL | 0.5 GB, 10 projects |
| **Redis Cloud** | Redis Cache | 30 MB |
| **Neo4j AuraDB** | Graph Database | 1 Free instance |
| **Upstash** | Kafka Streaming | 10K msg/day free |
| **Gemini API** | AI inference (Agents) | 1M tokens/day FREE |
| **Groq API** | Fast LLM (Agents) | 14K tokens/min FREE |

> ⚠️ **Render free tier sleeps after 15 minutes of inactivity.** First request takes ~30 seconds. Fine for demos.

---

## Step 1 — Get Free API Keys

### 🔑 Required Keys

1. **Google Gemini API Key** — used by `demand_agent.py` and all AI agents
   - Go to: https://aistudio.google.com/
   - Click "Get API Key" → Create → Copy key
   - `GEMINI_API_KEY=AIza...`

2. **Groq API Key** — fallback LLM for agents when Gemini quota hits
   - Go to: https://console.groq.com/
   - Sign up → API Keys → Create new
   - `GROQ_API_KEY=gsk_...`

### 🗺️ Optional Keys (for full features)

3. **Mapbox Token** — for supply chain map
   - https://account.mapbox.com/ → Tokens → Default public token
   - `VITE_MAPBOX_TOKEN=pk.eyJ...`

4. **NewsAPI Key** — used by `demand_agent.py` to fetch news signals
   - https://newsapi.org/ → Register → API Key
   - `NEWS_API_KEY=...`

5. **YouTube API Key** — used by `demand_agent.py` for demand sensing
   - https://console.cloud.google.com/ → Enable YouTube Data API v3 → Create credentials
   - `YOUTUBE_API_KEY=AIza...`

6. **AISStream API Key** — for live vessel tracking
   - https://aisstream.io/ → Sign up → Get key
   - `AISSTREAM_API_KEY=...` (optional, skip for demo)

---

## Step 2 — Free Cloud Databases

### 🐘 PostgreSQL — Neon.tech (FREE)

1. Go to **https://neon.tech** → Sign Up (use GitHub)
2. Click **"New Project"** → Name: `supply-chain`
3. Region: **AWS US East** (or nearest)
4. Copy the **Connection String**:
   ```
   postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/supply_chain?sslmode=require
   ```
5. Save as `DATABASE_URL`

### 🔴 Redis — Redis Cloud (FREE)

1. Go to **https://redis.cloud** → Sign Up
2. Click **"New Database"** → Choose **Free** plan (30 MB)
3. Go to your database → **Configuration** tab
4. Copy **Public endpoint** + **Password**
5. Build: `REDIS_URL=redis://:PASSWORD@HOST:PORT`

### 🔗 Neo4j — AuraDB Free

1. Go to **https://neo4j.com/cloud/platform/aura-graph-database/**
2. **"Start Free"** → Sign Up → Create Free instance
3. ⚠️ **Download the credentials file** (shown only ONCE at creation!)
4. Save:
   - `NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io`  ← must be `neo4j+s://` not `bolt://`
   - `NEO4J_USER=neo4j`
   - `NEO4J_PASSWORD=` (from downloaded file)

### ⚡ Kafka — Upstash (FREE)

1. Go to **https://upstash.com** → Sign Up
2. **Kafka** tab → **Create Cluster** → Name: `supply-chain`
3. Copy:
   - **Bootstrap Server**: `xxx.upstash.io:9092`
   - **SASL Username** and **SASL Password**
4. Create these topics in Upstash console:
   - `ais-feed`
   - `flight-feed`
   - `geo-events`

---

## Step 3 — Deploy Backend (Render.com)

The backend **includes the agents and ML** — they are services called from within FastAPI.

### 3.1 Push Code to GitHub

```bash
git add .
git commit -m "Prepare for deployment"
git push origin main
```

### 3.2 Create Render Web Service

1. Go to **https://render.com** → Sign Up with GitHub
2. Click **"New +"** → **"Web Service"**
3. Connect your `Cummins-Hackathon` repository
4. Configure:

   | Setting | Value |
   |---------|-------|
   | **Name** | `supply-chain-backend` |
   | **Region** | Oregon (US West) |
   | **Branch** | `main` |
   | **Root Directory** | `backend` |
   | **Runtime** | `Python 3` |
   | **Build Command** | `pip install --upgrade pip && pip install -r requirements.txt` |
   | **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | **Instance Type** | **Free** |

5. Add environment variables (see Step 8)
6. Click **"Create Web Service"**
7. Wait ~5-10 minutes for the first build

### 3.3 What Happens on Backend Startup

When Render starts your backend, `app/main.py` automatically:

```
✅ Connects to Neon PostgreSQL
✅ Connects to Redis Cloud
✅ Seeds Neo4j graph (graph_seeder.py runs on startup)
✅ Runs Prophet demand forecasts (ml_demand_forecaster.py runs on startup)
✅ Starts Kafka producers (for live data publishing)
```

All this happens **automatically** — no extra steps needed.

### 3.4 Verify Backend

Open: `https://supply-chain-backend.onrender.com/docs`
You should see the **FastAPI Swagger UI**.

---

## Step 4 — Deploy Frontend (Vercel)

1. Go to **https://vercel.com** → Sign Up with GitHub
2. Click **"New Project"** → Import `Cummins-Hackathon`
3. Configure:

   | Setting | Value |
   |---------|-------|
   | **Framework Preset** | Vite |
   | **Root Directory** | `frontend` |
   | **Build Command** | `npm run build` |
   | **Output Directory** | `dist` |
   | **Install Command** | `npm install` |

4. Add Environment Variables:

   | Key | Value |
   |-----|-------|
   | `VITE_API_BASE_URL` | `https://supply-chain-backend.onrender.com/api/v1` |
   | `VITE_WS_URL` | `wss://supply-chain-backend.onrender.com/api/v1` |
   | `VITE_MAPBOX_TOKEN` | `your_mapbox_token` |

5. Click **"Deploy"** → Done in ~2 minutes

Your frontend: `https://supply-chain-os.vercel.app`

---

## Step 5 — Agents Deployment

### How Your Agents Work

```
agents/
├── demand_agent.py        ← Standalone script + called via backend API
├── alert_agent/           ← Placeholder (empty, not deployed separately)
├── copilot/               ← Placeholder (empty, not deployed separately)
└── po_agent/              ← Placeholder (empty, not deployed separately)
```

### `demand_agent.py` — The Core AI Agent

This is a **Python script with a 5-step LangGraph-style pipeline**:
1. **Parse Query** → Gemini extracts structured params from natural language
2. **Fetch Sources** → Parallel calls to YouTube, NewsAPI, Reddit, Google Trends
3. **Filter & Tag** → Groq LLM filters relevant signals (demand/disruption/sentiment)
4. **Predict Requirements** → Mathematical model computes demand units + confidence
5. **Generate Insights** → Gemini writes 3 strategic recommendations

### Deployment: Agents Are Called From Backend

The agent logic is **already wired into your backend services** (`backend/app/services/`). When a user hits the demand-sensing API endpoint, the backend internally runs the agent pipeline.

**For hackathon demo — run the agent locally too:**

```bash
# From project root
cd agents
pip install google-generativeai aiohttp python-dotenv groq pytrends

# Set keys in .env (already done if .env is configured)

# Run the demand agent standalone:
python demand_agent.py
```

### If You Want Agents as a Separate Microservice (Optional)

Deploy `agents/` as its own Render service:

1. Create a `agents/requirements.txt`:
   ```
   google-generativeai>=0.5.0
   aiohttp>=3.9.0
   python-dotenv>=1.0.1
   groq>=0.4.0
   pytrends>=4.9.2
   fastapi[standard]>=0.110.0
   uvicorn>=0.29.0
   ```

2. Create `agents/main.py`:
   ```python
   from fastapi import FastAPI
   from demand_agent import run_pipeline
   import asyncio

   app = FastAPI(title="Demand Agent Service")

   @app.post("/demand/analyze")
   async def analyze_demand(query: str, baseline_units: int = 1000):
       result = await run_pipeline(query, baseline_units)
       return result

   @app.get("/health")
   def health():
       return {"status": "ok", "service": "demand-agent"}
   ```

3. Create a **second Render service** with:
   - Root Directory: `agents`
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`

---

## Step 6 — ML Models Deployment

### How Your ML Models Work

```
ml/
├── demand_forecast/   ← Prophet time series (placeholder folder)
├── lstm/              ← LSTM neural net (placeholder folder)
├── chokepoint/        ← Chokepoint scoring (placeholder folder)
├── mlflow/            ← Experiment tracking (placeholder folder)
├── nlp/               ← NLP processing (placeholder folder)
└── risk_engine/       ← Risk scoring (placeholder folder)

# The ACTUAL model code lives in:
backend/app/services/
├── ml_demand_forecaster.py   ← Prophet model (runs on backend startup)
├── ml_chokepoint_scorer.py   ← Chokepoint ML scoring
├── ml_lstm_route.py          ← LSTM route risk
├── ml_geo_scorer.py          ← Geographic risk scoring
└── monte_carlo.py            ← Monte Carlo simulation
```

### Deployment: ML Runs INSIDE the Backend ✅

**All ML models are already deployed** when you deploy the backend to Render.

At startup, `app/main.py` calls:
```python
from app.services.ml_demand_forecaster import generate_and_store_forecasts
generate_and_store_forecasts()   # ← Prophet runs here automatically
```

### MLflow Tracking (Optional)

MLflow is **not deployed to the cloud** (too heavy for free tier). Instead it uses SQLite:

```env
# In your backend env vars:
MLFLOW_TRACKING_URI=sqlite:///mlflow.db
```

This stores experiment data locally on Render's disk. It resets on each deploy, which is fine for hackathon demos.

To view MLflow locally:
```bash
cd backend
mlflow ui --port 5001
# Open http://localhost:5001
```

### If Render Build Fails Due to ML Dependencies

Some ML packages (`prophet`, `scikit-learn`) can fail to build. Add a `runtime.txt` in the `backend/` directory:

```
python-3.11.0
```

And update the build command in Render:
```
pip install --upgrade pip setuptools wheel && pip install -r requirements.txt
```

---

## Step 7 — Ingestion Pipeline Deployment

### What Your Ingestion Pipeline Does

```
ingestion/
├── kafka/
│   └── consumers/     ← Kafka consumers (placeholder)
├── airflow/
│   └── dags/          ← Airflow DAG definitions (placeholder)
└── flink/             ← Flink stream processing (placeholder)

# The ACTUAL ingestion code lives in:
backend/app/services/
├── kafka_consumer.py  ← Reads from Kafka topics
├── kafka_producer.py  ← Publishes to Kafka topics
├── ais_stream.py      ← Live vessel AIS data
├── opensky_ingest.py  ← Flight tracking data
└── geo_ingest.py      ← Geographic event ingestion
```

### Deployment Options

#### Option A: Kafka Consumers Run Inside Backend (Recommended for Demo)

Your `kafka_consumer.py` is called by the backend. Upstash Kafka handles the broker.

**No separate deployment needed** — it works with Upstash via environment variables.

#### Option B: Airflow — Skip for Hackathon

Airflow requires significant resources (2+ GB RAM). **Skip it for the hackathon demo.**

The scheduled data pipeline jobs are unnecessary for a demo — just seed data manually:
```bash
# Via Render Shell
python -c "from app.services.geo_ingest import seed_geo_data; seed_geo_data()"
```

To run Airflow locally only:
```bash
# Uses Docker Compose (local only)
docker compose up airflow-scheduler -d
# Visit http://localhost:8085  (admin/admin)
```

#### Option C: Separate Ingestion Worker on Render (Optional)

If you want Kafka consumers running as a persistent background worker:

1. In Render: **"New +"** → **"Background Worker"**
2. Configure:
   - Root Directory: `backend`
   - Build: `pip install -r requirements.txt`
   - Start Command: `python -m app.services.kafka_consumer`
3. Add same environment variables as the main backend

---

## Step 8 — Configure Environment Variables

### Backend — Set in Render Dashboard

Go to Render → your service → **Environment** tab:

```env
# ── DATABASES ─────────────────────────────────────────────────────
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/supply_chain?sslmode=require
REDIS_URL=redis://:your_password@redis-xxx.redns.redis-cloud.com:12345

# ── GRAPH DB ──────────────────────────────────────────────────────
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# ── KAFKA (Upstash) ───────────────────────────────────────────────
KAFKA_BOOTSTRAP_SERVERS=your-cluster.upstash.io:9092
KAFKA_SASL_USERNAME=your_upstash_username
KAFKA_SASL_PASSWORD=your_upstash_password
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=SCRAM-SHA-256
KAFKA_TOPIC_AIS=ais-feed
KAFKA_TOPIC_FLIGHT=flight-feed
KAFKA_TOPIC_GEO_EVENTS=geo-events

# ── AI AGENTS (Required for demand_agent.py) ──────────────────────
GEMINI_API_KEY=your_gemini_key
GEMINI_API_KEY_2=optional_second_key      # Agent rotates if quota hit
GROQ_API_KEY=your_groq_key
GROQ_API_KEY_2=optional_second_key       # Agent rotates if quota hit

# ── DATA APIs (used by demand_agent.py) ───────────────────────────
NEWS_API_KEY=your_newsapi_key
YOUTUBE_API_KEY=your_youtube_api_key
AISSTREAM_API_KEY=your_aisstream_key     # Skip if not using live AIS

# ── SECURITY ──────────────────────────────────────────────────────
SECRET_KEY=your_64_char_random_string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ── CORS (allow Vercel frontend) ──────────────────────────────────
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:5173

# ── ML / MLFLOW ───────────────────────────────────────────────────
MLFLOW_TRACKING_URI=sqlite:///mlflow.db
```

> 💡 **Generate SECRET_KEY**:
> ```python
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

### Frontend — Set in Vercel Dashboard

```env
VITE_API_BASE_URL=https://supply-chain-backend.onrender.com/api/v1
VITE_WS_URL=wss://supply-chain-backend.onrender.com/api/v1
VITE_MAPBOX_TOKEN=your_mapbox_token
```

---

## Step 9 — Run DB Migrations

### Via Render Shell (Easiest)

1. Render dashboard → your backend service → **Shell** tab
2. Run:
   ```bash
   alembic upgrade head
   ```

### Or Locally Pointing to Cloud

```bash
cd backend
# Edit backend/.env — set DATABASE_URL to Neon URL
alembic upgrade head
```

### Seed Initial Data

After migration, seed the Neo4j graph:
```bash
# Via Render Shell:
python -c "from app.services.graph_seeder import seed_supply_graph; seed_supply_graph()"

# Seed alerts:
python seed_alerts.py
```

---

## Step 10 — Verify Everything Works

### ✅ Full Checklist

**Core Infrastructure:**
- [ ] `GET https://your-backend.onrender.com/health` → `{"status": "ok"}`
- [ ] `https://your-backend.onrender.com/docs` → Swagger UI loads
- [ ] `https://your-app.vercel.app` → Frontend loads

**Database:**
- [ ] `GET /api/v1/suppliers` → returns data array (not 500)
- [ ] Neo4j graph seeded → check via `/api/v1/admin/seed-graph` endpoint

**AI Agents:**
- [ ] POST to demand analysis endpoint → Gemini/Groq responds with signals
- [ ] Check Render logs: should see `[GeminiRotator] Loaded X Gemini key(s)`

**ML Models:**
- [ ] Demand forecasts show in dashboard (seeded on startup)
- [ ] Check Render logs: should see `demand_forecasts_seeded_on_startup`

**Ingestion:**
- [ ] Kafka topics created in Upstash dashboard
- [ ] Backend logs show Kafka producer initialized (or graceful skip if disabled)

### 🔍 Where to Check Logs

| Service | Where to Look |
|---------|--------------|
| Backend/Agents/ML | Render → your service → **Logs** tab |
| Frontend | Browser → F12 → Console |
| Database | Neon console → **Monitoring** tab |
| Kafka | Upstash → **Messages** tab |
| Neo4j | Neo4j Aura console → **Queries** tab |

---

## 🔧 Troubleshooting

### ❌ Agent fails — "No Gemini keys configured"

Your `demand_agent.py` reads `GEMINI_API_KEY` from env. Make sure it's set in Render:
```
GEMINI_API_KEY=AIzaSy...
```

### ❌ ML startup fails — Prophet/scikit import error on Render

Add to top of your Render build command:
```
pip install --upgrade pip setuptools wheel && pip install -r requirements.txt
```
Or create `backend/runtime.txt`:
```
python-3.11.0
```

### ❌ Neo4j seed fails on startup

AuraDB uses SSL. Make sure `NEO4J_URI` starts with `neo4j+s://` (NOT `bolt://`):
```
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
```

The backend catches this error gracefully and logs `neo4j_seed_skipped_on_startup`. App still runs.

### ❌ Kafka connection fails (Upstash)

Upstash **requires SASL_SSL authentication**. Add to Render env vars:
```
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=SCRAM-SHA-256
```

If Kafka is still causing build issues, you can **disable Kafka** in `backend/app/main.py` for hackathon:
```python
# Comment out the Kafka imports/startup if not needed for demo
```

### ❌ Backend 500 on startup — DB not ready

Neon DB may take a few seconds to wake up. Render will retry. If it keeps failing:
```bash
# Via Render Shell — test connection:
python -c "
from sqlalchemy import create_engine, text
import os
e = create_engine(os.environ['DATABASE_URL'])
print(e.connect().execute(text('SELECT 1')).scalar())
"
```

### ❌ demand_agent.py — "pytrends" error

pytrends (Google Trends) can be rate-limited. If it fails, the agent still works with the other 3 sources (YouTube, NewsAPI, Reddit). No action needed.

### ❌ CORS error on frontend

Ensure `CORS_ORIGINS` in Render includes your **exact** Vercel URL:
```
CORS_ORIGINS=https://supply-chain-os-git-main-yourname.vercel.app,http://localhost:5173
```

---

## 🐳 Local Docker (Alternative — Run Everything Locally)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- At least 8 GB RAM (all services are heavy)

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/Cummins-Hackathon.git
cd Cummins-Hackathon

# 2. Copy and fill environment
cp .env.example .env
# Edit .env — fill in GEMINI_API_KEY, GROQ_API_KEY, MAPBOX_TOKEN etc.

# 3. Start all services (backend, frontend, postgres, redis, neo4j, kafka, mlflow, airflow)
docker compose up --build -d

# 4. Wait for healthy (~2-3 minutes)
docker compose ps

# 5. Run DB migrations
docker compose exec backend alembic upgrade head

# 6. Seed Neo4j graph
docker compose exec backend python -c "from app.services.graph_seeder import seed_supply_graph; seed_supply_graph()"

# 7. Run the demand agent standalone
cd agents
python demand_agent.py

# 8. Access everything
# Frontend:    http://localhost:5173
# Backend API: http://localhost:8000
# Swagger:     http://localhost:8000/docs
# Neo4j:       http://localhost:7474  (neo4j/admin123)
# MLFlow:      http://localhost:5000
# Airflow:     http://localhost:8085  (admin/admin)

# Stop everything:
docker compose down

# Stop + delete all data:
docker compose down -v
```

---

## 💰 Cost Summary

| Service | What's Hosted | Cost |
|---------|--------------|------|
| Vercel | React Frontend | **FREE** |
| Render.com | FastAPI + Agents + ML Models | **FREE** |
| Neon.tech | PostgreSQL | **FREE** |
| Redis Cloud | Redis Cache | **FREE** |
| Neo4j AuraDB | Graph DB + Supply Chain Graph | **FREE** |
| Upstash | Kafka (Ingestion pipeline) | **FREE** |
| Gemini API | Demand Agent AI | **FREE** |
| Groq API | Demand Agent fallback LLM | **FREE** |
| **TOTAL** | | **$0/month** |

---

## 📞 Quick Reference

| Resource | URL |
|----------|-----|
| 🌐 Frontend App | `https://your-app.vercel.app` |
| ⚙️ Backend + Agents + ML | `https://your-backend.onrender.com` |
| 📖 API Swagger Docs | `https://your-backend.onrender.com/docs` |
| 🗄️ Neon DB Console | https://console.neon.tech |
| 🔴 Redis Cloud | https://app.redislabs.com |
| 🔗 Neo4j AuraDB | https://console.neo4j.io |
| ⚡ Upstash Kafka | https://console.upstash.com |
| 🚀 Render Dashboard | https://dashboard.render.com |
| 🌍 Vercel Dashboard | https://vercel.com/dashboard |

---

## 🗺️ Deployment Decision Tree

```
Is this for a hackathon demo?
├── YES → Deploy backend + frontend only (Render + Vercel)
│         Agents & ML run automatically inside backend ✅
│         Skip Airflow (too heavy for free tier) ✅
│         Use Upstash for Kafka ✅
│
└── NO (production) →
    ├── Agents: Consider separate Render worker or AWS Lambda
    ├── ML Models: Consider HuggingFace Spaces or GCP Vertex AI
    ├── Airflow: Use Astronomer.io (free trial) or GCP Cloud Composer
    └── Kafka: Use Confluent Cloud (free 30-day trial)
```

---

*Generated for Cummins Hackathon — Supply Chain Intelligence OS*
