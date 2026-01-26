import duckdb

def analyze_cancellations():
    con = duckdb.connect(database=':memory:')
    
    # Create view over optimized parquet files
    # Using is_cancelled column per schema
    print("Creating view over data/optimized/**/*.parquet...")
    try:
        con.execute("CREATE VIEW vbl_data AS SELECT * FROM 'data/optimized/**/*.parquet'")
    except Exception as e:
        print(f"Error creating view: {e}")
        return

    # 1. Count Cancellations
    print("\n--- 1. Cancellation Counts ---")
    query_count = """
    SELECT 
        is_cancelled, 
        COUNT(*) as count 
    FROM vbl_data 
    GROUP BY is_cancelled
    """
    try:
        results = con.execute(query_count).fetchall()
        for row in results:
            print(f"is_cancelled: {row[0]}, Count: {row[1]}")
    except Exception as e:
        print(f"Error querying counts: {e}")

    # 2. Correlation with Status
    print("\n--- 2. Status Correlation (for is_cancelled='true') ---")
    # Note: Assuming 'true' string based on typical CSV, but could be boolean or 1/0
    # Let's check what value 'true' actually is from step 1
    
    query_status = """
    SELECT 
        departure_status, 
        arrival_status, 
        COUNT(*) as count 
    FROM vbl_data 
    WHERE is_cancelled = 'true' OR is_cancelled = '1' OR is_cancelled = TRUE
    GROUP BY departure_status, arrival_status
    ORDER BY count DESC
    """
    try:
        results = con.execute(query_status).fetchall()
        if not results:
            print("No cancelled trips found (or is_cancelled filter issue).")
        for row in results:
            print(f"Dep: {row[0]}, Arr: {row[1]}, Count: {row[2]}")
    except Exception as e:
        print(f"Error querying status correlation: {e}")

    # 3. Example Trips
    print("\n--- 3. Example Cancelled Trips ---")
    query_examples = """
    SELECT DISTINCT trip_id
    FROM vbl_data 
    WHERE is_cancelled = 'true' OR is_cancelled = '1' OR is_cancelled = TRUE
    LIMIT 5
    """
    try:
        results = con.execute(query_examples).fetchall()
        for row in results:
            print(f"Trip ID: {row[0]}")
    except Exception as e:
        print(f"Error querying examples: {e}")

if __name__ == "__main__":
    analyze_cancellations()
