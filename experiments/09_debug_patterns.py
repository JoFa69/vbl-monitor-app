import duckdb
import os
import pandas as pd

# Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'optimized')
PARQUET_PATH = os.path.join(DATA_DIR, '**', '*.parquet')

def debug_patterns():
    conn = duckdb.connect(':memory:')
    
    # Init Data
    conn.execute(f"CREATE VIEW vbl_data AS SELECT * FROM read_parquet('{PARQUET_PATH}', hive_partitioning=true)")

    # Check Date Range and Distinct Days for Line 1
    print("Checking Date Range...")
    dates = conn.execute("SELECT MIN(date), MAX(date) FROM vbl_data").fetchone()
    print(f"Date Range: {dates}")
    
    day_count = conn.execute("SELECT COUNT(DISTINCT date) FROM vbl_data WHERE line_name = '1'").fetchone()[0]
    print(f"Distinct Days with Line 1 data: {day_count}")

    # 1. Investigate Trip IDs and Day Types for the fragmented patterns
    print("--- Detailed Inspector: 19:05 vs 19:06 trips (Line 1, Route Obernau -> Ebikon) ---")
    
    query = """
    WITH trip_data AS (
        SELECT 
            trip_id,
            date,
            isodow(date) as dow,
            min(departure_planned) as trip_start,
            arg_min(stop_name, departure_planned) as start_stop,
            arg_max(stop_name, arrival_planned) as end_stop
        FROM vbl_data
        WHERE line_name = '1'
          AND date >= '2025-11-01' AND date <= '2025-11-30'
        GROUP BY trip_id, date
    )
    SELECT
        strftime(trip_start, '%H:%M') as pattern_time,
        trip_start,
        trip_id,
        dow,
        start_stop || ' » ' || end_stop as route
    FROM trip_data
    WHERE strftime(trip_start, '%H:%M') IN ('19:05', '19:06')
      AND route LIKE 'Obernau%Ebikon%'
    ORDER BY trip_start
    """
    
    results = conn.execute(query).df()
    print(results.to_string())
    
    # Check if trip_id shares a prefix
    print("\n--- Trip ID Analysis ---")
    if not results.empty:
        ids = results['trip_id'].tolist()
        split_ids = [str(t).split(':') for t in ids]
        print(f"Sample Split IDs: {split_ids[:3]}")

    # 2. Check "Pattern View" Query Logic specifically (Strict Grouping)
    print("\n--- Simulating Pattern View Logic (Strict Time) ---")
    sim_query = """
    WITH trip_details AS (
        SELECT
            trip_id,
            date,
            min(departure_planned) as trip_start_ts,
            arg_min(stop_name, departure_planned) as start_name,
            arg_max(stop_name, arrival_planned) as end_name 
        FROM vbl_data v
        WHERE line_name = '1'
           AND date >= '2025-11-01' AND date <= '2025-11-30'
        GROUP BY trip_id, date
    ),
    trip_patterns AS (
        SELECT
            trip_id,
            date,
            start_name || ' » ' || end_name as route_name,
            strftime(trip_start_ts, '%H:%M') as pattern_time
        FROM trip_details
    )
    SELECT
        route_name,
        pattern_time,
        COUNT(DISTINCT trip_id) as n_trips_old_bug,
        COUNT(DISTINCT trip_id || date) as n_trips_fixed
    FROM trip_patterns
    WHERE pattern_time BETWEEN '19:00' AND '20:00'
    GROUP BY route_name, pattern_time
    ORDER BY pattern_time
    """
    sim_results = conn.execute(sim_query).df()
    print(sim_results.to_string())

if __name__ == "__main__":
    debug_patterns()
