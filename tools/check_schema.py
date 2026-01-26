import duckdb
import os

try:
    path = os.path.join('data', 'processed', '*.parquet').replace(chr(92), chr(47))
    print(f"Reading from {path}")
    df = duckdb.sql(f"SELECT * FROM read_parquet('{path}') LIMIT 1").df()
    print(df.columns)
    print(df.dtypes)
except Exception as e:
    print(e)
