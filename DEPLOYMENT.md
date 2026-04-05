# SupplyOS Deployment Guide

This document provides instructions on how to deploy the SupplyOS "Digital Twin" and Demand Sensing platform.

---

## 🏗 System Architecture
- **Frontend**: React 18, Vite, TailwindCSS, Cytoscape.js (Graph Engine).
- **Backend**: FastAPI (Python 3.10+), Uvicorn.
- **AI Engine**: Gemini 2.5 Flash / Groq (Llama 3).
- **Data Persistence**: SQLite (local) and CSV-based parsing.

---

## 🛠 Prerequisites
- **Node.js**: v18 or higher
- **Python**: v3.10 or higher
- **Package Managers**: `npm` and `pip`

---

## 📦 Local Setup & Development

### 1. Backend Setup
1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Initialize the database (if needed):
   ```bash
   python reset_db.py
   ```
4. Start the development server:
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### 2. Frontend Setup
1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

---

## 🌍 Environment Variables

You must configure the following `.env` files. **Do not commit these to a public repository.**

### Root/Backend `.env` (`/backend/.env`)
```env
# AI API Keys
GEMINI_API_KEY=your_gemini_key_here
GROQ_API_KEY=your_groq_key_here

# Market Sensing Keys
NEWS_API_KEY=your_newsapi_key_here

# Database
DATABASE_URL=sqlite:///./supply_chain.db
```

### Frontend `.env` (`/frontend/.env`)
```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_MAPBOX_TOKEN=your_mapbox_token_here
```

---

## 🚀 Production Deployment

### Option A: Manual Deployment (VPS/EC2)
1. **Frontend**: Build the static assets:
   ```bash
   cd frontend
   npm run build
   ```
   Deploy the `dist` folder to a CDN or host using Nginx/Apache.

2. **Backend**: Run with a production-grade server:
   ```bash
   cd backend
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
   ```

### Option B: Docker Deployment
The project includes a `docker-compose.yml` for unified deployment.
1. Build and start containers:
   ```bash
   docker-compose up --build -d
   ```

---

## 🧪 Verification
- **API Status**: Visit `http://localhost:8000/docs` for Swagger UI.
- **Frontend**: Visit `http://localhost:5173` (or your production URL).
- **Digital Twin**: Ensure `supply.csv` is uploaded to visualize the graph.
