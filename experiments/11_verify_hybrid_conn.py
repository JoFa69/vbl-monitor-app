
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import conn, TABLE_NAME, get_connection

print(f"Conn Object: {conn}")
print(f"TABLE_NAME: {TABLE_NAME}")

if conn:
    print("Connection Object exists.")
    try:
        # Check vbl_data view
        count = conn.execute("SELECT COUNT(*) FROM vbl_data").fetchone()[0]
        print(f"vbl_data View Count: {count}")
        
        # Check enrichment
        count_enr = conn.execute("SELECT COUNT(*) FROM vbl_data_enriched").fetchone()[0]
        print(f"vbl_data_enriched View Count: {count_enr}")
        
    except Exception as e:
        print(f"Error querying views: {e}")
else:
    print("ERROR: conn is None")

print("Verification Script Finished.")
