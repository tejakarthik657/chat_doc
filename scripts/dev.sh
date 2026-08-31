#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Development startup script - runs all services locally (without Docker)
# Usage: bash scripts/dev.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "RAG Backend - Production Setup (Local Development)"
echo "═══════════════════════════════════════════════════════════════════════════════"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ── Check prerequisites ───────────────────────────────────────────────────────
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.11+${NC}"
    exit 1
fi

# Check Redis
if ! command -v redis-cli &> /dev/null; then
    echo -e "${YELLOW}⚠️  Redis not found. Installing via Homebrew (macOS) or apt (Linux)...${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install redis
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install redis-server
    fi
fi

# Check MongoDB (optional, can use local or cloud)
if ! command -v mongod &> /dev/null; then
    echo -e "${YELLOW}⚠️  MongoDB not found locally. Make sure it's running (use Docker or MongoDB Atlas)${NC}"
fi

echo -e "${GREEN}✓ Prerequisites OK${NC}\n"

# ── Setup Python environment ──────────────────────────────────────────────────
if [ ! -d "rag-backend/.venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    cd rag-backend
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
    cd ..
else
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
    source rag-backend/.venv/bin/activate
fi

# ── Start Redis in background (if not running) ────────────────────────────────
if ! redis-cli ping > /dev/null 2>&1; then
    echo -e "${YELLOW}Starting Redis server...${NC}"
    redis-server --daemonize yes --logfile ~/.redis/redis.log
    sleep 2
fi
echo -e "${GREEN}✓ Redis running${NC}\n"

# ── Start services ────────────────────────────────────────────────────────────
echo -e "${YELLOW}Starting services...${NC}\n"

# Terminal 1: FastAPI backend
echo -e "${YELLOW}[1/3] Starting FastAPI backend (port 8000)...${NC}"
cd rag-backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..
sleep 3

# Terminal 2: Celery worker (background task processing)
echo -e "${YELLOW}[2/3] Starting Celery worker...${NC}"
cd rag-backend
celery -A app.celery_app worker --loglevel=info --concurrency=2 &
WORKER_PID=$!
cd ..
sleep 3

# Terminal 3: Celery Beat (scheduled tasks)
echo -e "${YELLOW}[3/3] Starting Celery Beat...${NC}"
cd rag-backend
celery -A app.celery_app beat --loglevel=info &
BEAT_PID=$!
cd ..
sleep 3

echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ All services started!${NC}"
echo ""
echo "  Backend:  http://localhost:8000/docs"
echo "  Celery:   Running workers..."
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Trap Ctrl+C to gracefully shutdown
trap "kill $BACKEND_PID $WORKER_PID $BEAT_PID 2>/dev/null; echo 'Services stopped.'" EXIT

# Keep script running
wait
