@echo off
REM Run project indexing manually
set KMP_DUPLICATE_LIB_OK=TRUE
echo [SYSTEM] Starting indexing for Project: %1, User: %2...
cd rag-backend
.venv311\Scripts\python scripts\reingest_project.py %1 %2
echo [SYSTEM] Indexing completed.
pause
