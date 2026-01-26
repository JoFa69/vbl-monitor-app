
import os
import sys
import duckdb
import csv
from collections import defaultdict

# Add project root to path
sys.path.append(os.getcwd())

from app.database import get_connection

def run_aggregation_lab():
    print("--- Lab: Aggregation Analysis ---")
    
    # Parameters
    LINE_ID = '1'
    DATE_FROM = '2025-11-01'
    DATE_TO = '2025-11-30'
    TIME_FROM = '07:00:00'
    TIME_TO = '08:00:00'
    
    conn = get_connection()
    
    try:
        # Step 1: Fetch Raw Data
        print(f"Fetching raw trips for Line {LINE_ID} between {DATE_FROM} and {DATE_TO} ({TIME_FROM}-{TIME_TO})...")
        
        query = f"""
        WITH raw_trips AS (
            SELECT
                trip_id,
                date_dt as date,
                min(departure_planned) as trip_start,
                -- We need route name: Start » End
                arg_min(stop_name, departure_planned) || ' » ' || arg_max(stop_name, arrival_planned) as route_name,
                count(distinct stop_name) as stop_count,
                
                -- Aggregating delays for stats
                min(date_diff('second', arrival_planned, arrival_actual)) as min_delay,
                max(date_diff('second', arrival_planned, arrival_actual)) as max_delay,
                avg(date_diff('second', arrival_planned, arrival_actual)) as avg_delay
            FROM vbl_data
            WHERE line_name = '{LINE_ID}'
              AND date_dt >= '{DATE_FROM}' AND date_dt <= '{DATE_TO}'
            GROUP BY trip_id, date_dt
        )
        SELECT 
            trip_id,
            date,
            strftime(trip_start, '%H:%M') as pattern_time,
            CAST(trip_start AS TIME) as exact_time,
            route_name,
            stop_count,
            min_delay,
            max_delay,
            avg_delay
        FROM raw_trips
        WHERE CAST(trip_start AS TIME) >= '{TIME_FROM}' 
          AND CAST(trip_start AS TIME) <= '{TIME_TO}'
        ORDER BY exact_time, date
        """
        
        results = conn.execute(query).fetchall()
        
        # Manually map results to list of dicts
        trips = []
        for r in results:
            trips.append({
                "trip_id": r[0],
                "date": r[1],
                "pattern_time": r[2],
                "exact_time": r[3],
                "route_name": r[4],
                "stop_count": r[5],
                "min_delay": r[6],
                "max_delay": r[7],
                "avg_delay": r[8] if r[8] is not None else 0
            })
            
        print(f"Loaded {len(trips)} individual trips.")
        
        if len(trips) == 0:
            print("No trips found.")
            return

        # Step 2: Simulate Aggregation (Cluster by Time + Route)
        clusters = defaultdict(list)
        for t in trips:
            key = (t['pattern_time'], t['route_name'])
            clusters[key].append(t)
            
        print("\n--- Cluster Analysis ---\n")
        
        # Sort clusters by time
        sorted_keys = sorted(clusters.keys(), key=lambda x: (x[0], x[1]))
        
        output_rows = []
        
        for ptime, rname in sorted_keys:
            group = clusters[(ptime, rname)]
            cluster_name = f"{ptime} Uhr -> {rname}"
            
            count = len(group)
            
            # Outlier Check: Stop Count
            stop_counts = [t['stop_count'] for t in group]
            # Find mode
            from statistics import mode
            try:
                mode_stop_count = mode(stop_counts)
            except:
                mode_stop_count = stop_counts[0]
                
            outliers = [t for t in group if t['stop_count'] != mode_stop_count]
            
            outlier_info = "None"
            if outliers:
                unique_deviants = set(t['stop_count'] for t in outliers)
                outlier_info = f"{len(outliers)} trips with deviant stop counts: {unique_deviants}"
            
            # Stats
            avg_delay = sum(t['avg_delay'] for t in group) / len(group)
            
            print(f"Cluster: {cluster_name}")
            print(f"  - Count: {count} trips")
            print(f"  - Stop Count Mode: {mode_stop_count}")
            if outliers:
                 print(f"  - WARNING: Found outliers! {outlier_info}")
                 print(f"    IDs: {[t['trip_id'] for t in outliers[:3]]}...")
                 
            output_rows.append({
                "Cluster": cluster_name,
                "Time": ptime,
                "Route": rname,
                "Count": count,
                "Ref_Stop_Count": mode_stop_count,
                "Outlier_Count": len(outliers),
                "Avg_Delay_Sec": round(avg_delay, 1)
            })
            print("-" * 40)
            
        # Save to CSV
        with open("lab_aggregation_results.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=output_rows[0].keys())
            writer.writeheader()
            writer.writerows(output_rows)
            
        print("\nSaved summary to lab_aggregation_results.csv")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    run_aggregation_lab()
