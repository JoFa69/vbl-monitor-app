import duckdb
from app.database import get_connection

def debug_trips():
    print("Connecting to DB...")
    conn = get_connection()
    try:
        d_from = '2025-11-08' # A Saturday
        d_to = '2025-11-08'
        
        print(f"Analyzing {d_from}...")
        
        # 1. Total Rows (Stop events)
        rows = conn.execute(f"SELECT COUNT(*) FROM vbl_data WHERE date_dt = '{d_from}' AND arrival_status = 'REAL'").fetchone()[0]
        print(f"Total REAL Stop Events: {rows}")
        
        # 2. Total Unique Trips (Any REAL data)
        trips = conn.execute(f"SELECT COUNT(DISTINCT trip_id) FROM vbl_data WHERE date_dt = '{d_from}' AND arrival_status = 'REAL'").fetchone()[0]
        print(f"Total Trips with ANY Real Data: {trips}")
        
        # 3. Trips caught by Current Logic (Last Stop has REAL data)
        query_current = f"""
        WITH trip_routes AS (
            SELECT
                trip_id,
                MAX(arrival_planned) as last_arrival_time
            FROM vbl_data
            WHERE date_dt = '{d_from}'
            GROUP BY trip_id
        )
        SELECT COUNT(DISTINCT v.trip_id)
        FROM vbl_data v
        JOIN trip_routes tr ON v.trip_id = tr.trip_id
        WHERE v.date_dt = '{d_from}'
          AND v.arrival_status = 'REAL'
          AND v.arrival_planned = tr.last_arrival_time
        """
        trips_current = conn.execute(query_current).fetchone()[0]
        print(f"Trips with REAL Data at Last Stop: {trips_current}")
        
        loss_pct = round((1 - trips_current / trips) * 100, 1)
        print(f"Data Loss due to Last Stop Filter: {loss_pct}%")

        if loss_pct > 10:
            print("MAJOR ISSUE: We are losing > 10% of trips because the last stop lacks real data.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    debug_trips()
