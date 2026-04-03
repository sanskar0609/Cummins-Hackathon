FROM python:3.11-slim

# System dependencies mapping essential C/C++ libraries for the local LangGraph AI
# computations and specifically GTK-3 mapping for WeasyPrint execution natively in Docker.
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-cffi \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Optimize layer caching for requirement dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Persist volumes internally
RUN mkdir -p /app/data/reports

COPY . .

# Run Uvicorn asynchronously with host exposed exclusively to Docker internal
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
