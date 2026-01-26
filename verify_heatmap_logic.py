import sys
import os
sys.path.append(os.getcwd())

from app.database import get_heatmap_stats, get_connection

def test_heatmap_direct():
    print("Testing get_heatmap_stats directly...")
    
    # 1. Get a valid route/date (hardcoded based on knowledge or query)
    try:
        conn = get_connection()
        # Find a trip to get a valid date and route
        trip = conn.execute("SELECT * FROM vbl_data_enriched LIMIT 1").fetchone()
        conn.close()
        
        if not trip:
            print("No data in DB.")
            return

        # Assuming trip has columns: ..., date_dt, ...
        # View columns: "..., date_dt, stop_sequence"
        # Let's print columns to be sure of indices if needed, or just hardcode if we know data exists.
        # User mentioned 2025-11-01 in previous context.
        
        test_date = "2025-11-01"
        
        print(f"Requesting Heatmap for {test_date} (trip view)...")
        # Route? We need a valid route name.
        # Let's verify with explicit route "Emmenbrücke Sprengi » Luzern, Bahnhof" if it exists, or wildcard.
        # Actually, let's just query for A route.
        
        conn = get_connection()
        r = conn.execute(f"SELECT start_name || ' » ' || end_name FROM vbl_data_enriched WHERE date_dt = '{test_date}' LIMIT 1").fetchone()
        conn.close()
        
        route_filter = None
        if r:
            route_filter = [r[0]]
            print(f"Using Route: {route_filter}")
        else:
            print("No route found for test date, trying without route filter (might be empty result due to validation)")
            # database.py requires route or line
            return

        stats = get_heatmap_stats(
            date_from=test_date,
            date_to=test_date,
            routes=route_filter,
            granularity="trip"
        )
        
        if "error" in stats:
            print(f"Error returned: {stats['error']}")
        else:
            grid = stats.get("grid", [])
            print(f"Success! Grid size: {len(grid)} rows x {len(grid[0]) if grid else 0} cols")
            if grid:
                print("First row samples:", grid[0][:5])
            
            # Verify stop order? 
            stops = stats.get("stops", [])
            if stops:
                print(f"Stops ({len(stops)}):", stops[:3], "...", stops[-3:])
                
    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_heatmap_direct()
