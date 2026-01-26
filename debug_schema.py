
import duckdb
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'optimized')
parquet_path = os.path.join(DATA_DIR, '**', '*.parquet').replace(chr(92), chr(47))

try:
    conn = duckdb.connect(database=':memory:')
    conn.execute(f"CREATE OR REPLACE VIEW vbl_data AS SELECT *, CAST(date AS DATE) as date_dt FROM read_parquet('{parquet_path}', hive_partitioning=true)")
    
    print("Columns in vbl_data:")
    columns = conn.execute("DESCRIBE vbl_data").fetchall()
    for col in columns:
        print(f"  {col[0]} ({col[1]})")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
