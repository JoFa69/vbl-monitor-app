
import duckdb
import os
from app.database import get_connection

def debug_routes():
    conn = get_connection()
    try:
        # Get a sample route
        query = """
        WITH trip_routes AS (
            SELECT
                trip_id,
                arg_min(stop_name, departure_planned) as start_name,
                arg_max(stop_name, arrival_planned) as end_name
            FROM vbl_data
            WHERE date >= '2025-11-01' AND date <= '2025-11-02'
            GROUP BY trip_id
        )
        SELECT start_name || ' » ' || end_name as route_name
        FROM trip_routes
        LIMIT 1
        """
        result = conn.execute(query).fetchone()
        if result:
            route_db = result[0]
            print(f"DB Route: {repr(route_db)}")
            
            # Simulated Input
            route_input = "Ebikon, Fildern » Obernau, Dorf"
            # Try to construct the DB one if it matches
            
            print(f"Input:    {repr(route_input)}")
            print(f"Match?    {route_db == route_input}")
            
            # Check length and chars
            print(f"DB Len: {len(route_db)}, Input Len: {len(route_input)}")
            for i, c in enumerate(route_db):
                print(f"DB[{i}]: {repr(c)} {ord(c)}")
                
    except Exception as e:
        print(e)
    finally:
        conn.close()

if __name__ == "__main__":
    debug_routes()
