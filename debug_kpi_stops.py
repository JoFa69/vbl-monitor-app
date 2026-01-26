import duckdb
from app.database import get_connection, get_punctuality_stats

def debug_kpi_stops_v2():
    conn = get_connection()
    try:
        print("Debugging KPI Stop Filter V2...")
        
        # 1. Check if Schwanenplatz is a terminal
        print("Checking if 'Luzern, Schwanenplatz' is a terminal...")
        is_term = conn.execute("""
            WITH trip_ends AS (
                SELECT trip_id, stop_name 
                FROM vbl_data 
                WHERE arrival_planned = (SELECT MAX(arrival_planned) FROM vbl_data v2 WHERE v2.trip_id = vbl_data.trip_id)
            )
            SELECT COUNT(*) FROM trip_ends WHERE stop_name = 'Luzern, Schwanenplatz'
        """).fetchone()[0]
        print(f"Trips ending at Schwanenplatz: {is_term}")
        
        # 2. Pick a stop that is definitely NOT a terminal (or rarely)
        # Find stops with high counts but low terminal counts
        stop_check = conn.execute("""
            WITH trip_ends AS (
                SELECT trip_id, stop_name 
                FROM vbl_data 
                WHERE arrival_planned = (SELECT MAX(arrival_planned) FROM vbl_data v2 WHERE v2.trip_id = vbl_data.trip_id)
            ),
            term_counts AS (
                SELECT stop_name, COUNT(*) as term_cnt FROM trip_ends GROUP BY stop_name
            ),
            all_counts AS (
                SELECT stop_name, COUNT(*) as total_cnt FROM vbl_data GROUP BY stop_name
            )
            SELECT a.stop_name, a.total_cnt, COALESCE(t.term_cnt, 0)
            FROM all_counts a
            LEFT JOIN term_counts t ON a.stop_name = t.stop_name
            WHERE a.total_cnt > 1000 AND (COALESCE(t.term_cnt, 0) * 1.0 / a.total_cnt) < 0.01
            LIMIT 1
        """).fetchone()
        
        if stop_check:
            intermediate_stop = stop_check[0]
            print(f"Testing with Intermediate Stop: '{intermediate_stop}' (Total: {stop_check[1]}, Term: {stop_check[2]})")
            
            stats = get_punctuality_stats('2025-11-01', '2025-11-30', stop_filter=[intermediate_stop])
            print(f"KPI Stats for {intermediate_stop}: {stats}")
             
            if stats.get('total', 0) == 0:
                 print("Result: KPI is 0. Confirmed issue for intermediate stops.")
            else:
                 print(f"Result: KPI is {stats['total']}. Logic might be filtering correctly?")
        else:
            print("Could not find a purely intermediate stop (unlikely).")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    debug_kpi_stops_v2()
