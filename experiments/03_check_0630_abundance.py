
import duckdb
import os
import glob

# Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'optimized')

def check_0630_abundance():
    print("--- 06:30 Abundance Check ---")
    
    try:
        conn = duckdb.connect(database=':memory:')
        
        # Load Data
        parquet_path = os.path.join(DATA_DIR, '**', '*.parquet').replace(chr(92), chr(47))
        print(f"Loading data from: {parquet_path}")
        conn.execute(f"CREATE OR REPLACE VIEW vbl_data AS SELECT *, CAST(date AS DATE) as date_dt FROM read_parquet('{parquet_path}', hive_partitioning=true)")
        
        # 1. Main Query: Count unique days with trips at 06:30
        # Assuming we are looking for ANY route/trip. 
        # If user meant a specific route, we should probably check overall first or ask. 
        # The prompt implies "certain route" but doesn't specify which one, so I will analyze ALL data first
        # to see if 06:30 is generally populated.
        
        # Filter for trips departing planned at 06:30:xx
        query_main = """
        SELECT 
            date_dt,
            COUNT(DISTINCT trip_id) as trip_count
        FROM vbl_data
        WHERE strftime(departure_planned, '%H:%M') = '06:30'
        GROUP BY date_dt
        ORDER BY date_dt
        """
        
        results = conn.execute(query_main).fetchall()
        
        total_days = len(results)
        print(f"\n[06:30:00 - 06:30:59]")
        print(f"Total Unique Days with Trips: {total_days}")
        
        if total_days > 0:
            print("\nFirst 10 Days found:")
            for r in results[:10]:
                print(f"  {r[0]} (Trips: {r[1]})")
                
            print("\nLast 10 Days found:")
            for r in results[-10:]:
                print(f"  {r[0]} (Trips: {r[1]})")
        else:
             print("WARNING: No trips found exactly at 06:30.")

        # 2. Neighbors check
        print("\n--- Neighbor Minute Check (06:25 - 06:35) ---")
        query_neighbors = """
        SELECT 
            strftime(departure_planned, '%H:%M') as minute,
            COUNT(DISTINCT trip_id) as total_trips,
            COUNT(DISTINCT date_dt) as unique_days
        FROM vbl_data
        WHERE strftime(departure_planned, '%H:%M') BETWEEN '06:25' AND '06:35'
        GROUP BY minute
        ORDER BY minute
        """
        
        neighbors = conn.execute(query_neighbors).fetchall()
        print(f"{'Minute':<10} | {'Total Trips':<12} | {'Unique Days':<12}")
        print("-" * 40)
        for minute, trip_cnt, day_cnt in neighbors:
            print(f"{minute:<10} | {trip_cnt:<12} | {day_cnt:<12}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_0630_abundance()
