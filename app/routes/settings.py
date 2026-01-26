
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Optional, Any
from app.database import get_merged_config, set_app_config
import json

router = APIRouter()

class TimePreset(BaseModel):
    start: str
    end: str

class ConfigModel(BaseModel):
    threshold_early: str
    threshold_late: str
    threshold_critical: str
    outlier_min: str
    outlier_max: str
    ignore_outliers: str # Using str "true"/"false" to match DB text storage
    time_presets: Optional[Dict[str, TimePreset]] = None

@router.get("/api/v1/settings")
async def get_settings():
    """
    Returns current configuration (DB + Defaults).
    """
    config = get_merged_config()
    
    # Parse nested JSON strings for the API response
    if 'time_presets' in config and isinstance(config['time_presets'], str):
        try:
            config['time_presets'] = json.loads(config['time_presets'])
        except:
            config['time_presets'] = None
            
    return config

@router.post("/api/v1/settings")
async def save_settings(config: ConfigModel):
    """
    Updates configuration.
    """
    config_dict = config.dict()
    
    # Ensure time_presets is properly serialized if it exists?
    # database.py `set_app_config` handles dict serialization using json.dumps
    # So we can pass the dict as is, BUT `config.dict()` converts sub-models to dicts automatically.
    # The DB expects keys: values. 
    # Important: `set_app_config` expects a dict of {key: value}.
    # If users send `true` (bool) for ignore_outliers, pydantic might convert/validate. 
    # Our DB stores everything as strings currently (VARCHAR).
    
    # Let's clean up the dict for storage
    storage_dict = {}
    for k, v in config_dict.items():
        if v is None:
            continue
            
        if k == 'time_presets':
            # This is a dict, set_app_config will serialize it.
            # However, our Pydantic model produces a Dict structure.
            storage_dict[k] = v
        else:
            # Cast everything else to string to match legacy key-value storage
            storage_dict[k] = str(v).lower() if isinstance(v, bool) else str(v)

    set_app_config(storage_dict)
    
    return {"status": "success", "config": storage_dict}
