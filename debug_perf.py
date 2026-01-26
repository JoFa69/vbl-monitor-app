import duckdb
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_connection

def run_explain():
    conn = get_connection()
    try:
        print("\n--- EXPLAIN ANALYZE (Filter on date) ---")
        query = "EXPLAIN ANALYZE SELECT count(*) FROM vbl_data WHERE date = '2025-11-01'" 
        
        results = conn.execute(query).fetchall()
        
        with open('explain_output.txt', 'w', encoding='utf-8') as f:
            for row in results:
                f.write(str(row) + "\n")
                if len(row) > 1:
                    f.write(str(row[1]) + "\n")
                
        print("EXPLAIN output written to explain_output.txt")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_explain()
