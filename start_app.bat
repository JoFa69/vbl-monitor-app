
@echo off
echo Starting VBL Monitor (Headless Mode)...

echo Starting Backend (Port 8081)...
start "VBL Backend" cmd /k "python -m uvicorn app.main:app --reload --port 8081"

echo Starting Frontend (Port 5173)...
cd frontend
start "VBL Frontend" cmd /k "npm run dev"

echo Done. Backend runs on http://localhost:8081/api/stats
echo Frontend runs on http://localhost:5173
