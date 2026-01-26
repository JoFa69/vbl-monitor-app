from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.routes import dashboard
import shutil
import os

app = FastAPI(title="VBL Monitor API", version="0.2.0")

# CORS Configuration
origins = [
    "http://localhost:5173",  # React Frontend (Vite)
    "http://localhost:5174",  # React Frontend (Fallback port)
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routes import dashboard, settings

# Include Routers
app.include_router(dashboard.router)
app.include_router(settings.router)

from app.database import get_app_config, set_app_config, get_merged_config, conn, TABLE_NAME

# View routes removed in favor of JSON API


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
    
    # Handle checkboxes: if generic checkboxes are unchecked, they are missing from form data
    # We explicitly check for known checkboxes
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
    # Expected fields: morning_start, morning_end, evening_start, evening_end
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
        
        # Cleanup individual fields if they were added to new_config loop above
        # (The loop above adds everything from form_data, so we should allow that or clean up. 
        # database.py handles extra keys fine, but keeping config clean is better. 
        # But set_app_config takes a dict and saves all keys. 
        # Let's remove them from new_config to avoid cluttering config.json with flat keys)
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
        # Determine path
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        target_path = os.path.join(base_dir, 'data', 'Ferien_Feiertage.csv')
        
        # Save file
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {"message": "Calendar data updated successfully. Changes will be reflected in next request."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files (future proofing, though we use CDN for Pico)
# Static files removed (API Internal Only)

if __name__ == "__main__":
    import uvicorn
    # Using port 8081 to avoid conflicts with common ports or restricted ranges
    uvicorn.run("app.main:app", host="0.0.0.0", port=8081, reload=True)
