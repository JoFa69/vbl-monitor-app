from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import shutil
import os
import sys
import logging

# Logger konfigurieren, damit wir Fehler im Render-Log sehen
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print(">>> PYTHON VERSION:", sys.version)

# Importiere _init_db explizit, damit wir es kontrolliert starten können
from app.database import (
    get_app_config, 
    set_app_config, 
    get_merged_config, 
    conn, 
    TABLE_NAME, 
    _init_db  # <--- Stelle sicher, dass _init_db in database.py verfügbar ist!
)
from app.routes import dashboard, settings

# --- LIFESPAN MANAGER (DER FIX FÜR RENDER) ---
# Das verhindert, dass die App beim Start einfriert, während sie auf die Datenbank wartet.
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(">>> STARTUP: Starte Datenbank-Verbindung...")
    try:
        _init_db()  # Hier wird die Verbindung erst aufgebaut
        logger.info(">>> STARTUP: Verbindung erfolgreich!")
    except Exception as e:
        logger.error(f">>> STARTUP FEHLER: {e}")
        import traceback
        traceback.print_exc()
    
    yield  # Hier läuft die App und nimmt Anfragen entgegen
    
    logger.info(">>> SHUTDOWN: App wird beendet.")

# App Initialisierung mit Lifespan
app = FastAPI(title="VBL Monitor API", version="0.2.0", lifespan=lifespan)

# CORS Configuration
origins = [
    "http://localhost:5173",  # React Frontend (Vite)
    "http://localhost:5174",  # React Frontend (Fallback port)
    "http://localhost:3000",
    # Falls du später eine Frontend-URL bei Render hast, füge sie hier hinzu:
    # "https://dein-frontend-name.onrender.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(dashboard.router)
app.include_router(settings.router)

# --- API ROUTES ---

@app.get("/api/config")
async def get_config():
    """
    Returns current configuration (DB + Defaults).
    """
    return get_merged_config()

@app.post("/api/config")
async def update_config(request: Request):
    """
    Updates configuration from form data.
    """
    new_config = {}
    
    # Handle checkboxes
    form_data = await request.form()
    data_dict = dict(form_data)
    if 'ignore_outliers' not in data_dict:
        data_dict['ignore_outliers'] = 'false'
    
    for k, v in data_dict.items():
        val = str(v)
        # Convert minutes to seconds for storage (outliers only)
        if k in ['outlier_min', 'outlier_max']:
            try:
                # Input (min) -> Output (sec)
                val = str(int(float(val) * 60))
            except ValueError:
                pass
        
        new_config[k] = val
    
    # Handle time_presets nested structure
    if 'morning_start' in data_dict:
        presets = {
            "morning": {
                "start": data_dict.get('morning_start'),
                "end": data_dict.get('morning_end')
            },
            "evening": {
                "start": data_dict.get('evening_start'),
                "end": data_dict.get('evening_end')
            }
        }
        new_config['time_presets'] = presets
        
        # Cleanup individual fields
        for k in ['morning_start', 'morning_end', 'evening_start', 'evening_end']:
            if k in new_config:
                del new_config[k]

    # Save to DB (and disk)
    set_app_config(new_config)
    
    return {"status": "OK", "message": "Konfiguration gespeichert", "config": new_config}

@app.post("/api/upload-calendar")
async def upload_calendar(file: UploadFile = File(...)):
    """
    Uploads a new calendar CSV file (Ferien_Feiertage.csv).
    """
    try:
        # Determine path safely
        # Wir nutzen os.getcwd(), was bei Render oft sicherer ist
        base_dir = os.getcwd() 
        # Fallback falls data Ordner nicht existiert
        data_dir = os.path.join(base_dir, 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            
        target_path = os.path.join(data_dir, 'Ferien_Feiertage.csv')
        
        # Save file
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {"message": "Calendar data updated successfully. Changes will be reflected in next request."}
    except Exception as e:
        logger.error(f"Upload Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Local development settings
    uvicorn.run("app.main:app", host="0.0.0.0", port=8081, reload=True)
