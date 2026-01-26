import sys
import os

# Add app to path
sys.path.append(os.getcwd())

from app.database import get_connection

def scan_routes():
    print("--- DEBUG ROUTE NAMES START ---")
    try:
        conn = get_connection()
        
        # 1. Check Date Range for Data Presence
        range_query = "SELECT MIN(date), MAX(date), COUNT(*) FROM vbl_data"
        row = conn.execute(range_query).fetchone()
        print(f"Data Range: {row[0]} to {row[1]} (Total Rows: {row[2]})")

        # 2. Check Routes for Line 2 (Emmenbrücke Sprengi)
        # Assuming Line "2" or similar. Let's find routes containing 'Sprengi' and 'Luzern'
        print("\nSearching for routes like '%Sprengi%' AND '%Luzern%'...")
        
        route_query = """
        WITH trip_routes AS (
             SELECT 
                trip_id,
                date,
                arg_min(stop_name, departure_planned) as start_name,
                arg_max(stop_name, arrival_planned) as end_name
             FROM vbl_data 
             GROUP BY trip_id, date
        )
        SELECT DISTINCT start_name || ' » ' || end_name as r_name
        FROM trip_routes
        WHERE r_name LIKE '%Sprengi%' AND r_name LIKE '%Luzern%'
        LIMIT 20
        """
        rows = conn.execute(route_query).fetchall()
        
        print(f"Found {len(rows)} matching routes:")
        for r in rows:
            print(f"  '{r[0]}'")
            # Encode to see hidden chars
            print(f"   Debug ASCII: {ascii(r[0])}")

        # 3. Check Counts for the target route
        target_route = "Emmenbrücke Sprengi » Luzern, Bahnhof"
        print(f"\nChecking exact match for: '{target_route}'")
        
        count_query = """
        WITH trip_routes_named AS (
             SELECT 
                trip_id,
                start_name || ' » ' || end_name as route_name
             FROM (
                 SELECT trip_id, arg_min(stop_name, departure_planned) as start_name, arg_max(stop_name, arrival_planned) as end_name 
                 FROM vbl_data GROUP BY trip_id
             )
        )
        SELECT COUNT(*) FROM trip_routes_named WHERE route_name = ?
        """
        c = conn.execute(count_query, [target_route]).fetchone()[0]
        print(f"Count for exact string: {c}")

        if c == 0:
            print("Trying with 'Emmenbrücke, Sprengi' (comma)?")
            alt_route = "Emmenbrücke, Sprengi » Luzern, Bahnhof"
            c2 = conn.execute(count_query, [alt_route]).fetchone()[0]
            print(f"Count for '{alt_route}': {c2}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    scan_routes()
