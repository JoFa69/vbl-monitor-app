import duckdb
try:
    conn = duckdb.connect()
    # Try the standard path
    conn.execute("CREATE VIEW vbl_data AS SELECT * FROM read_parquet('data/optimized/**/*.parquet', hive_partitioning=True)")
    print("Schema:")
    for row in conn.execute('DESCRIBE vbl_data').fetchall():
        print(row)
except Exception as e:
    print(e)
