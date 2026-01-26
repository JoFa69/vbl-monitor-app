import duckdb
import os
import sys

def migrate():
    print("Starting migration to Hive Partitioning...")
    
    # Define paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_path = os.path.join(base_dir, 'data', 'processed', '*.parquet').replace(chr(92), chr(47))
    target_dir = os.path.join(base_dir, 'data', 'optimized')
    
    # Ensure target directory exists (DuckDB creates it usually, but good practice)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        
    conn = duckdb.connect(':memory:')
    
    try:
        # Check source data first
        print(f"Reading source data from: {source_path}")
        count = conn.sql(f"SELECT COUNT(*) FROM read_parquet('{source_path}')").fetchone()[0]
        print(f"Found {count} rows in source.")
        
        if count == 0:
            print("No data to migrate.")
            return

        # Prepare Query
        # parsing date. Assumes 'date' column exists and is castable to DATE.
        # We need to extract year and month.
        # We assume 'date' is in YYYY-MM-DD format if string.
        
        query = f"""
            COPY (
                SELECT 
                    *,
                    YEAR(CAST(date AS DATE)) as year,
                    MONTH(CAST(date AS DATE)) as month
                FROM read_parquet('{source_path}')
            ) 
            TO '{target_dir.replace(chr(92), chr(47))}' 
            (FORMAT PARQUET, PARTITION_BY (year, month), OVERWRITE_OR_IGNORE)
        """
        
        print("Executing COPY command (this may take a moment)...")
        conn.execute(query)
        
        print(f"Migration finished. New structure created in: {target_dir}")
        print("Structure verification:")
        # List some created folders
        subdirs = [d for d in os.listdir(target_dir) if os.path.isdir(os.path.join(target_dir, d))]
        print(f"Found year partitions: {subdirs}")
        
    except Exception as e:
        print(f"Migration FAILED: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
