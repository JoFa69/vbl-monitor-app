import duckdb
con = duckdb.connect()
try:
    df = con.execute("SELECT departure_planned FROM 'data/processed/*.parquet' LIMIT 2").fetchdf()
    print("Data sample:")
    print(df)
    print("\nTypes:")
    print(df.dtypes)
except Exception as e:
    print(e)
