
from fastapi import APIRouter, Request, Query, HTTPException
from app.database import (
    get_punctuality_stats, 
    get_lines,
    get_stats_by_time_slot,
    get_stats_by_weekday,
    get_problematic_stops,
    get_stops,
    debug_check_route,
    get_date_range,
    get_day_class_counts,
    get_merged_config,
    get_cancellation_stats,
    get_dwell_time_by_hour,
    get_worst_trips,
    get_heatmap_stats
)
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
from app.schemas import HeatmapResponse, DashboardMetadata

router = APIRouter()

@router.get("/api/dashboard-metadata", response_model=DashboardMetadata)
async def get_dashboard_metadata():
    """Returns initial metadata like date ranges, config, etc."""
    date_range = get_date_range()
    lines = get_lines()
    config = get_merged_config()
    
    # Parse time_presets if available
    time_presets = {}
    if 'time_presets' in config:
        try:
             if isinstance(config['time_presets'], str):
                 time_presets = json.loads(config['time_presets'])
             else:
                 time_presets = config['time_presets']
        except Exception:
            pass

    return {
        "date_range": date_range,
        "lines": lines,
        "config": config,
        "time_presets": time_presets
    }

@router.get("/api/stats")
async def get_stats_api(
    request: Request,
    date_from: str = Query(None, alias="from"),
    date_to: str = Query(None, alias="to"),
    time_from: str = Query(None, alias="time_from"),
    time_to: str = Query(None, alias="time_to"),
    routes: Optional[List[str]] = Query(None, alias="route"),
    stops: Optional[List[str]] = Query(None, alias="stop"),
    day_class: Optional[str] = Query(None, alias="day_class"),
    line: Optional[str] = Query(None, alias="line"),
    metric: str = Query("arrival")
):
    """
    HTMX endpoint to return just the stats partial.
    """
    # Default to data range if no date provided (though frontend usually sends it)
    if not date_from or not date_to:
        date_range = get_date_range()
        if not date_from: date_from = date_range['min']
        if not date_to: date_to = date_range['max']
        
    # Sanitize inputs
    if routes: routes = [r for r in routes if r]
    if stops: stops = [s for s in stops if s]
    if day_class == "": day_class = None
    if line == "": line = None

    stats = get_punctuality_stats(date_from, date_to, route_filter=routes, stop_filter=stops, day_class=day_class, line_filter=line, metric_type=metric, time_from=time_from, time_to=time_to)
    
    # Cancellation Stats needed for totals? If this is just stats card.
    # Let's align with the kpi-stats logic below to be unified or simple.
    # The pure 'get_stats' usually returned just the punctuality buckets. 
    # But let's return it as JSON data.
    
    return {
        "stats": stats,
        "filters": {
            "date_from": date_from, 
            "date_to": date_to,
            "metric": metric
        }
    }

@router.get("/api/components/kpi-stats")
async def get_kpi_stats(
    request: Request,
    date_from: str = Query(None, alias="from"),
    date_to: str = Query(None, alias="to"),
    time_from: str = Query(None, alias="time_from"),
    time_to: str = Query(None, alias="time_to"),
    routes: Optional[List[str]] = Query(None, alias="route"),
    stops: Optional[List[str]] = Query(None, alias="stop"),
    day_class: Optional[str] = Query(None, alias="day_class"),
    line: Optional[str] = Query(None, alias="line"),
    metric: str = Query("arrival")
):
    """
    Returns the KPI tiles fragment.
    """
    if not date_from or not date_to:
        date_range = get_date_range()
        if not date_from: date_from = date_range['min']
        if not date_to: date_to = date_range['max']
        
    # Sanitize inputs
    if routes: routes = [r for r in routes if r]
    if stops: stops = [s for s in stops if s]
    if day_class == "": day_class = None
    if line == "": line = None

    stats = get_punctuality_stats(date_from, date_to, route_filter=routes, stop_filter=stops, day_class=day_class, line_filter=line, metric_type=metric, time_from=time_from, time_to=time_to)
    
    # Cancellation Stats (Independent of metric? Usually yes, cancelled is cancelled)
    cancellation_stats = get_cancellation_stats(date_from, date_to, routes, stops, day_class, line)

    # 1. Calculate Grand Total (Real + Cancelled)
    real_total = stats.get('total', 0)
    cancelled_total = cancellation_stats.get('total_cancelled_trips', 0)
    grand_total = real_total + cancelled_total
    
    # 2. Update Total in Stats (so UI shows Sum)
    stats['total'] = grand_total
    
    # 3. Recalculate Percentages based on Grand Total
    percentages = {}
    if grand_total > 0:
        # Punctuality buckets
        percentages = {k: round((v / grand_total) * 100, 1) for k, v in stats.items() if k != 'total'}
        
        # Cancellation Rate (re-calculated to be consistent with grand total)
        cancellation_rate = round((cancelled_total / grand_total) * 100, 1)
        cancellation_stats['cancellation_rate'] = cancellation_rate
    else:
        cancellation_stats['cancellation_rate'] = 0.0

    config = get_merged_config()

    return {
        "stats": stats,
        "cancellation_stats": cancellation_stats,
        "percentages": percentages,
        "total": grand_total,
        "config": config
    }

@router.get("/api/stats/hourly")
async def get_hourly_stats(
    request: Request,
    date_from: str = Query(None, alias="from"),
    date_to: str = Query(None, alias="to"),
    time_from: str = Query(None, alias="time_from"),
    time_to: str = Query(None, alias="time_to"),
    granularity: int = Query(60),
    routes: Optional[List[str]] = Query(None, alias="route"),
    stops: Optional[List[str]] = Query(None, alias="stop"),
    day_class: Optional[str] = Query(None, alias="day_class"),
    line: Optional[str] = Query(None, alias="line"),
    metric: str = Query("arrival")
):
    # Default dates (helper could be used here to avoid repetition, but keeping inline for now)
    if not date_from or not date_to:
        date_range = get_date_range()
        if not date_from: date_from = date_range['min']
        if not date_to: date_to = date_range['max']
    
    # Sanitize inputs
    if routes: routes = [r for r in routes if r]
    if stops: stops = [s.split(' » ')[0].strip() for s in stops if s]
    if day_class == "": day_class = None
    if line == "": line = None

    data = get_stats_by_time_slot(date_from, date_to, routes, stops, day_class, line_filter=line, metric_type=metric, time_from=time_from, time_to=time_to, bucket_size_minutes=granularity)
    
    # Prepare data for Chart.js (Stacked)
    labels = [str(d['time_slot']) for d in data]
    data_early = [d['early'] for d in data]
    data_on_time = [d['on_time'] for d in data]
    data_late_slight = [d['late_slight'] for d in data]
    data_late_severe = [d['late_severe'] for d in data]
    
    return {
        "labels": labels,
        "datasets": {
            "early": data_early,
            "on_time": data_on_time,
            "late_slight": data_late_slight,
            "late_severe": data_late_severe
        },
        "raw_data": data
    }

@router.get("/api/stats/weekday")
async def get_weekday_stats(
    request: Request,
    date_from: str = Query(None, alias="from"),
    date_to: str = Query(None, alias="to"),
    routes: Optional[List[str]] = Query(None, alias="route"),
    stops: Optional[List[str]] = Query(None, alias="stop"),
    day_class: Optional[str] = Query(None, alias="day_class"),
    line: Optional[str] = Query(None, alias="line"),
    metric: str = Query("arrival")
):
    if not date_from or not date_to:
        date_range = get_date_range()
        if not date_from: date_from = date_range['min']
        if not date_to: date_to = date_range['max']
    
    # Sanitize inputs
    if routes: routes = [r for r in routes if r]
    if stops: stops = [s.split(' » ')[0].strip() for s in stops if s]
    if day_class == "": day_class = None
    if line == "": line = None

    # TODO: Weekday stats currently don't support metric switch in `get_stats_by_weekday` implementation above?
    # I verified `get_stats_by_weekday` DOES NOT yet have `metric_type`. I need to fix that in `database.py` first!
    # Checking `database.py` replacement... I missed `get_stats_by_weekday`! 
    # I should have checked closely. I will assume I need to fix `database.py` for weekday too.
    # But let's finish `dashboard.py` edits assuming it will be there.
    
    # Wait, I did NOT edit `get_stats_by_weekday` in previous step. I must do it.
    
    data = get_stats_by_weekday(date_from, date_to, routes, stops, day_class, line_filter=line, metric_type=metric)
    
    labels = [d['day_name'] for d in data]
    data_early = [d['early'] for d in data]
    data_on_time = [d['on_time'] for d in data]
    data_late_slight = [d['late_slight'] for d in data]
    data_late_severe = [d['late_severe'] for d in data]
    
    return {
        "labels": labels,
        "datasets": {
            "early": data_early,
            "on_time": data_on_time,
            "late_slight": data_late_slight,
            "late_severe": data_late_severe
        }
    }

@router.get("/api/stats/stops")
async def get_stops_stats(
    request: Request,
    date_from: str = Query(None, alias="from"),
    date_to: str = Query(None, alias="to"),
    routes: Optional[List[str]] = Query(None, alias="route"),
    day_class: Optional[str] = Query(None, alias="day_class"),
    line: Optional[str] = Query(None, alias="line")
):
    if not date_from or not date_to:
        date_range = get_date_range()
        if not date_from: date_from = date_range['min']
        if not date_to: date_to = date_range['max']
    
    # Sanitize inputs
    if routes: routes = [r for r in routes if r]
    if day_class == "": day_class = None
    if line == "": line = None
    
    # Problematic stops technically should invoke metric too? Yes.
    # Need to update `get_problematic_stops` in database too.
    
    data = get_problematic_stops(date_from, date_to, routes, day_class=day_class, line_filter=line)
    
    return data
    
@router.get("/api/stats/dwell-time")
async def get_dwell_time_api(
    request: Request,
    date_from: str = Query(None, alias="from"),
    date_to: str = Query(None, alias="to"),
    routes: Optional[List[str]] = Query(None, alias="route"),
    stops: Optional[List[str]] = Query(None, alias="stop"),
    day_class: Optional[str] = Query(None, alias="day_class"),
    line: Optional[str] = Query(None, alias="line")
):
    if not date_from or not date_to:
        date_range = get_date_range()
        if not date_from: date_from = date_range['min']
        if not date_to: date_to = date_range['max']
        
    if routes: routes = [r for r in routes if r]
    if stops: stops = [s.split(' » ')[0].strip() for s in stops if s]
    if day_class == "": day_class = None
    if line == "": line = None
    
    data = get_dwell_time_by_hour(date_from, date_to, routes, stops, day_class, line_filter=line)
    
    labels = [str(d['hour']) for d in data]
    values = [d['avg_seconds'] for d in data]
    
    # We can return JSON if we want to render strictly via JS, OR a partial.
    # Request said: "render to template". Let's use a partial for the chart container?
    # Or return JSON data for the chart to consume? 
    # Usually we return a partial with data embedded.
    
    return {
        "labels": labels,
        "values": values
    }


@router.get("/api/lines/{line_id}/stops")
async def get_line_stops(
    line_id: str,
    route: Optional[str] = Query(None)
):
    """
    Returns stops for a given line (or all if line_id is empty).
    """
    if line_id == "all":
        line_id = None
        
    stops = get_stops(line_filter=line_id, route_filter=route)
    return stops

@router.get("/api/debug/check_route")
async def check_route_debug(route: str):
    return debug_check_route(route)

@router.get("/api/stats/worst-trips")
async def get_worst_trips_api(
    request: Request,
    date_from: str = Query(None, alias="from"),
    date_to: str = Query(None, alias="to"),
    routes: Optional[List[str]] = Query(None, alias="route"),
    stops: Optional[List[str]] = Query(None, alias="stop"),
    day_class: Optional[str] = Query(None, alias="day_class"),
    line: Optional[str] = Query(None, alias="line"),
    time_from: Optional[str] = Query(None, alias="time_from"),
    time_to: Optional[str] = Query(None, alias="time_to")
):
    if not date_from or not date_to:
        date_range = get_date_range()
        if not date_from: date_from = date_range['min']
        if not date_to: date_to = date_range['max']
        
    if routes: routes = [r for r in routes if r]
    if stops: stops = [s.split(' » ')[0].strip() for s in stops if s]
    if day_class == "": day_class = None
    if line == "": line = None
    
    data = get_worst_trips(date_from, date_to, routes, stops, day_class, line_filter=line, time_from=time_from, time_to=time_to)
    
    return data

@router.get("/api/stats/heatmap", response_model=HeatmapResponse)
async def get_heatmap_stats_api(
    request: Request,
    date_from: str = Query(None, alias="from"),
    date_to: str = Query(None, alias="to"),
    time_from: str = Query(None, alias="time_from"),
    time_to: str = Query(None, alias="time_to"),
    granularity: str = Query("60"),
    routes: Optional[List[str]] = Query(None, alias="route"),
    stops: Optional[List[str]] = Query(None, alias="stop"),
    day_class: Optional[str] = Query(None, alias="day_class"),
    line: Optional[str] = Query(None, alias="line"),
    metric: str = Query("arrival"),
    trip_type_regular: bool = Query(False)
):
    if not date_from or not date_to:
        date_range = get_date_range()
        if not date_from: date_from = date_range['min']
        if not date_to: date_to = date_range['max']
    
    if routes: routes = [r for r in routes if r]
    if stops: stops = [s.split(' » ')[0].strip() for s in stops if s]
    if day_class == "": day_class = None
    if line == "": line = None
    
    # --- API DEBUG ---
    print(f"--- API DEBUG ---")
    print(f"RECEIVED Date: '{date_from}' to '{date_to}'")
    if routes:
        print(f"RECEIVED Filters: {routes} (Type: {type(routes)})")
        for r in routes:
            print(f"RECEIVED Route String: '{r}'")
            print(f"RECEIVED Route Bytes: {r.encode('utf-8')}")
            
            # Check for "»" specifically
            if "»" in r:
                print(f"  -> Contains '»' (U+00BB)")
            else:
                print(f"  -> DOES NOT contain '»'")
                
    
    # Logic: The backend should NOT override the user's requested granularity.
    # The Frontend (App.jsx) handles auto-switching if needed.
    # We strictly respect 'trip' if requested.


    data = get_heatmap_stats(
        date_from, date_to, routes, stops, day_class, 
        line_filter=line, metric_type=metric, 
        time_from=time_from, time_to=time_to, 
        granularity=granularity,
        trip_type_regular=trip_type_regular
    )
    
    print(f"DEBUG: Heatmap Data Keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
    if isinstance(data, dict) and 'grid' in data:
        grid = data.get('grid', [])
        print(f"DEBUG: Heatmap Matrix Mode. Grid Rows: {len(grid)}, Cols: {len(grid[0]) if grid else 0}")
        
        # --- PATTERN DEBUG ---
        print("--- PATTERN DEBUG ---")
        if 'x_labels' in data:
            print(f"First 5 x_labels: {data.get('x_labels', [])[:5]}")
        else:
            print("WARNING: 'x_labels' MISSING in response data!")
            
        if 'trips' in data:
             cols = data.get('trips', [])
             print(f"First 5 trips metadata: {cols[:5]}")
        else:
             print("WARNING: 'trips' MISSING in response data!")
    
    return data

