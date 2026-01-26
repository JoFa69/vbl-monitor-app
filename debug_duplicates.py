import duckdb
from app.database import get_connection

def debug_duplicates():
    conn = get_connection()
    try:
        d_from = '2025-11-08' # A Saturday
        
        print(f"Analyzing {d_from} for duplicates...")
        
        # 1. Check if multiple rows exist for the same trip_id, date, arrival_planned
        query_dupes = f"""
        SELECT trip_id, arrival_planned, COUNT(*) as cnt
        FROM vbl_data
        WHERE date_dt = '{d_from}'
        GROUP BY trip_id, arrival_planned
        HAVING cnt > 1
        ORDER BY cnt DESC
        LIMIT 5
        """
        dupes = conn.execute(query_dupes).fetchall()
        if dupes:
            print("WARNING: Found duplicates for (trip_id, arrival_planned):")
            for tid, arr, cnt in dupes:
                print(f"  {tid} @ {arr}: {cnt} rows")
        else:
            print("SUCCESS: No duplicates found for (trip_id, arrival_planned).")

        # 2. Check if Last Stop logic selects multiple rows per trip
        query_last_stop_dupes = f"""
        WITH trip_routes AS (
            SELECT
                trip_id,
                MAX(arrival_planned) as last_arrival_time
            FROM vbl_data
            WHERE date_dt = '{d_from}'
            GROUP BY trip_id
        )
        SELECT v.trip_id, COUNT(*) as cnt
        FROM vbl_data v
        JOIN trip_routes tr ON v.trip_id = tr.trip_id
        WHERE v.date_dt = '{d_from}'
          AND v.arrival_status = 'REAL'
          AND v.arrival_planned = tr.last_arrival_time
        GROUP BY v.trip_id
        HAVING cnt > 1
        LIMIT 5
        """
        last_dupes = conn.execute(query_last_stop_dupes).fetchall()
        if last_dupes:
             print("WARNING: Last Stop Filter selects multiple rows for single trip:")
             for tid, cnt in last_dupes:
                 print(f"  {tid}: {cnt} rows")
        else:
             print("SUCCESS: Last Stop Filter selects exactly one row per trip (with REAL data at end).")

        # 3. Check Lines aggregation
        print("\nChecking get_lines() counts (Aggregated globally):")
        # Global count
        lines_query = """
        SELECT line_name, COUNT(DISTINCT trip_id) as distinct_ids, COUNT(*) as total_rows
        FROM vbl_data
        GROUP BY line_name
        LIMIT 3
        """
        l_res = conn.execute(lines_query).fetchall()
        for l, d, t in l_res:
             print(f"Line {l}: {d} distinct IDs, {t} total rows")
             
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    debug_duplicates()
