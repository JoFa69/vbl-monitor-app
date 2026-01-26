from typing import Dict, Any, List, Optional
import logging
import os
import duckdb
from datetime import datetime

# Setup Logging
logger = logging.getLogger(__name__)

# Constants
# Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'optimized')
RAW_DATA_DIR = os.path.join(BASE_DIR, 'data')

def load_calendar_data(conn: duckdb.DuckDBPyConnection):
    """
    Loads special dates (holidays/vacations) from CSV into DuckDB.
    """
    csv_path = os.path.join(RAW_DATA_DIR, 'Ferien_Feiertage.csv')
    
    try:
        if os.path.exists(csv_path):
            # Load from CSV if exists
            # We explicitly set encoding to latin-1 (common for German CSVs) and dateformat
            conn.execute(f"""
                CREATE OR REPLACE TABLE special_dates AS 
                SELECT * FROM read_csv('{csv_path.replace(chr(92), chr(47))}', 
                    encoding='latin-1', 
                    dateformat='%d.%m.%y',
                    auto_detect=true,
                    header=true
                )
            """)
        else:
            # Create empty table if file is missing to prevent query errors
            conn.execute("CREATE TABLE IF NOT EXISTS special_dates (date DATE, day_type VARCHAR, description VARCHAR)")
            
    except Exception as e:
        logger.error(f"Error loading calendar data: {e}")
        # Ensure table exists even on error
        conn.execute("CREATE TABLE IF NOT EXISTS special_dates (date DATE, day_type VARCHAR, description VARCHAR)")

def create_day_class_macro(conn: duckdb.DuckDBPyConnection):
    """
    Creates the get_day_class(my_date) macro/function in DuckDB.
    Since we need a table lookup, a simple SCALAR MACRO might not work if it doesn't support subqueries flexibly.
    However, DuckDB allows scalar subqueries.
    
    Logic:
    1. Check if date in special_dates (Feiertag > Ferien)
    2. Else check day of week
    
    We use a scalar subquery to look up the priority day_type.
    """
    try:
        # We can implement this logic effectively using a subquery that finds the 'highest priority' entry for the date
        # Priority: Feiertag > Ferien.
        # Let's map day_type to a robust string.
        # We need to handle multiple entries per date if any (e.g. Ferien + Feiertag distinct rows? usually one).
        
        # Macro Logic:
        # (SELECT 
        #    CASE 
        #      WHEN day_type = 'Feiertag' THEN 'Sonn-/Feiertag'
        #      WHEN day_type = 'Ferien' AND extract('dow' FROM my_date) BETWEEN 1 AND 5 THEN 'Mo-Fr (Ferien)'
        #      ELSE NULL 
        #    END 
        #  FROM special_dates WHERE date = my_date 
        #  ORDER BY CASE WHEN day_type='Feiertag' THEN 1 ELSE 2 END 
        #  LIMIT 1
        # )
        # COALESCE that with standard dow logic.
        
        # Note: extract('dow', ...) -> 0=Sunday, 1=Monday... 6=Saturday in DuckDB? NO.
        # DuckDB `extract('dow' ...)`: Sunday=0, Monday=1, ... Saturday=6.
        # Wait, Step 2 requested: 1-5 -> Mo-Fr, 6 -> Sa, 7 -> So.
        # `isodow()` returns Monday=1 ... Sunday=7. This matches the request better.
        
        query = """
        CREATE OR REPLACE MACRO get_day_class(my_date) AS
        COALESCE(
            (SELECT 
                CASE 
                    WHEN day_type = 'Feiertag' THEN 'Sonn-/Feiertag'
                    WHEN day_type = 'Ferien' AND isodow(my_date) BETWEEN 1 AND 5 THEN 'Mo-Fr (Ferien)'
                    ELSE NULL
                END
             FROM special_dates 
             WHERE date = CAST(my_date AS DATE)
             ORDER BY CASE WHEN day_type = 'Feiertag' THEN 0 ELSE 1 END
             LIMIT 1
            ),
            CASE 
                WHEN isodow(my_date) BETWEEN 1 AND 5 THEN 'Mo-Fr (Schule)'
                WHEN isodow(my_date) = 6 THEN 'Samstag'
                ELSE 'Sonn-/Feiertag'
            END
        )
        """
        conn.execute(query)
    except Exception as e:
        logger.error(f"Error creating macro: {e}")

def load_config_data(conn: duckdb.DuckDBPyConnection):
    """
    Initializes app_config table and loads data from persistence file (JSON).
    """
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS app_config (key VARCHAR PRIMARY KEY, value VARCHAR)")
        
        config_path = os.path.join(RAW_DATA_DIR, 'config.json')
        if os.path.exists(config_path):
            import json
            with open(config_path, 'r') as f:
                data = json.load(f)
                for k, v in data.items():
                    # Upsert
                    val = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                    conn.execute("INSERT OR REPLACE INTO app_config VALUES (?, ?)", [k, val])
    except Exception as e:
        logger.error(f"Error initializing config: {e}")

# --- Global Database Connection & Initialization ---

conn: Optional[duckdb.DuckDBPyConnection] = None
TABLE_NAME: Optional[str] = None

def _init_db():
    global conn, TABLE_NAME
    token = os.environ.get('MOTHERDUCK_TOKEN')
    
    try:
        if token:
            # Scenario A: Cloud (MotherDuck)
            logger.info("Connecting to MotherDuck Cloud...")
            conn = duckdb.connect(f'md:my_db?motherduck_token={token}')
            TABLE_NAME = "my_db.main.data_nov25"
            logger.info("Connected to MotherDuck Cloud")
        else:
            # Scenario B: Local
            logger.info("Connecting to Local Parquet Files...")
            conn = duckdb.connect(':memory:')
            # Construct absolute path for local glob
            # Ensure forward slashes for DuckDB
            parquet_path = os.path.join(DATA_DIR, '**', '*.parquet').replace(chr(92), chr(47))
            TABLE_NAME = f"'{parquet_path}'" 
            logger.info(f"Connected to Local Parquet Files at {TABLE_NAME}")

        # 1. Load Calendar Data
        load_calendar_data(conn)
        
        # 2. Initialize Config
        load_config_data(conn)
        
        # 3. Create Helper Macros
        create_day_class_macro(conn)
        
        # 4. Create Abstract View 'vbl_data'
        # This View allows us to swap the source (Parquet vs MotherDuck) without changing queries.
        # We use read_parquet for local to ensure hive_partitioning is enabled if needed,
        # but the user requested 'SELECT * FROM {TABLE_NAME}'.
        # For local, if TABLE_NAME is a string literal of a path, we can use it directly.
        # However, to support hive_partitioning explicitly if auto-detect fails, we might need a tweak.
        # But 'SELECT * FROM 'path'' usually triggers valid auto-detection.
        # We alias it to vbl_data.
        
        conn.execute(f"CREATE OR REPLACE VIEW vbl_data AS SELECT *, CAST(date AS DATE) as date_dt FROM {TABLE_NAME}")
        
        # 5. Enriched View (Sequence)
        conn.execute("""
            CREATE OR REPLACE VIEW vbl_data_enriched AS
            SELECT 
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY trip_id, date 
                    ORDER BY COALESCE(departure_planned, arrival_planned) ASC
                ) as stop_sequence
            FROM vbl_data
            WHERE (departure_planned IS NOT NULL OR arrival_planned IS NOT NULL)
        """)
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

# Initialize on module load
_init_db()

def get_connection() -> duckdb.DuckDBPyConnection:
    """
    Returns the global database connection. 
    WARNING: Do not close this connection in downstream functions.
    """
    return conn

def get_app_config() -> Dict[str, str]:
    """Returns all config key-value pairs from DB."""
    conn = get_connection()
    try:
        results = conn.execute("SELECT key, value FROM app_config").fetchall()
        return {r[0]: r[1] for r in results}
    finally:
        pass # Global connection preserved

DEFAULT_CONFIG = {
    "threshold_early": "-60",
    "threshold_late": "180",
    "threshold_critical": "300",
    "ignore_outliers": "false",
    "outlier_min": "-1200",
    "outlier_max": "3600"
}

def get_merged_config() -> Dict[str, str]:
    """Returns configuration with DB values overriding defaults."""
    db_config = get_app_config()
    final_config = DEFAULT_CONFIG.copy()
    final_config.update(db_config)
    return final_config

def set_app_config(config_data: Dict[str, str]):
    """Updates config in DB and persists to JSON file."""
    conn = get_connection()
    try:
        # Update DB (for verification/completeness)
        # Update DB (for verification/completeness)
        import json
        for k, v in config_data.items():
            val = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            conn.execute("INSERT OR REPLACE INTO app_config VALUES (?, ?)", [k, val])
            
        # Persist to JSON
        config_path = os.path.join(RAW_DATA_DIR, 'config.json')
        import json
        
        # Read existing to merge? Or just overwrite with current DB state?
        # Better: Read all from DB to ensure we have the full picture if we do partial updates
        current_db_state = {r[0]: r[1] for r in conn.execute("SELECT key, value FROM app_config").fetchall()}
        
        with open(config_path, 'w') as f:
            json.dump(current_db_state, f, indent=2)
            
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise
    finally:
        pass # Global connection preserved

def get_date_range() -> Dict[str, str]:
    """
    Returns the min and max date available in the dataset.
    """
    conn = get_connection()
    try:
        query = "SELECT MIN(date_dt), MAX(date_dt) FROM vbl_data"
        min_date, max_date = conn.execute(query).fetchone()
        
        # Fallback if no data
        if not min_date:
            today = datetime.now().strftime('%Y-%m-%d')
            return {"min": today, "max": today}
            
        return {
            "min": min_date.strftime('%Y-%m-%d'), 
            "max": max_date.strftime('%Y-%m-%d')
        }
    except Exception as e:
        logger.error(f"Error fetching date range: {e}")
        today = datetime.now().strftime('%Y-%m-%d')
        return {"min": today, "max": today}
    finally:
        pass # Global connection preserved

def get_lines() -> Dict[str, List[Dict[str, Any]]]:
    """
    Retrieves a dictionary of lines and their associated routes (Start » End) with trip counts.
    Structure: {"1": [{"name": "Kriens, Busa » Ebikon, Fildern", "count": 120}, ...], ...}
    """
    conn = get_connection()
    try:
        # We use a CTE to first distinct trips and find their start/end stops.
        # Then we aggregate to count trips per unique route.
        query = """
        WITH trip_routes AS (
            SELECT
                line_name,
                trip_id,
                -- Find Start: The stop with the earliest DEPARTURE time
                arg_min(stop_name, departure_planned) as start_name,
                -- Find End: The stop with the latest ARRIVAL time
                arg_max(stop_name, arrival_planned) as end_name
            FROM vbl_data
            GROUP BY trip_id, line_name
        ),
        route_stats AS (
            SELECT
                line_name,
                start_name || ' » ' || end_name as route_name,
                COUNT(trip_id) as count
            FROM trip_routes
            WHERE start_name IS NOT NULL AND end_name IS NOT NULL
            GROUP BY line_name, route_name
        )
        SELECT line_name, route_name, count
        FROM route_stats
        ORDER BY count DESC
        """
        results = conn.execute(query).fetchall()
        
        lines = {}
        for line_name, route_name, count in results:
            if line_name not in lines:
                lines[line_name] = []
            lines[line_name].append({"name": route_name, "count": count})
            
        return lines
    except Exception as e:
        logger.error(f"Error fetching lines: {e}")
        return {}
    finally:
        pass # Global connection preserved

def get_stops(line_filter: Optional[str] = None, route_filter: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Returns stops for a given line/route. 
    If route_filter is provided, tries to determine the "next stop" for context.
    Returns list of dicts: {"value": "Stop Name", "label": "Stop Name [» Next Stop]"}
    """
    conn = get_connection()
    try:
        from datetime import datetime
        
        # New Logic: Distinction via "Stop » Destination"
        # We need end_name (destination) for every stop context.
        
        # Base logic:
        # 1. Identify trips matching line/route filters (if any).
        # 2. For these trips, select stop_name and end_name.
        # 3. Return distinct composite string.
        
        cte = """
        WITH trip_routes AS (
            SELECT 
                trip_id,
                arg_max(stop_name, arrival_planned) as end_name,
                arg_min(stop_name, departure_planned) as start_name
            FROM vbl_data
            WHERE stop_name IS NOT NULL
            GROUP BY trip_id
        )
        """
        
        # Build Filter
        where_clauses = ["v.stop_name IS NOT NULL"]
        params = []
        
        if line_filter:
            where_clauses.append("v.line_name = ?")
            params.append(line_filter)
            
        if route_filter:
            # Route filter is "Start » End"
            where_clauses.append("(tr.start_name || ' » ' || tr.end_name) = ?")
            params.append(route_filter)
            
        where_str = " AND ".join(where_clauses)
        
        query = f"""
        {cte}
        SELECT DISTINCT v.stop_name || ' » ' || tr.end_name as full_name
        FROM vbl_data v
        JOIN trip_routes tr ON v.trip_id = tr.trip_id
        WHERE {where_str}
        ORDER BY full_name
        """
        
        results = conn.execute(query, params).fetchall()
        
        # Return format expected by frontend: value=full_name, label=full_name
        # The frontend will use the value for filtering (which now supports composite)
        return [{"value": r[0], "label": r[0]} for r in results]
            
    except Exception as e:
        logger.error(f"Error fetching stops: {e}")
        return []
    finally:
        pass # Global connection preserved

def debug_check_route(route_input: str) -> Dict[str, Any]:
    conn = get_connection()
    try:
        parts = route_input.split(' » ')
        if len(parts) != 2: return {"error": "Invalid separate"}
        start, end = parts
        
        # We need to recreate the exact CTE logic to see what's in DB
        query = """
        WITH trip_routes AS (
            SELECT trip_id, 
                   arg_min(stop_name, departure_planned) as start_name, 
                   arg_max(stop_name, arrival_planned) as end_name 
            FROM vbl_data 
            WHERE date >= '2025-11-01' AND date <= '2025-11-02'
            GROUP BY trip_id
        )
        SELECT start_name || ' » ' || end_name as r 
        FROM trip_routes 
        WHERE start_name = ? AND end_name = ? 
        LIMIT 1
        """
        row = conn.execute(query, [start, end]).fetchone()
        
        input_ords = [ord(c) for c in route_input]
        if row:
            db_route = row[0]
            return {
                "match": (db_route == route_input),
                "db_route": db_route,
                "db_ords": [ord(c) for c in db_route],
                "input_ords": input_ords
            }
        return {"match": False, "reason": "Not found in DB", "input_ords": input_ords}
    except Exception as e:
        return {"error": str(e)}
    finally:
        pass # Global connection preserved

def _build_filter_clause(date_from: str, date_to: str, routes: Optional[List[str]] = None, stops: Optional[List[str]] = None, day_class: Optional[str] = None, line_filter: Optional[str] = None, time_from: Optional[str] = None, time_to: Optional[str] = None):
    """
    Helper to build SQL WHERE clause and parameters for common filters.
    Returns (where_clause, params_list)
    """
    clauses = ["v.date >= ? AND v.date <= ?"]
    params = [date_from, date_to]
    
    if routes:
        # Robust Route Filtering: Split 'Start » End' to filter by clean stop names
        route_conditions = []
        for r in routes:
             parts = r.split(' » ')
             if len(parts) == 2:
                 # Precision Filter (Avoids encoding issues with '»')
                 route_conditions.append("(tr.start_name = ? AND tr.end_name = ?)")
                 # We assume strict match on stop names is safe. 
                 params.extend([parts[0], parts[1]])
             else:
                 # Fallback to Fuzzy Match
                 route_conditions.append("tr.route_name LIKE ?")
                 clean_r = r.replace('»', '%')
                 params.append(f"%{clean_r}%")
        
        if route_conditions:
            clauses.append(f"({' OR '.join(route_conditions)})")
        
    if stops:
        # Check if stops are composite "Stop » Dest"
        # We assume if the FIRST stop contains " » ", they all do (or we treat them as such)
        if len(stops) > 0 and " » " in stops[0]:
            # Composite filter: stop_name || ' » ' || end_name
            stop_placeholders = ','.join(['?'] * len(stops))
            clauses.append(f"(v.stop_name || ' » ' || tr.end_name) IN ({stop_placeholders})")
            params.extend(stops)
        else:
            # Legacy/Simple filter
            stop_placeholders = ','.join(['?'] * len(stops))
            clauses.append(f"v.stop_name IN ({stop_placeholders})")
            params.extend(stops)
        
    if day_class:
        clauses.append("get_day_class(v.date_dt) = ?")
        params.append(day_class)

    if line_filter:
        clauses.append("v.line_name = ?")
        params.append(line_filter)
        
    if time_from and time_to:
        if time_from == time_to:
            # Equal time (e.g. 04:00 to 04:00) implies "Whole Day" (effectively no filter within the date range)
            pass
        elif time_from > time_to:
            # Cross-midnight range (e.g. 22:00 to 02:00)
            clauses.append("(CAST(v.arrival_planned AS TIME) >= CAST(? AS TIME) OR CAST(v.arrival_planned AS TIME) <= CAST(? AS TIME))")
            params.extend([time_from, time_to])
        else:
            # Standard range (e.g. 06:00 to 09:00)
            clauses.append("CAST(v.arrival_planned AS TIME) >= CAST(? AS TIME)")
            clauses.append("CAST(v.arrival_planned AS TIME) <= CAST(? AS TIME)")
            params.extend([time_from, time_to])
    elif time_from:
        clauses.append("CAST(v.arrival_planned AS TIME) >= CAST(? AS TIME)")
        params.append(time_from)
    elif time_to:
        clauses.append("CAST(v.arrival_planned AS TIME) <= CAST(? AS TIME)")
        params.append(time_to)
        
    return " AND ".join(clauses), params


def get_punctuality_stats(date_from: str, date_to: str, route_filter: Optional[List[str]] = None, stop_filter: Optional[List[str]] = None, day_class: Optional[str] = None, line_filter: Optional[str] = None, metric_type: str = "arrival", time_from: Optional[str] = None, time_to: Optional[str] = None) -> Dict[str, int]:
    """
    Calculates punctuality statistics for the given date range, filtered by routes/stops.
    metric_type: 'arrival' or 'departure'
    """
    conn = get_connection()
    try:
        # Load Config
        cfg = get_app_config()
        t_early = int(cfg.get('threshold_early', -60))
        t_late = int(cfg.get('threshold_late', 180)) # Default from 120 to 180 to match new config default
        t_crit = int(cfg.get('threshold_critical', 300))
        
        # Determine columns based on metric
        col_planned = "v.arrival_planned" if metric_type == "arrival" else "v.departure_planned"
        col_actual = "v.arrival_actual" if metric_type == "arrival" else "v.departure_actual"

        # Outlier Logic
        outlier_condition = ""
        outlier_params = []
        if cfg.get('ignore_outliers') == 'true':
            out_min = int(cfg.get('outlier_min', -1200))
            out_max = int(cfg.get('outlier_max', 3600))
            outlier_condition = f"AND date_diff('second', {col_planned}, {col_actual}) BETWEEN ? AND ?"
            outlier_params = [out_min, out_max]

        # 1. Base params for the Trip Route CTE (date range only to limit scope early)
        cte_params = [date_from, date_to]
        
        # 2. Filter params for the main query
        filter_clause, filter_params = _build_filter_clause(date_from, date_to, route_filter, stop_filter, day_class, line_filter, time_from, time_to)
        
        # We join with trip_routes only if we need route information (which we do for the filter)
        # But wait, if we filter by specific stop, we simply look at vbl_data where stop_name = X.
        # If we filter by route, we need the CTE mapping trip_id -> route.
        
        # Determine if we should filter by last stop only
        # If specific stops are requested, we want to analyze those specific stops, not just end-of-trip
        # ONLY apply last_stop logic for ARRIVAL at end of trip if no specific stop filter?
        # Actually for 'departure' we usually care about START of trip or all stops?
        # Requirement: "Pünktlichkeit" usually means Arrival Punctuality at last stop (for trips) or all stops (for stops).
        # Adjust logic: If metric is departure, we might compare start. However, user request implies switching GLOBAL metric.
        
        last_stop_condition = "AND v.arrival_planned = tr.last_arrival_time"
        if (stop_filter and len(stop_filter) > 0) or metric_type == 'departure':
             # If looking at departure, checking arrival time at last stop is wrong.
             # We should probably look at all stops? Or just start?
             # Let's disable the "last stop only" filter for departure mode to capture delays at any point, 
             # OR if specifically requested, maybe start?
             # "Pünktlichkeit" dashboard typically aggregates ALL measured events if not single trip.
             # But existing logic filtered for LAST stop to avoid overcounting a single trip's delay?
             # Let's keep existing logic: "last_stop_condition" was there to count unique TRIPS based on their final status.
             # If metric=departure, we should use FIRST stop? Or just disable?
             # Let's disable for now to show all data points or maybe start?
             # Use: If departure default to start?
             pass 

        if (stop_filter and len(stop_filter) > 0):
            last_stop_condition = ""
        elif metric_type == 'departure':
             # For departure punctuality of a TRIP, usually it is the Start.
             last_stop_condition = "AND v.departure_planned = tr.first_departure_time"
            
        query = f"""
        WITH trip_routes AS (
            SELECT
                trip_id,
                date,
                arg_min(stop_name, departure_planned) as start_name,
                arg_max(stop_name, arrival_planned) as end_name,
                MAX(arrival_planned) as last_arrival_time,
                MIN(departure_planned) as first_departure_time
            FROM vbl_data
            WHERE date >= ? AND date <= ?
            GROUP BY trip_id, date
        ),
        trip_routes_named AS (
            SELECT 
                trip_id,
                date,
                start_name || ' » ' || end_name as route_name,
                start_name,
                end_name,
                last_arrival_time,
                first_departure_time
            FROM trip_routes
        ),
        trip_delays AS (
            SELECT
                v.trip_id,
                MAX(date_diff('second', {col_planned}, {col_actual})) as delay
            FROM vbl_data v
            JOIN trip_routes_named tr ON v.trip_id = tr.trip_id AND v.date = tr.date
            WHERE v.{metric_type}_status = 'REAL' 
              {last_stop_condition}
              AND {filter_clause}
              {outlier_condition}
            GROUP BY v.trip_id, v.date
        )
        SELECT
            CASE
                WHEN delay < {t_early} THEN 'early'
                WHEN delay BETWEEN {t_early} AND {t_late} THEN 'on_time'
                WHEN delay BETWEEN {t_late + 1} AND {t_crit} THEN 'late_slight'
                WHEN delay > {t_crit} THEN 'late_severe'
                ELSE 'unknown'
            END as bucket,
            COUNT(*) as count
        FROM trip_delays
        GROUP BY bucket
        """
        
        # Params: CTE dates + Filter params + Outlier params
        full_params = cte_params + filter_params + outlier_params
        
        results = conn.execute(query, full_params).fetchall()
        
        stats = {
            'early': 0, 'on_time': 0, 'late_slight': 0, 'late_severe': 0, 'total': 0
        }
        
        total = 0
        for row in results:
            bucket, count = row
            if bucket in stats:
                stats[bucket] = count
                total += count
                
        stats['total'] = total
        return stats
        
    except Exception as e:
        logger.error(f"Error calculating stats: {e}")
        return {}
    finally:
        pass # Global connection preserved

def get_stats_by_time_slot(date_from: str, date_to: str, routes: Optional[List[str]] = None, stops: Optional[List[str]] = None, day_class: Optional[str] = None, line_filter: Optional[str] = None, metric_type: str = "arrival", time_from: Optional[str] = None, time_to: Optional[str] = None, bucket_size_minutes: int = 60) -> List[Dict[str, Any]]:
    """
    Returns aggregated stats bucketed by time slots (default 60 mins).
    """
    conn = get_connection()
    try:
        # Load Config
        cfg = get_app_config()
        t_early = int(cfg.get('threshold_early', -60))
        t_late = int(cfg.get('threshold_late', 180))
        
        col_planned = "v.arrival_planned" if metric_type == "arrival" else "v.departure_planned"
        col_actual = "v.arrival_actual" if metric_type == "arrival" else "v.departure_actual"
        
        # Outlier Logic
        outlier_condition = ""
        outlier_params = []
        if cfg.get('ignore_outliers') == 'true':
            out_min = int(cfg.get('outlier_min', -1200))
            out_max = int(cfg.get('outlier_max', 3600))
            outlier_condition = f"AND date_diff('second', {col_planned}, {col_actual}) BETWEEN ? AND ?"
            outlier_params = [out_min, out_max]

        cte_params = [date_from, date_to]
        filter_clause, filter_params = _build_filter_clause(date_from, date_to, routes, stops, day_class, line_filter, time_from, time_to)
        
        last_stop_condition = "AND v.arrival_planned = tr.last_arrival_time"
        if metric_type == 'departure':
             last_stop_condition = "AND v.departure_planned = tr.first_departure_time"

        if stops and len(stops) > 0:
            last_stop_condition = ""
            
        seconds_per_bucket = bucket_size_minutes * 60
            
        query = f"""
        WITH trip_routes AS (
            SELECT
                trip_id,
                date,
                arg_min(stop_name, departure_planned) as start_name,
                arg_max(stop_name, arrival_planned) as end_name,
                MAX(arrival_planned) as last_arrival_time,
                MIN(departure_planned) as first_departure_time
            FROM vbl_data
            WHERE date >= ? AND date <= ?
            GROUP BY trip_id, date
        ),
        trip_routes_named AS (
            SELECT trip_id, date, start_name || ' » ' || end_name as route_name, start_name, end_name, last_arrival_time, first_departure_time FROM trip_routes
        ),
        slot_data AS (
            SELECT
                -- Bucketing Logic: Round down timestamp to nearest bucket start, format as HH:MM
                strftime(to_timestamp(floor(epoch(MAX({col_planned})) / {seconds_per_bucket}) * {seconds_per_bucket}), '%H:%M') as time_slot,
                CASE
                    WHEN MAX(date_diff('second', {col_planned}, {col_actual})) < {t_early} THEN 'early'
                    WHEN MAX(date_diff('second', {col_planned}, {col_actual})) BETWEEN {t_early} AND {t_late} THEN 'on_time'
                    WHEN MAX(date_diff('second', {col_planned}, {col_actual})) BETWEEN {t_late + 1} AND {cfg.get('threshold_critical', 300)} THEN 'late_slight'
                    ELSE 'late_severe'
                END as status
            FROM vbl_data v
            JOIN trip_routes_named tr ON v.trip_id = tr.trip_id AND v.date = tr.date
            WHERE v.{metric_type}_status = 'REAL' 
              {last_stop_condition}
              AND {filter_clause}
              {outlier_condition}
            GROUP BY v.trip_id, v.date
        )
        SELECT
            time_slot,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'early' THEN 1 ELSE 0 END) as early,
            SUM(CASE WHEN status = 'on_time' THEN 1 ELSE 0 END) as on_time,
            SUM(CASE WHEN status = 'late_slight' THEN 1 ELSE 0 END) as late_slight,
            SUM(CASE WHEN status = 'late_severe' THEN 1 ELSE 0 END) as late_severe
        FROM slot_data
        GROUP BY time_slot
        ORDER BY CASE 
            WHEN CAST(substr(time_slot, 1, 2) AS INTEGER) < 4 THEN CAST(substr(time_slot, 1, 2) AS INTEGER) + 24 
            ELSE CAST(substr(time_slot, 1, 2) AS INTEGER) 
        END, time_slot
        """
        
        results = conn.execute(query, cte_params + filter_params + outlier_params).fetchall()
        
        output = []
        for time_slot, total, early, on_time, late_slight, late_severe in results:
            output.append({
                "time_slot": time_slot,
                "total": total,
                "early": early,
                "on_time": on_time,
                "late_slight": late_slight,
                "late_severe": late_severe
            })
        return output
    except Exception:
        raise
    finally:
        pass # Global connection preserved

def get_dwell_time_by_hour(date_from: str, date_to: str, routes: Optional[List[str]] = None, stops: Optional[List[str]] = None, day_class: Optional[str] = None, line_filter: Optional[str] = None, time_from: Optional[str] = None, time_to: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Returns average dwell time (halt status) per hour.
    Formula: AVG(departure_actual - arrival_actual) where both are REAL.
    """
    conn = get_connection()
    try:
        cte_params = [date_from, date_to]
        filter_clause, filter_params = _build_filter_clause(date_from, date_to, routes, stops, day_class, line_filter, time_from, time_to)
        
        query = f"""
        WITH trip_routes AS (
             SELECT
                trip_id,
                date,
                arg_min(stop_name, departure_planned) as start_name,
                arg_max(stop_name, arrival_planned) as end_name
            FROM vbl_data
            WHERE date >= ? AND date <= ?
            GROUP BY trip_id, date
        ),
        trip_routes_named AS (
            SELECT trip_id, date, start_name || ' » ' || end_name as route_name, start_name, end_name FROM trip_routes
        ),
        dwell_data AS (
            SELECT
                extract('hour' from v.arrival_actual) as hour,
                date_diff('second', v.arrival_actual, v.departure_actual) as dwell_seconds
            FROM vbl_data v
            JOIN trip_routes_named tr ON v.trip_id = tr.trip_id AND v.date = tr.date
            WHERE v.arrival_status = 'REAL' AND v.departure_status = 'REAL'
              AND {filter_clause}
              -- Filter out negative or excessive dwell times? e.g. > 20 mins?
              AND date_diff('second', v.arrival_actual, v.departure_actual) BETWEEN 0 AND 1200
        )
        SELECT
            hour,
            AVG(dwell_seconds) as avg_seconds
        FROM dwell_data
        GROUP BY hour
        ORDER BY hour
        """
        
        results = conn.execute(query, cte_params + filter_params).fetchall()
        
        output = []
        for hour, avg_seconds in results:
            output.append({
                "hour": int(hour),
                "avg_seconds": round(avg_seconds, 1)
            })
        return output
        
    except Exception as e:
        logger.error(f"Error calculating dwell time: {e}")
        return []
    finally:
        pass # Global connection preserved


def get_stats_by_weekday(date_from: str, date_to: str, routes: Optional[List[str]] = None, stops: Optional[List[str]] = None, day_class: Optional[str] = None, line_filter: Optional[str] = None, metric_type: str = "arrival", time_from: Optional[str] = None, time_to: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Returns aggregated stats bucketed by weekday.
    """
    conn = get_connection()
    try:
        col_planned = "v.arrival_planned" if metric_type == "arrival" else "v.departure_planned"
        col_actual = "v.arrival_actual" if metric_type == "arrival" else "v.departure_actual"
        
        cte_params = [date_from, date_to]
        filter_clause, filter_params = _build_filter_clause(date_from, date_to, routes, stops, day_class, line_filter, time_from, time_to)
        
        last_stop_condition = "AND v.arrival_planned = tr.last_arrival_time"
        if metric_type == 'departure':
             last_stop_condition = "AND v.departure_planned = tr.first_departure_time"

        if stops and len(stops) > 0:
            last_stop_condition = ""
            
        # load thresholds
        cfg = get_app_config()
        t_early = int(cfg.get('threshold_early', -60))
        t_late = int(cfg.get('threshold_late', 180))
        t_crit = int(cfg.get('threshold_critical', 300))
        
        # Outlier Logic
        outlier_condition = ""
        outlier_params = []
        if cfg.get('ignore_outliers') == 'true':
            out_min = int(cfg.get('outlier_min', -1200))
            out_max = int(cfg.get('outlier_max', 3600))
            outlier_condition = f"AND date_diff('second', {col_planned}, {col_actual}) BETWEEN ? AND ?"
            outlier_params = [out_min, out_max]

        query = f"""
        WITH trip_routes AS (
            SELECT
                trip_id,
                date,
                arg_min(stop_name, departure_planned) as start_name,
                arg_max(stop_name, arrival_planned) as end_name,
                MAX(arrival_planned) as last_arrival_time,
                MIN(departure_planned) as first_departure_time
            FROM vbl_data
            WHERE date >= ? AND date <= ?
            GROUP BY trip_id, date
        ),
        trip_routes_named AS (
            SELECT trip_id, date, start_name || ' » ' || end_name as route_name, start_name, end_name, last_arrival_time, first_departure_time FROM trip_routes
        ),
        daily_data AS (
            SELECT
                isodow(MAX(v.date_dt)) as dow, -- 1=Monday, 7=Sunday
                CASE
                    WHEN MAX(date_diff('second', {col_planned}, {col_actual})) < {t_early} THEN 'early'
                    WHEN MAX(date_diff('second', {col_planned}, {col_actual})) BETWEEN {t_early} AND {t_late} THEN 'on_time'
                    WHEN MAX(date_diff('second', {col_planned}, {col_actual})) BETWEEN {t_late + 1} AND {t_crit} THEN 'late_slight'
                    ELSE 'late_severe'
                END as status
            FROM vbl_data v
            JOIN trip_routes_named tr ON v.trip_id = tr.trip_id AND v.date = tr.date
            WHERE v.{metric_type}_status = 'REAL' 
              {last_stop_condition}
              AND {filter_clause}
              {outlier_condition}
            GROUP BY v.trip_id, v.date
        )
        SELECT
            dow,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'early' THEN 1 ELSE 0 END) as early,
            SUM(CASE WHEN status = 'on_time' THEN 1 ELSE 0 END) as on_time,
            SUM(CASE WHEN status = 'late_slight' THEN 1 ELSE 0 END) as late_slight,
            SUM(CASE WHEN status = 'late_severe' THEN 1 ELSE 0 END) as late_severe
        FROM daily_data
        GROUP BY dow
        ORDER BY dow
        """
        
        results = conn.execute(query, cte_params + filter_params + outlier_params).fetchall()
        
        days_map = {1: 'Mo', 2: 'Di', 3: 'Mi', 4: 'Do', 5: 'Fr', 6: 'Sa', 7: 'So'}
        output = []
        for dow, total, early, on_time, late_slight, late_severe in results:
            output.append({
                "dow": int(dow),
                "day_name": days_map.get(int(dow), 'Unknown'),
                "total": total,
                "early": early,
                "on_time": on_time,
                "late_slight": late_slight,
                "late_severe": late_severe
            })
        return output
    except Exception:
        raise
    finally:
        pass # Global connection preserved

def get_cancellation_stats(date_from: str, date_to: str, routes: Optional[List[str]] = None, stop_filter: Optional[List[str]] = None, day_class: Optional[str] = None, line_filter: Optional[str] = None) -> Dict[str, Any]:
    """
    Calculates duplicate-free cancellation statistics.
    """
    conn = get_connection()
    try:
        cte_params = [date_from, date_to]
        filter_clause, filter_params = _build_filter_clause(date_from, date_to, routes, stop_filter, day_class, line_filter)
        
        # Robust Date Casting: Ensure we use DATE type for comparison to be safe
        filter_clause = filter_clause.replace('v.date', 'v.date_dt')
        
        query = f"""
        WITH filtered_data AS (
            SELECT
                v.trip_id,
                v.is_cancelled,
                v.arrival_status
            FROM vbl_data v
            LEFT JOIN (
                SELECT 
                    trip_id, 
                    date, 
                    arg_min(stop_name, departure_planned) as start_name, 
                    arg_max(stop_name, arrival_planned) as end_name,
                    arg_min(stop_name, departure_planned) || ' » ' || arg_max(stop_name, arrival_planned) as route_name
                FROM vbl_data 
                WHERE CAST(date AS DATE) >= CAST(? AS DATE) AND CAST(date AS DATE) <= CAST(? AS DATE)
                GROUP BY trip_id, date
            ) tr ON v.trip_id = tr.trip_id AND v.date = tr.date
            WHERE {filter_clause}
        )
        SELECT
            COUNT(DISTINCT CASE 
                WHEN is_cancelled = true 
                  OR CAST(is_cancelled AS VARCHAR) IN ('true', 'True', '1', 't') 
                THEN trip_id 
            END) as cancelled_trips,
            COUNT(DISTINCT trip_id) as total_trips
        FROM filtered_data
        """
        
        # Params: CTE subquery (2) + Filter clause params (2 + N)
        results = conn.execute(query, cte_params + filter_params).fetchone()
        
        cancelled = results[0] if results[0] else 0
        total = results[1] if results[1] else 0
        
        logger.info(f"DEBUG CANCELLATION: Found {cancelled} cancelled trips in range {date_from} to {date_to}")

        rate = round((cancelled / total) * 100, 2) if total > 0 else 0.0
        
        return {
            "total_cancelled_trips": cancelled,
            "total_trips": total,
            "cancellation_rate": rate
        }
    except Exception as e:
        logger.error(f"Error stats cancellations: {e}")
        return {"total_cancelled_trips": 0, "cancellation_rate": 0.0}
    finally:
        pass # Global connection preserved

def get_problematic_stops(date_from: str, date_to: str, routes: Optional[List[str]] = None, stops: Optional[List[str]] = None, day_class: Optional[str] = None, line_filter: Optional[str] = None, metric_type: str = "arrival", time_from: Optional[str] = None, time_to: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Returns statistics for stops where delays often occur.
    """
    conn = get_connection()
    try:
        col_planned = "v.arrival_planned" if metric_type == "arrival" else "v.departure_planned"
        col_actual = "v.arrival_actual" if metric_type == "arrival" else "v.departure_actual"
        
        cte_params = [date_from, date_to]
        filter_clause, filter_params = _build_filter_clause(date_from, date_to, routes, stops, day_class, line_filter, time_from, time_to)
        
        query = f"""
        WITH trip_routes AS (
            SELECT
                trip_id,
                date,
                arg_min(stop_name, departure_planned) as start_name,
                arg_max(stop_name, arrival_planned) as end_name
            FROM vbl_data
            WHERE date >= ? AND date <= ?
            GROUP BY trip_id, date
        ),
        trip_routes_named AS (
            SELECT trip_id, date, start_name || ' » ' || end_name as route_name, start_name, end_name FROM trip_routes
        ),
        stop_stats AS (
            SELECT
                v.stop_name,
                AVG(date_diff('second', {col_planned}, {col_actual})) as avg_delay,
                SUM(CASE WHEN date_diff('second', {col_planned}, {col_actual}) < -60 THEN 1 ELSE 0 END) as early_count,
                SUM(CASE WHEN date_diff('second', {col_planned}, {col_actual}) BETWEEN -60 AND 120 THEN 1 ELSE 0 END) as punctual_count,
                SUM(CASE WHEN date_diff('second', {col_planned}, {col_actual}) BETWEEN 121 AND 300 THEN 1 ELSE 0 END) as late_slight_count,
                SUM(CASE WHEN date_diff('second', {col_planned}, {col_actual}) > 300 THEN 1 ELSE 0 END) as severe_delays,
                COUNT(v.trip_id) as total_stops
            FROM vbl_data v
            JOIN trip_routes_named tr ON v.trip_id = tr.trip_id AND v.date = tr.date
            WHERE v.{metric_type}_status = 'REAL' 
              AND {filter_clause}
            GROUP BY v.stop_name
        )
        SELECT stop_name, avg_delay, early_count, punctual_count, late_slight_count, severe_delays, total_stops
        FROM stop_stats
        WHERE total_stops > 20 -- filter out noise (increased threshold)
        ORDER BY severe_delays DESC, avg_delay DESC
        LIMIT 20
        """
        
        results = conn.execute(query, cte_params + filter_params).fetchall()
        
        output = []
        for row in results:
             output.append({
                 "stop_name": row[0],
                 "avg_delay_seconds": round(row[1], 1),
                 "early": row[2],
                 "on_time": row[3],
                 "late_slight": row[4],
                 "late_severe": row[5],
                 "total_trips": row[6],
                 "pct_early": round((row[2]/row[6])*100, 1) if row[6] > 0 else 0,
                 "pct_on_time": round((row[3]/row[6])*100, 1) if row[6] > 0 else 0,
                 "pct_late_slight": round((row[4]/row[6])*100, 1) if row[6] > 0 else 0,
                 "pct_late_severe": round((row[5]/row[6])*100, 1) if row[6] > 0 else 0
             })
             
        return output
    except Exception as e:
        logger.error(f"Error fetching problematic stops: {e}")
        return []
    finally:
        pass # Global connection preserved

def get_worst_trips(date_from: str, date_to: str, routes: Optional[List[str]] = None, stops: Optional[List[str]] = None, day_class: Optional[str] = None, line_filter: Optional[str] = None, time_from: Optional[str] = None, time_to: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Returns top 50 worst trips.
    """
    conn = get_connection()
    try:
        cte_params = [date_from, date_to]
        filter_clause, filter_params = _build_filter_clause(date_from, date_to, routes, stops, day_class, line_filter, time_from, time_to)
        
        query = f"""
        WITH trip_routes AS (
            SELECT
                trip_id,
                date,
                arg_min(stop_name, departure_planned) as start_name,
                arg_max(stop_name, arrival_planned) as end_name
            FROM vbl_data
            WHERE date >= ? AND date <= ?
            GROUP BY trip_id, date
        ),
        trip_routes_named AS (
            SELECT trip_id, date, start_name || ' » ' || end_name as route_name, start_name, end_name FROM trip_routes
        ),
        trip_delays AS (
            SELECT
                v.trip_id,
                v.date,
                v.arrival_planned,
                tr.route_name,
                v.line_name,
                MAX(date_diff('second', v.arrival_planned, v.arrival_actual)) as max_delay
            FROM vbl_data v
            JOIN trip_routes_named tr ON v.trip_id = tr.trip_id AND v.date = tr.date
            WHERE v.arrival_status = 'REAL'
              AND {filter_clause}
            GROUP BY v.trip_id, v.date, v.arrival_planned, tr.route_name, v.line_name
        )
        SELECT trip_id, date, arrival_planned, route_name, line_name, max_delay
        FROM trip_delays
        ORDER BY max_delay DESC
        LIMIT 50
        """
        
        results = conn.execute(query, cte_params + filter_params).fetchall()
        
        output = []
        for tid, date, time, route, line, delay in results:
            output.append({
                "trip_id": tid,
                "date": str(date),
                "time": str(time).split(' ')[1] if ' ' in str(time) else str(time),
                "route": route,
                "line": line,
                "delay_minutes": round(delay / 60, 1)
            })
        return output
    except Exception:
        raise
    finally:
        pass # Global connection preserved

def get_day_class_counts(date_from: str, date_to: str) -> Dict[str, int]:
    """
    Returns the count of distinct days for each day class in the given range.
    """
    conn = get_connection()
    try:
        query = f"""
        SELECT 
            get_day_class(date_dt) as day_class,
            COUNT(DISTINCT date_dt) as day_count
        FROM vbl_data
        WHERE date_dt BETWEEN '{date_from}' AND '{date_to}'
        GROUP BY day_class
        """
        results = conn.execute(query).fetchall()
        return {r[0]: r[1] for r in results}
    except Exception as e:
        logger.error(f"Error calculating day class counts: {e}")
        return {}
    finally:
        pass # Global connection preserved


def get_heatmap_stats(date_from: str, date_to: str, routes: Optional[List[str]] = None, stops: Optional[List[str]] = None, day_class: Optional[str] = None, line_filter: Optional[str] = None, metric_type: str = "arrival", time_from: Optional[str] = None, time_to: Optional[str] = None, granularity: Optional[str] = None, trip_type_regular: bool = False) -> Dict[str, Any]:
    """
    Returns stats for Heatmap with Advanced Metrics (Percentiles P1-P5).
    Strict Granularity Logic:
    - 'trip': Returns individual trips (No aggregation).
    - 'pattern': Returns aggregated pattern stats.
    - None/'60'/int: Returns time-bucketed aggregation (Standard Heatmap).
    """
    conn = get_connection()
    try:
        # Fallback Logic: If granularity is not set, default to "60" (Standard Heatmap).
        # We consciously avoid auto-switching to 'pattern' or 'trip' based on date range here 
        # to verify strict parameter adherence.
        if granularity is None:
            granularity = "60"

        # Validate Inputs: Need at least Line OR Route
        if (not routes or len(routes) == 0) and not line_filter:
            return {"error": "Please select a line or route"}
            
        # --- DEBUG LOGGING ---
        print(f"DEBUG: get_heatmap_stats called")
        print(f"  Granularity: {granularity}")
        print(f"  Time Window: {time_from} - {time_to}")
        print(f"  Date Range : {date_from} - {date_to}")
        print(f"  Routes     : {routes}")
        print(f"  Line       : {line_filter}")
        # ---------------------

        cfg = get_app_config()
        t_early = int(cfg.get('threshold_early', -60))
        t_late = int(cfg.get('threshold_late', 180))
        t_crit = int(cfg.get('threshold_critical', 300))
        
        col_planned = "v.arrival_planned" if metric_type == "arrival" else "v.departure_planned"
        col_actual = "v.arrival_actual" if metric_type == "arrival" else "v.departure_actual"
        
        filter_clause, filter_params = _build_filter_clause(date_from, date_to, routes, stops, day_class, line_filter, time_from, time_to)
        
        # 1. Determine Stop Sequence (Row Order)
        
        # Determine strict route for stop ordering
        primary_route = routes[0] if routes and len(routes) > 0 else None
        
        # Fallback: Find the most frequent route for this line if only line_filter is present
        if not primary_route and line_filter:
             sub = f"""
             WITH trip_routes AS (
                SELECT 
                    trip_id,
                    arg_min(stop_name, stop_sequence) as start_name,
                    arg_max(stop_name, stop_sequence) as end_name
                FROM vbl_data_enriched
                WHERE line_name = ? AND date >= ? AND date <= ?
                GROUP BY trip_id
             )
             SELECT start_name || ' » ' || end_name as r_name, COUNT(*) as c
             FROM trip_routes
             GROUP BY r_name ORDER BY c DESC LIMIT 1
             """
             try:
                 r_row = conn.execute(sub, [line_filter, date_from, date_to]).fetchone()
                 if r_row:
                     primary_route = r_row[0]
             except Exception:
                 pass

        if not primary_route:
             # Fallback if still no route: Just list distinct stops -> try to order by sequence across all trips
             structure_query = """
             SELECT stop_name, AVG(stop_sequence) as avg_seq
             FROM vbl_data_enriched
             WHERE line_name = ? AND date >= ? AND date <= ?
             GROUP BY stop_name
             ORDER BY avg_seq
             """
             st_params = [line_filter, date_from, date_to]
        else:
             # Standard Sequence Logic: Use stop_sequence from vbl_data_enriched for the selected route
             structure_query = f"""
             WITH relevant_trips AS (
                 SELECT trip_id
                 FROM vbl_data_enriched
                 WHERE date >= ? AND date <= ?
                 GROUP BY trip_id
                 HAVING arg_min(stop_name, stop_sequence) || ' » ' || arg_max(stop_name, stop_sequence) = ?
             )
             SELECT 
                v.stop_name, 
                AVG(v.stop_sequence) as avg_seq 
             FROM vbl_data_enriched v
             JOIN relevant_trips rt ON v.trip_id = rt.trip_id
             WHERE v.date >= ? AND v.date <= ?
             GROUP BY v.stop_name
             ORDER BY avg_seq
             """
             # Params: [date_from, date_to, primary_route, date_from, date_to]
             st_params = [date_from, date_to, primary_route, date_from, date_to]
             
        stop_rows = conn.execute(structure_query, st_params).fetchall()
        ordered_stops = [r[0] for r in stop_rows]
        
        if not ordered_stops:
            return {"stops": [], "data": []}


        # 2. Aggregated Data Query with Percentiles OR Trip View
        
        # Outlier Logic

        outlier_condition = ""
        outlier_params = []
        if cfg.get('ignore_outliers') == 'true':
            out_min = int(cfg.get('outlier_min', -1200))
            out_max = int(cfg.get('outlier_max', 3600))
            outlier_condition = f"AND date_diff('second', {col_planned}, {col_actual}) BETWEEN ? AND ?"
            outlier_params = [out_min, out_max]
        
        if granularity == 'trip':
            # TRIP VIEW: No aggregation, distinct trips as columns
            
            # Additional Filter: Regular trips only?
            trip_type_condition = ""
            if trip_type_regular:
                trip_type_condition = "AND (is_additional IS NULL OR is_additional = FALSE)"

            # DYNAMIC FILTER CONSTRUCTION
            
            where_conditions = ["v.date >= ? AND v.date <= ?", f"v.{metric_type}_status = 'REAL'"]
            query_params = [date_from, date_to]

            # Line Filter
            if line_filter:
                where_conditions.append("v.line_name = ?")
                query_params.append(line_filter)
            
            # --- REFACTOR START: Enhanced Route Filtering (V2) ---
            if routes and len(routes) > 0:
                route_conditions = []
                for r in routes:
                    # Input Parsing: Split by " » " or ">>"
                    parts = []
                    if ' » ' in r:
                        parts = r.split(' » ')
                    elif '»' in r: # Handle tight spacing just in case
                        parts = r.split('»')
                    elif '>>' in r:
                        parts = r.split('>>')
                    
                    if len(parts) >= 2:
                        # Clean whitespace
                        start_stop = parts[0].strip()
                        end_stop = parts[1].strip()
                        
                        # Use wildcards for robustness against minor encoding diffs or spacing
                        # Filter strictly on Start AND End
                        route_conditions.append("(tr.start_name LIKE ? AND tr.end_name LIKE ?)")
                        query_params.extend([f"%{start_stop}%", f"%{end_stop}%"])
                    else:
                        # Fallback: fuzzy match on the whole string
                        route_conditions.append("tr.route_name LIKE ?")
                        clean_r = r.replace('»', '%').replace('>>', '%').strip()
                        query_params.append(f"%{clean_r}%")

                if route_conditions:
                    where_conditions.append(f"({' OR '.join(route_conditions)})")
            # --- REFACTOR END ---

            # Time Filter (Drill-Down Support)
            if time_from:
                # drill-down usually passes specific time window. 
                # We filter on trip_start_time to ensure we capture the specific trip(s)
                where_conditions.append("strftime(tr.trip_start_time, '%H:%M:%S') >= ?")
                query_params.append(time_from)
                print(f"DEBUG SQL: Filtering precise time window start >= {time_from}")

            if time_to:
                where_conditions.append("strftime(tr.trip_start_time, '%H:%M:%S') <= ?")
                query_params.append(time_to)
                print(f"DEBUG SQL: Filtering precise time window end <= {time_to}")

            # Outlier (from config)
            if outlier_condition:
                where_conditions.append(f"1=1 {outlier_condition}") 
            
            final_where_str = " AND ".join(where_conditions)
            
            query_params.extend(outlier_params)
            
            query = f"""
            WITH trip_routes AS (
                SELECT
                    trip_id,
                    date,
                    arg_min(stop_name, stop_sequence) as start_name,
                    arg_max(stop_name, stop_sequence) as end_name,
                    MIN(departure_planned) as trip_start_time,
                    arg_min(block_id, departure_planned) as vehicle_id
                FROM vbl_data_enriched
                WHERE date >= ? AND date <= ? {trip_type_condition}
                GROUP BY trip_id, date
            ),
            trip_routes_named AS (
                SELECT 
                    trip_id, 
                    date, 
                    start_name || ' » ' || end_name as route_name,
                    start_name,
                    end_name,
                    trip_start_time,
                    vehicle_id
                FROM trip_routes
            ),
            trip_data AS (
                SELECT
                    v.stop_name,
                    v.trip_id,
                    v.departure_planned, -- Use for secondary sort
                    tr.trip_start_time,
                    tr.vehicle_id,
                    tr.date,
                    date_diff('second', {col_planned}, {col_actual}) as delay_seconds,
                    v.stop_sequence,
                    'unknown' as status
                FROM vbl_data_enriched v
                JOIN trip_routes_named tr ON v.trip_id = tr.trip_id AND v.date = tr.date
                WHERE {final_where_str}
            )
            SELECT
                trip_id,
                strftime(trip_start_time, '%H:%M') as start_time,
                vehicle_id,
                stop_name,
                delay_seconds,
                status,
                strftime(date, '%d.%m.') as date_short
            FROM trip_data
            ORDER BY trip_start_time, stop_sequence
            """
            
            full_params_list = [date_from, date_to] + query_params
            
            print(f"DEBUG SQL: {query}")
            print(f"DEBUG PARAMS: {full_params_list}")

            results = conn.execute(query, full_params_list).fetchall()
            
            # Post-processing: Pivot to Matrix Grid [Rows=Stops, Cols=Trips]
            
            # 1. Identify Unique Trips (Columns)
            seen_trips = set()
            trip_infos = [] 
            x_labels = []   
            
            # Map: stop_name -> { trip_id -> delay_seconds }
            data_map = {} 
            
            for r in results:
                tid = r[0]
                stime = r[1]
                vid = r[2] if r[2] else ""
                sname = r[3]
                delay = r[4]
                date_short = r[6]
                
                # Register Column if new (maintain order from query)
                instance_id = f"{tid}_{date_short}"
                
                if instance_id not in seen_trips:
                    seen_trips.add(instance_id)
                    # Count distinct trips for header? 
                    # Actually standard way: Time (Vehicle)
                    # We add n=? to header if pattern view, but here is trip view.
                    # Just Time is standard.
                    label = stime
                    
                    trip_infos.append({
                        "id": instance_id,
                        "label": label,
                        "vehicle": vid,
                        "date": date_short, 
                        "course": "" 
                    })
                    x_labels.append(date_short)
                
                # Store Data
                if sname not in data_map:
                    data_map[sname] = {}
                data_map[sname][instance_id] = delay

            # 2. Build Grid
            grid = []
            
            for stop in ordered_stops:
                row = []
                stop_data = data_map.get(stop, {})
                
                for trip in trip_infos:
                    tid_key = trip['id']
                    val = stop_data.get(tid_key) 
                    row.append(val)
                
                grid.append(row)

            return {
                "stops": ordered_stops,   
                "x_labels": x_labels,    
                "trips": trip_infos,     
                "grid": grid             
            }

        else:
            if granularity == 'pattern':
                # PATTERN VIEW
                return get_pattern_stats(
                    date_from, date_to, routes, stops, day_class, 
                    line_filter, metric_type, time_from, time_to, 
                    ordered_stops
                )
            
            # ORIGINAL AGGREGATION LOGIC
            try:
                seconds_per_bucket = int(granularity) * 60
            except ValueError:
                seconds_per_bucket = 3600 # Default to 60 min if invalid
            
            query = f"""
            WITH trip_routes AS (
                SELECT
                    trip_id,
                    date,
                    arg_min(stop_name, departure_planned) as start_name,
                    arg_max(stop_name, arrival_planned) as end_name,
                    MAX(arrival_planned) as last_arrival_time,
                    MIN(departure_planned) as first_departure_time
                FROM vbl_data
                WHERE date >= ? AND date <= ?
                GROUP BY trip_id, date
            ),
            trip_routes_named AS (
                SELECT trip_id, date, start_name || ' » ' || end_name as route_name, start_name, end_name, last_arrival_time, first_departure_time 
                FROM trip_routes
            ),
            raw_delays AS (
                SELECT
                    v.stop_name,
                    strftime(to_timestamp(floor(epoch({col_planned}) / {seconds_per_bucket}) * {seconds_per_bucket}), '%H:%M') as time_slot,
                    date_diff('second', {col_planned}, {col_actual}) as delay_seconds,
                    CASE
                        WHEN date_diff('second', {col_planned}, {col_actual}) < {t_early} THEN 'early'
                        WHEN date_diff('second', {col_planned}, {col_actual}) BETWEEN {t_early} AND {t_late} THEN 'on_time'
                        WHEN date_diff('second', {col_planned}, {col_actual}) BETWEEN {t_late + 1} AND {t_crit} THEN 'late_slight'
                        ELSE 'late_severe'
                    END as status
                FROM vbl_data v
                JOIN trip_routes_named tr ON v.trip_id = tr.trip_id AND v.date = tr.date
                WHERE v.{metric_type}_status = 'REAL' 
                  AND {filter_clause}
                  {outlier_condition}
            )
            SELECT
                stop_name,
                time_slot,
                COUNT(*) as total,
                -- Status Counts
                SUM(CASE WHEN status = 'early' THEN 1 ELSE 0 END) as early,
                SUM(CASE WHEN status = 'on_time' THEN 1 ELSE 0 END) as on_time,
                SUM(CASE WHEN status = 'late_slight' THEN 1 ELSE 0 END) as late_slight,
                SUM(CASE WHEN status = 'late_severe' THEN 1 ELSE 0 END) as late_severe,
                -- Statistics
                AVG(delay_seconds) as avg_delay,
                -- Percentiles: P1(97.5), P2(84), P3(50 - Median), P4(16), P5(2.5)
                quantile_cont(delay_seconds, [0.025, 0.16, 0.50, 0.84, 0.975]) as quantiles
            FROM raw_delays
            GROUP BY stop_name, time_slot
            """
            
            cte_params = [date_from, date_to]
            results = conn.execute(query, cte_params + filter_params + outlier_params).fetchall()
            
            data = []
            for row in results:
                # Unpack quantiles
                qs = row[8] # list
                
                data.append({
                    "stop_name": row[0],
                    "time_slot": row[1],
                    "total": row[2],
                    "early": row[3],
                    "on_time": row[4],
                    "late_slight": row[5],
                    "late_severe": row[6],
                    "avg_delay": round(row[7], 1) if row[7] is not None else 0,
                    "p5": round(qs[0], 1) if qs else 0,
                    "p4": round(qs[1], 1) if qs else 0,
                    "p3": round(qs[2], 1) if qs else 0, # Median
                    "p2": round(qs[3], 1) if qs else 0,
                    "p1": round(qs[4], 1) if qs else 0  # Stress
                })
                
            return {
                "stops": ordered_stops,
                "data": data
            }

    except Exception as e:
        logger.error(f"Error calculating heatmap: {e}")
        return {"stops": [], "data": [], "error": str(e)}
    finally:
        pass # Global connection preserved

def get_pattern_stats(date_from: str, date_to: str, routes: Optional[List[str]] = None, stops: Optional[List[str]] = None, day_class: Optional[str] = None, line_filter: Optional[str] = None, metric_type: str = "arrival", time_from: Optional[str] = None, time_to: Optional[str] = None, ordered_stops: List[str] = []) -> Dict[str, Any]:
    """
    Returns aggregated stats for 'Pattern View' (Fahrplan-Muster-Sicht).
    Aggregates trips by Planned Departure Time (HH:MM) and Route.
    Rows: Stops
    Cols: Unique Patterns (Time + Route)
    """
    conn = get_connection()
    try:
        cfg = get_app_config()
        col_planned = "v.arrival_planned" if metric_type == "arrival" else "v.departure_planned"
        col_actual = "v.arrival_actual" if metric_type == "arrival" else "v.departure_actual"
        
        # Outlier Logic
        outlier_condition = ""
        outlier_params = []
        if cfg.get('ignore_outliers') == 'true':
            out_min = int(cfg.get('outlier_min', -1200))
            out_max = int(cfg.get('outlier_max', 3600))
            outlier_condition = f"AND date_diff('second', {col_planned}, {col_actual}) BETWEEN ? AND ?"
            outlier_params = [out_min, out_max]

        # 1. Pre-Aggregation Filter (Safe context calculation)
        # We MUST NOT filter by time, route, or stop here, because we need the FULL trip to determine its start/end/route-name.
        # Only Date, Line, and DayType are safe to filter at the row level before grouping.
        pre_filter_clause, pre_filter_params = _build_filter_clause(
            date_from, date_to, 
            routes=None, stops=None, # Explicitly valid filtering only
            day_class=day_class, 
            line_filter=line_filter, 
            time_from=None, time_to=None
        )

        # 2. Main Filter (Applied after we have context)
        # This includes all user filters (Time, Route, Stop, etc.)
        # This clause expects 'tr' alias for route info.
        main_filter_clause, main_filter_params = _build_filter_clause(
            date_from, date_to, 
            routes, stops, 
            day_class, line_filter, 
            time_from, time_to
        )
        
        # PATTERN AGGREGATION QUERY
        query = f"""
        WITH trip_details AS (
            SELECT
                trip_id,
                date,
                min(departure_planned) as trip_start_ts,
                arg_min(stop_name, departure_planned) as start_name,
                arg_max(stop_name, arrival_planned) as end_name 
            FROM vbl_data v
            WHERE {pre_filter_clause}
            GROUP BY trip_id, date
        ),
        trip_patterns AS (
            SELECT
                trip_id,
                date,
                start_name || ' » ' || end_name as route_name,
                start_name,
                end_name,
                strftime(trip_start_ts, '%H:%M') as pattern_time
            FROM trip_details
        ),
        pattern_stats AS (
            SELECT
                v.stop_name,
                tr.route_name,
                tr.pattern_time,
                AVG(date_diff('second', {col_planned}, {col_actual})) as avg_delay,
                COUNT(DISTINCT v.date) as trip_count
            FROM vbl_data v
            JOIN trip_patterns tr ON v.trip_id = tr.trip_id AND v.date = tr.date
            WHERE v.{metric_type}_status = 'REAL' 
              AND {main_filter_clause} 
              {outlier_condition}
            GROUP BY v.stop_name, tr.route_name, tr.pattern_time
        )
        SELECT 
            stop_name,
            route_name,
            pattern_time,
            CAST(ROUND(avg_delay) AS INTEGER) as delay,
            trip_count
        FROM pattern_stats
        ORDER BY pattern_time, route_name
        """

        # Params: Pre-filter (for CTE) + Main-filter + Outlier (for main query)
        all_params = pre_filter_params + main_filter_params + outlier_params
        
        results = conn.execute(query, all_params).fetchall()
        
        # Post-Processing: Convert to Grid
        
        # 1. Identify Unique Patterns (Columns) & Metadata
        distinct_patterns = {} # (time, route) -> count (max)
        
        for r in results:
            sname, rname, ptime, delay, count = r
            key = (ptime, rname)
            if key not in distinct_patterns:
                distinct_patterns[key] = count 
            else:
                distinct_patterns[key] = max(distinct_patterns[key], count)
        
        # Sort Patterns
        sorted_keys = sorted(distinct_patterns.keys(), key=lambda x: (x[0], x[1]))
        
        # Build Column Metadata & Index Map
        pattern_infos = []
        key_to_idx = {}
        
        for i, (ptime, rname) in enumerate(sorted_keys):
            cnt = distinct_patterns[(ptime, rname)]
            pattern_infos.append({
                "id": f"{ptime}|{rname}",
                "label": f"{ptime} (n={cnt})",
                "vehicle": rname, 
                "trip_count": cnt
            })
            key_to_idx[(ptime, rname)] = i
            
        x_labels = [p['label'] for p in pattern_infos]
        
        # 2. Build Grid
        grid_map = {stop: [None] * len(pattern_infos) for stop in ordered_stops}
        
        for r in results:
            sname, rname, ptime, delay, count = r
            if sname in grid_map:
                 col_idx = key_to_idx.get((ptime, rname))
                 if col_idx is not None:
                     grid_map[sname][col_idx] = delay
                     
        grid = []
        for stop in ordered_stops:
            grid.append(grid_map[stop])
            
        return {
            "stops": ordered_stops,
            "x_labels": x_labels,
            "trips": pattern_infos, 
            "grid": grid
        }

    except Exception as e:
        logger.error(f"Error calculating pattern stats: {e}")
        return {"stops": [], "grid": [], "error": str(e)}
    finally:
        pass # Global connection preserved

if __name__ == "__main__":
    # Local verification
    print("Testing get_lines()...")
    lines = get_lines()
    print(f"Found {len(lines)} lines.")
    for line, routes in list(lines.items())[:2]:
        print(f"Line {line}:")
        for r in routes[:2]:
            print(f"  - {r}")

    print("\nTesting get_punctuality_stats()...")
    # Use November 2025 where we know data exists
    start_date = "2025-11-01"
    end_date = "2025-11-02"
    
    stats = get_punctuality_stats(start_date, end_date)
    print(f"Stats (no filter): {stats}")
    
    try:
        conn = get_connection()
        # Create a valid route for testing filter
        # Note: We need a query that matches our new logic to get a valid route name
        valid_route_query = f"""
        WITH trip_routes AS (
            SELECT
                trip_id,
                arg_min(stop_name, departure_planned) as start_name,
                arg_max(stop_name, arrival_planned) as end_name
            FROM vbl_data
            WHERE date >= '{start_date}' AND date <= '{end_date}'
            GROUP BY trip_id
        )
        SELECT start_name || ' » ' || end_name as route_name 
        FROM trip_routes 
        LIMIT 1
        """
        valid_route_row = conn.execute(valid_route_query).fetchone()
        # conn.close()
        
        if valid_route_row:
            test_route = valid_route_row[0]
            print(f"\nTesting filter with route: {test_route}")
            # Note: We pass a list because the function expects optional list
            stats_filtered = get_punctuality_stats(start_date, end_date, route_filter=[test_route])
            print(f"Stats (filtered): {stats_filtered}")
            
            if stats_filtered['total'] > 0:
                print("SUCCESS: Filter returned results.")
            else:
                print("WARNING: Filter returned 0 results (unexpected if route exists).")
        else:
            print("\nCould not find a valid route in the date range for testing.")
            
    except Exception as e:
        print(f"Test failed with error: {e}")
