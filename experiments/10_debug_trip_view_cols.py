import duckdb
import os
import pandas as pd

# Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'optimized')
PARQUET_PATH = os.path.join(DATA_DIR, '**', '*.parquet')

def debug_trip_view_columns():
    conn = duckdb.connect(':memory:')
    
    # Init Data
    conn.execute(f"CREATE VIEW vbl_data AS SELECT *, CAST(date AS DATE) as date_dt FROM read_parquet('{PARQUET_PATH}', hive_partitioning=true)")
    
    # Add sequences
    conn.execute("""
        CREATE OR REPLACE VIEW vbl_data_enriched AS
        SELECT 
            *,
            ROW_NUMBER() OVER (PARTITION BY trip_id, date ORDER BY departure_planned ASC) as stop_sequence
        FROM vbl_data
        WHERE (departure_planned IS NOT NULL OR arrival_planned IS NOT NULL)
    """)

    # 1. Select a trip_id that spans multiple days (e.g. from previous run)
    target_trip_id = 'ch:1:sjyid:100619:plan:88613028-fa2c-492f-a8b1-7776da6e9012' 
    # This was the 19:05 trip
    
    print(f"--- Simulating Trip View for Trip ID {target_trip_id} (Range Nov 1-5) ---")
    
    query = """
    WITH trip_routes AS (
        SELECT
            trip_id,
            date,
            MIN(departure_planned) as trip_start_time,
            arg_min(block_id, departure_planned) as vehicle_id
        FROM vbl_data_enriched
        WHERE date >= '2025-11-01' AND date <= '2025-11-05' 
          AND trip_id = ?
        GROUP BY trip_id, date
    ),
    trip_data AS (
        SELECT
            v.trip_id,
            strftime(tr.trip_start_time, '%H:%M') as start_time,
            tr.date,
            strftime(tr.date, '%d.%m.') as date_short
        FROM vbl_data_enriched v
        JOIN trip_routes tr ON v.trip_id = tr.trip_id AND v.date = tr.date
        GROUP BY v.trip_id, tr.trip_start_time, tr.date
    )
    SELECT * FROM trip_data ORDER BY date
    """
    
    results = conn.execute(query, [target_trip_id]).fetchall()
    
    print(f"Found {len(results)} trip instances in DB:")
    for r in results:
        print(r)
        
    # Simulate the Fixed Python Logic
    seen_trips = set()
    trip_infos = []
    
    for r in results:
        tid = r[0]
        stime = r[1]
        date_short = r[3]
        
        instance_id = f"{tid}_{date_short}"
        
        if instance_id not in seen_trips:
            seen_trips.add(instance_id)
            trip_infos.append(f"{instance_id} ({date_short})")
            
    print(f"\nFrontend Columns (Fixed Logic): {len(trip_infos)}")
    for t in trip_infos:
        print(t)

    # Validate
    if len(trip_infos) == len(results):
        print("\n[PASS] Logic correctly showed multiple columns.")
    else:
        print(f"\n[FAIL] Logic collapsed columns! Expected {len(results)}, got {len(trip_infos)}")

if __name__ == "__main__":
    debug_trip_view_columns()
