import duckdb
from app.database import get_connection

def debug_saturday():
    conn = get_connection()
    try:
        d_from = '2025-11-01'
        d_to = '2025-11-30'
        
        # 1. Check raw counts per date for Saturdays
        print("Raw Counts (Rows) for 'Samstag':")
        query_raw = f"""
        SELECT date_dt, COUNT(*) 
        FROM vbl_data 
        WHERE date_dt BETWEEN '{d_from}' AND '{d_to}' 
          AND get_day_class(date_dt) = 'Samstag'
        GROUP BY date_dt
        ORDER BY date_dt
        """
        raw_rows = conn.execute(query_raw).fetchall()
        for d, c in raw_rows:
            print(f"{d}: {c} rows")
            
        # 2. Check Trips per date for Saturdays (using get_stats_by_hour logic mimic)
        print("\nTrips per date for 'Samstag' (Last Stop Logic):")
        query_trips = f"""
        WITH trip_routes AS (
            SELECT
                trip_id,
                MAX(arrival_planned) as last_arrival_time
            FROM vbl_data
            WHERE date >= '{d_from}' AND date <= '{d_to}'
            GROUP BY trip_id
        )
        SELECT v.date_dt, COUNT(*) 
        FROM vbl_data v
        JOIN trip_routes tr ON v.trip_id = tr.trip_id
        WHERE v.date >= '{d_from}' AND v.date <= '{d_to}'
          AND v.arrival_status = 'REAL'
          AND v.arrival_planned = tr.last_arrival_time
          AND get_day_class(v.date_dt) = 'Samstag'
        GROUP BY v.date_dt
        ORDER BY v.date_dt
        """
        raw_trips = conn.execute(query_trips).fetchall()
        for d, c in raw_trips:
            print(f"{d}: {c} trips")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    debug_saturday()
