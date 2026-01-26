import sys
import os
sys.path.append(os.getcwd())
import logging
from app.database import get_heatmap_stats, get_connection

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_improvements():
    print("--- Starting Verification ---")
    
    # 1. Get a valid date range and route for testing
    conn = get_connection()
    try:
        # Find a date with data
        row = conn.execute("SELECT MIN(date_dt), MAX(date_dt) FROM vbl_data").fetchone()
        if not row or not row[0]:
            print("ERROR: No data found in DB.")
            return
        
        start_date = row[0].strftime('%Y-%m-%d')
        end_date = row[1].strftime('%Y-%m-%d')
        print(f"Date Range: {start_date} to {end_date}")
        
        # Find a valid route (Trip View target)
        route_row = conn.execute(f"""
            SELECT start_name || ' » ' || end_name 
            FROM (
                SELECT trip_id, arg_min(stop_name, departure_planned) as start_name, arg_max(stop_name, arrival_planned) as end_name
                FROM vbl_data 
                WHERE date >= '{start_date}' AND date <= '{end_date}'
                GROUP BY trip_id
            ) LIMIT 1
        """).fetchone()
        
        if not route_row:
            print("ERROR: No routes found.")
            return
            
        test_route = route_row[0]
        print(f"Test Route: {test_route}")
        
    finally:
        conn.close()

    # 2. Test Trip View Filter
    print("\n--- Testing Trip View Filter ---")
    try:
        result = get_heatmap_stats(
            date_from=start_date,
            date_to=end_date,
            routes=[test_route],
            granularity='trip'
        )
        
        if 'error' in result:
            print(f"Error: {result['error']}")
        else:
            trips = result.get('trips', [])
            print(f"Found {len(trips)} trips.")
            if len(trips) > 0:
                print("SUCCESS: Trip View data returned.")
                # Verify columns
                print(f"Columns: {[t['label'] for t in trips[:3]]} ...")
                # Verify route filtering worked (indirectly via result count > 0)
            else:
                 print("WARNING: Trip View returned 0 trips.")

    except Exception as e:
        print(f"EXCEPTION in Trip View: {e}")

    # 3. Test Pattern View Labels
    print("\n--- Testing Pattern View Labels ---")
    try:
        result = get_heatmap_stats(
            date_from=start_date,
            date_to=end_date,
            routes=[test_route], # Using same route should work for pattern view too
            granularity='pattern'
        )
        
        if 'error' in result:
             print(f"Error: {result['error']}")
        else:
            x_labels = result.get('x_labels', [])
            print(f"X Labels: {x_labels[:3]} ...")
            
            # Check for (n=...)
            if any("(n=" in label for label in x_labels):
                print("SUCCESS: Pattern View labels contain trip counts.")
            else:
                print("FAILURE: Pattern View labels DO NOT contain trip counts.")
                
    except Exception as e:
        print(f"EXCEPTION in Pattern View: {e}")

if __name__ == "__main__":
    verify_improvements()
