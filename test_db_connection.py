import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from app.database import get_connection

try:
    print("Testing get_connection()...")
    conn = get_connection()
    print("Connection successful.")
    
    print("Testing vbl_data_enriched...")
    res = conn.execute("SELECT * FROM vbl_data_enriched LIMIT 1").fetchall()
    print(f"Enriched View Result: {len(res)} rows")
    if res:
        print("Columns:", [d[0] for d in conn.description])
        
    conn.close()
except Exception as e:
    print(f"CRITICAL FAILIURE: {e}")
    import traceback
    traceback.print_exc()
