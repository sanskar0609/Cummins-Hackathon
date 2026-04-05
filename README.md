# Cummins Hackathon

This repository contains a multi-service supply chain intelligence platform with a frontend, backend API, data services, and supporting infrastructure for local development through Docker Compose.

## What Has Been Done So Far

The project has been pulled locally and prepared for local Docker-based development.

Completed setup steps:

- Cloned the repository into `Cummins-Hackathon`
- Confirmed Docker and Docker Compose are installed and available
- Added both required environment files:
  - root `.env`
  - `backend/.env`
- Validated the Docker Compose configuration
- Built the local application images for:
  - `frontend`
  - `backend`
- Pulled required infrastructure images
- Resolved interrupted Docker startup conflicts caused by partially created containers and networks
- Started the full stack successfully with Docker Compose

## Current Local Status

At the time of this README update, the full Docker stack has been started successfully.

Running services and ports:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Airflow UI: `http://localhost:8085`
- MLflow: `http://localhost:5000`
- Neo4j Browser: `http://localhost:7474`
- Neo4j Bolt: `localhost:7687`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- Kafka: `localhost:9092`
- Zookeeper: `localhost:2181`

## Project Structure

Top-level folders in this repository:

- `frontend/` - client application and Docker build for the UI
- `backend/` - FastAPI-based backend and application services
- `backend/airflow/` - Airflow DAGs and related orchestration files
- `data/` - raw and processed project data
- `infra/` - infrastructure-related assets
- `ingestion/` - ingestion pipelines and related workflows
- `ml/` - machine learning assets and related logic
- `reports/` - reporting outputs and project reports
- `agents/` - agent-related project assets

Important root files:

- `.env.example` - reference environment template
- `.env` - local environment configuration
- `docker-compose.yml` - primary service orchestration
- `docker-compose.override.yml` - local development overrides
- `Makefile` - helper commands for local development

## Environment Files

This project currently expects two local environment files:

1. Root environment file:
   - `.env`
2. Backend environment file:
   - `backend/.env`

Notes:

- Both files are now present locally
- The backend service reads `backend/.env` through Docker Compose
- The root `.env` is useful as the central local reference and project-level config source
- Do not commit private keys, tokens, or passwords to version control

## Docker Setup

### Services Defined in Compose

The Compose stack includes these services:

- `frontend`
- `backend`
- `postgres`
- `redis`
- `neo4j`
- `zookeeper`
- `kafka`
- `mlflow`
- `airflow-scheduler`

### Docker Files Used

- `frontend/Dockerfile`
- `backend/Dockerfile`
- `docker-compose.yml`
- `docker-compose.override.yml`

### Commands Used During Setup

Useful commands that were used or validated during setup:

```powershell
docker --version
docker compose version
docker compose config
docker compose up -d --build
docker compose down --remove-orphans
docker compose ps
docker compose logs --tail 50 backend
docker compose logs --tail 50 frontend
docker compose logs --tail 50 airflow-scheduler
```

### Why the First Docker Startup Took So Long

The first full startup was slow because:

- several large images had to be downloaded
- application images had to be built locally
- backend image installation includes Python and system packages
- frontend image runs `npm ci` and builds the production bundle
- interrupted runs left behind partially created Docker resources that had to be cleaned up

Large images involved include services such as:

- Apache Airflow
- Kafka
- Zookeeper
- Neo4j
- PostgreSQL
- Redis
- Python base image
- Node and NGINX for the frontend build

After the initial pull/build, future startups should usually be much faster.

## Problem Resolved During Setup

A Docker conflict occurred because earlier interrupted runs had already created some Compose resources.

Observed issues:

- existing Compose network with the same name
- containers stuck in `Created` state
- container name conflict for `cummins-hackathon-airflow-scheduler-1`

Resolution used:

```powershell
docker compose down --remove-orphans
docker compose up -d
```

This cleanup removed the stopped or partial Compose resources without deleting volumes.

## How To Run The Project Again

From the project root:

```powershell
docker compose up -d
```

To verify running services:

```powershell
docker compose ps
```

To stop the stack:

```powershell
docker compose down
```

To stop and remove volumes as well:

```powershell
docker compose down --volumes --remove-orphans
```

Use the last command carefully because it removes persisted local Docker data.

## Helpful Makefile Commands

This repository includes a `Makefile` with convenience targets:

- `make copy-env`
- `make validate`
- `make up`
- `make down`
- `make logs`
- `make ps`
- `make infra`
- `make clean`

Equivalent intentions:

- `copy-env` creates `.env` from `.env.example` if it does not exist
- `validate` checks Compose syntax
- `up` starts all services
- `down` stops services
- `logs` tails logs
- `ps` shows container status
- `infra` starts infra-only services
- `clean` removes containers and volumes

## Access Points

Open these URLs locally after startup:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Airflow: `http://localhost:8085`
- MLflow: `http://localhost:5000`
- Neo4j Browser: `http://localhost:7474`

## Known Notes

- `docker-compose.yml` still contains the deprecated `version:` field
- Docker Compose currently ignores that field, so it does not block startup
- It can be removed later to eliminate the warning message

## Recommended Next Steps

- verify the frontend loads correctly in the browser
- confirm backend API routes respond as expected
- test Neo4j, Airflow, and MLflow access
- document important API endpoints
- add a safe sample env template that avoids exposing real secrets
- remove deprecated Docker Compose `version:` usage

## Quick Start

```powershell
docker compose up -d
docker compose ps
```

Then open:

- `http://localhost:5173`
- `http://localhost:8000`
- `http://localhost:8085`
- `http://localhost:5000`
- `http://localhost:7474`
