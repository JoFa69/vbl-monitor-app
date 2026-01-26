import sys
import os

sys.path.append(os.getcwd())

from app.database import get_connection

def test_structure():
    print("--- DEBUG STRUCTURE START ---")
    
    # 1. Setup Parameters
    # Use the EXACT string found in previous step (ASCII decoded manually or just copied)
    # The previous output was: 'Emmenbr\xfccke Sprengi \xbb Luzern, Bahnhof'
    # In Python 3 source (utf-8 default), we can write it directly:
    target_route = "Emmenbrücke Sprengi » Luzern, Bahnhof"
    
    # Use wide date range to be safe
    date_from = "2025-10-01"
    date_to = "2025-11-30"

    print(f"Target Route: '{target_route}'")
    
    try:
        conn = get_connection()
        
        # 2. Replicate structure_query EXACTLY from database.py
        structure_query = f"""
        WITH trip_starts AS (
            SELECT trip_id, MIN(departure_planned) as trip_start
            FROM vbl_data
            WHERE date >= ? AND date <= ?
            GROUP BY trip_id
        ),
        route_trips AS (
            SELECT 
                v.trip_id,
                v.stop_name,
                date_diff('second', ts.trip_start, v.arrival_planned) as offset_seconds
            FROM vbl_data v
            JOIN trip_starts ts ON v.trip_id = ts.trip_id
            JOIN (
                 SELECT trip_id, arg_min(stop_name, departure_planned) || ' » ' || arg_max(stop_name, arrival_planned) as route_name
                 FROM vbl_data
                 WHERE date >= ? AND date <= ?
                 GROUP BY trip_id
            ) tr ON v.trip_id = tr.trip_id
            WHERE tr.route_name = ?
        )
        SELECT 
            stop_name, 
            AVG(offset_seconds) as avg_offset 
        FROM route_trips
        GROUP BY stop_name
        ORDER BY avg_offset
        """
        
        st_params = [date_from, date_to, date_from, date_to, target_route]
        print(f"Executing query...")
        
        stop_rows = conn.execute(structure_query, st_params).fetchall()
        
        print(f"Result Rows: {len(stop_rows)}")
        for r in stop_rows:
            print(f" - {r[0]} (offset {r[1]})")
            
        if not stop_rows:
            print("FAILURE: No stops found for structure.")
            
            # Debug: Check if the subquery finds ANY trips for this route
            check_q = """
            SELECT COUNT(*) 
            FROM (
                 SELECT trip_id, arg_min(stop_name, departure_planned) || ' » ' || arg_max(stop_name, arrival_planned) as route_name
                 FROM vbl_data
                 WHERE date >= ? AND date <= ?
                 GROUP BY trip_id
            ) 
            WHERE route_name = ?
            """
            c = conn.execute(check_q, [date_from, date_to, target_route]).fetchone()[0]
            print(f"Subquery Verification Count: {c}")

    except Exception as e:
        print(f"CRASH: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_structure()
