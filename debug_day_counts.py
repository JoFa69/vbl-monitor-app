import duckdb
from app.database import get_connection

def debug_counts():
    print("Connecting to DB...")
    try:
        conn = get_connection()
        
        # Define range (using November 2025 as known data presence)
        d_from = '2025-11-01'
        d_to = '2025-11-30'
        
        print(f"Checking counts for {d_from} to {d_to}...")
        
        query = f"""
        SELECT 
            get_day_class(date_dt) as day_class,
            COUNT(DISTINCT date_dt) as day_count,
            COUNT(*) as trip_count
        FROM vbl_data
        WHERE date_dt BETWEEN '{d_from}' AND '{d_to}'
        GROUP BY day_class
        ORDER BY day_class
        """
        
        results = conn.execute(query).fetchall()
        print("\nDay Class Counts:")
        for dc, days, trips in results:
            print(f"- {dc}: {days} days, {trips} trips")
            
        print("\nDetailed Day List:")
        data = conn.execute(f"""
            SELECT DISTINCT date_dt, get_day_class(date_dt) 
            FROM vbl_data 
            WHERE date_dt BETWEEN '{d_from}' AND '{d_to}'
            ORDER BY date_dt
        """).fetchall()
        for d, c in data:
            print(f"{d} -> {c}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_counts()
