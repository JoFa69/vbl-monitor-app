
import duckdb
import os
import sys

def get_connection():
    """
    Establishes a connection to the DuckDB database.
    Attempts to locate 'vbl_data.duckdb' in the project root.
    """
    # 1. Determine Path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir) # Go up one level
    
    # Path to optimized data
    data_dir = os.path.join(project_root, 'data', 'optimized')
    parquet_path = os.path.join(data_dir, '**', '*.parquet').replace(chr(92), chr(47))

    # 2. Check Existence
    if not os.path.exists(data_dir):
        print(f"Warning: Data directory not found at {data_dir}")
        raise FileNotFoundError(f"Data directory missing: {data_dir}")
    
    # 3. Connect & Initialize
    try:
        conn = duckdb.connect(database=':memory:')
        
        # Create View mimicking app/database.py
        # Start simple: just the view
        # app/database.py: CREATE OR REPLACE VIEW vbl_data AS SELECT *, CAST(date AS DATE) as date_dt FROM read_parquet(...)
        
        query = f"CREATE OR REPLACE VIEW vbl_data AS SELECT *, CAST(date AS DATE) as date_dt FROM read_parquet('{parquet_path}', hive_partitioning=true)"
        # print(f"Executing: {query}") # Debug
        conn.execute(query)
        
        # Also need Day Class Macro? Probably yes for future queries
        # But user demand specifically requested Parquet Support first.
        # Let's add the basic macro to be safe
        conn.execute("""
        CREATE OR REPLACE MACRO get_day_class(my_date) AS
            CASE 
                WHEN isodow(my_date) BETWEEN 1 AND 5 THEN 'Mo-Fr (Schule)'
                WHEN isodow(my_date) = 6 THEN 'Samstag'
                ELSE 'Sonn-/Feiertag'
            END
        """)
        
        return conn
    except Exception as e:
        print(f"Failed to connect/init DB: {e}")
        raise
