import duckdb
import os

def main():
    # Define paths
    # Using wildcard to load all processed parquet files
    parquet_path = 'data/processed/*.parquet' 
    output_path = 'experiments/debug_sequences.csv'

    # Check if input files exist (rudimentary check)
    import glob
    if not glob.glob(parquet_path):
        print(f"Error: No files found at {parquet_path}")
        return

    print(f"Connecting to DuckDB and loading {parquet_path}...")
    con = duckdb.connect(database=':memory:')

    # Create the view vbl_data_enriched
    # PARTITION BY trip_id, date to ensure uniqueness per trip instance
    # ORDER BY departure_planned to determine sequence
    print("Creating view vbl_data_enriched...")
    con.execute(f"""
        CREATE OR REPLACE VIEW vbl_data_enriched AS
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY trip_id, date
                ORDER BY COALESCE(departure_planned, arrival_planned) ASC
            ) as stop_sequence
        FROM '{parquet_path}'
        WHERE (departure_planned IS NOT NULL OR arrival_planned IS NOT NULL)
    """)

    # Query and export the data
    # Filter for line 4
    # Format departure_planned as HH:MM:SS
    print(f"Exporting sequence data for Line 4 to {output_path}...")
    
    query = """
        SELECT
            date,
            trip_id,
            line_name,
            stop_sequence,
            stop_name,
            strftime(departure_planned, '%H:%M:%S') as departure_planned_str
        FROM vbl_data_enriched
        WHERE line_name = '4'
        ORDER BY date, trip_id, stop_sequence
    """

    con.execute(f"COPY ({query}) TO '{output_path}' (HEADER, DELIMITER ',')")
    
    print("Export complete.")

if __name__ == "__main__":
    main()
