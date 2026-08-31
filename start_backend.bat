@echo off
echo Starting RAG Backend Server...
cd rag-backend
.venv311\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
