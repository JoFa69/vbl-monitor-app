
import sys
import os

# Ensure we can import from the current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db_connector import get_connection

def test_db():
    print("Testing DuckDB Connection...")
    try:
        conn = get_connection()
        print("Verbindung zur DB hergestellt.")
        
        # Original Test
        # result = conn.execute("SELECT 1").fetchone()
        
        # New Test: Count rows in vbl_data
        row_count = conn.execute("SELECT COUNT(*) FROM vbl_data").fetchone()[0]
        
        if row_count > 0:
             print(f"Erfolg! {row_count} Zeilen in 'vbl_data' gefunden.")
        else:
             print("Warnung: Tabelle 'vbl_data' ist leer.")
            
        conn.close()
    except Exception as e:
        print(f"Verbindung fehlgeschlagen: {e}")

if __name__ == "__main__":
    test_db()
