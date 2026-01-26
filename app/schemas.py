from pydantic import BaseModel
from typing import List, Optional, Any, Dict, Union

class TripData(BaseModel):
    id: str
    label: str
    vehicle: Optional[str] = None
    trip_start_time: Optional[str] = None

class HeatmapCell(BaseModel):
    stop_name: str
    # Common fields
    total: Optional[int] = 0
    
    # Aggregated fields
    time_slot: Optional[str] = None
    on_time: Optional[int] = 0
    early: Optional[int] = 0
    late_slight: Optional[int] = 0
    late_severe: Optional[int] = 0
    avg_delay: Optional[float] = 0.0
    p1: Optional[float] = 0.0
    p2: Optional[float] = 0.0
    p3: Optional[float] = 0.0
    p4: Optional[float] = 0.0
    p5: Optional[float] = 0.0

    # Trip View fields
    trip_id: Optional[str] = None
    delay: Optional[float] = 0.0
    status: Optional[str] = None

class TripInfo(BaseModel):
    id: str
    label: str
    vehicle: Optional[str] = None
    course: Optional[str] = None

class HeatmapResponse(BaseModel):
    # Shared Fields
    stops: Optional[List[str]] = None  # Optional because standard view puts stops inside data objects (redundant but existing) 
                                       # Actually standard view returns {stops: [], data: []} as per database.py line 1343
    
    # Standard View Field
    data: Optional[List[HeatmapCell]] = None
    
    # Trip View Fields (Matrix Mode)
    rows: Optional[List[str]] = None      # Y-Axis (Stops)
    x_labels: Optional[List[str]] = None  # X-Axis (Time)
    trip_infos: Optional[List[TripInfo]] = None
    grid: Optional[List[List[Optional[int]]]] = None # The Matrix
    
    error: Optional[str] = None

class DashboardMetadata(BaseModel):
    date_range: Dict[str, str]
    lines: Dict[str, List[Dict[str, Any]]]
    config: Dict[str, Any]
    time_presets: Dict[str, Any]
