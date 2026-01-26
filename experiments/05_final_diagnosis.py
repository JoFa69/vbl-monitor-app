import duckdb
import os
import glob

# PFAD ANPASSEN!
# Try to find a valid parquet file if the default doesn't exist
DATA_PATH = "data/vbl_data.parquet"
if not os.path.exists(DATA_PATH):
    # Fallback to processed data
    potential_files = glob.glob("data/processed/*.parquet")
    if potential_files:
        DATA_PATH = potential_files[-1].replace("\\", "/") # Use the latest ONE
    else:
        # Fallback to optimized data
        potential_files = glob.glob("data/optimized/**/*.parquet", recursive=True)
        if potential_files:
             DATA_PATH = potential_files[0].replace("\\", "/")

def run_diagnosis():
    con = duckdb.connect()
    print(f"--- Diagnose Start: {DATA_PATH} ---")

    # 1. VIEW ERZWINGEN
    print("1. Erstelle View 'vbl_data_enriched' neu...")
    try:
        con.execute(f"""
            CREATE OR REPLACE VIEW vbl_data_enriched AS
            SELECT 
                *,
                row_number() OVER (
                    PARTITION BY trip_id, date 
                    ORDER BY departure_planned ASC
                ) as stop_sequence
            FROM '{DATA_PATH}'
            WHERE departure_planned IS NOT NULL
        """)
        print("   -> OK: View erstellt.")
    except Exception as e:
        print(f"   -> FEHLER beim Erstellen der View: {e}")
        return

    # 2. ROUTEN-CHECK (Simuliert den Split-Filter)
    print("\n2. Teste Route: 'Luzern, Bahnhof » ...'") 
    # Adjusted to match data found in previous run
    start_filter = "Bahnhof"
    end_filter = "Mönchweg"
    
    # Wir simulieren die CTE Logik aus dem Backend
    # Note: We use the view which already has stop_sequence
    query = f"""
    WITH trip_routes AS (
        SELECT 
            trip_id, 
            date,
            arg_min(stop_name, stop_sequence) as start_name,
            arg_max(stop_name, stop_sequence) as end_name,
            MIN(departure_planned) as trip_start_time
        FROM vbl_data_enriched
        WHERE line_name = '4' 
        GROUP BY trip_id, date
    )
    SELECT 
        COUNT(*) as fahrten_gefunden,
        MIN(start_name) as beispiel_start,
        MIN(end_name) as beispiel_end
    FROM trip_routes
    WHERE start_name LIKE '%{start_filter}%' 
      AND end_name LIKE '%{end_filter}%'
    """
    
    try:
        df = con.execute(query).df()
        print("   -> Ergebnis:")
        print(df.to_string())
        
        if df['fahrten_gefunden'].iloc[0] == 0:
            print("\n   WARNUNG: 0 Fahrten gefunden! Der Routen-Filter greift nicht.")
            print("   Mögliche Ursache: Start/Ziel Namen in DB anders als im Filter?")
            # Debug: Was gibt es denn?
            print("   Zeige verfügbare Start/Ziele für Linie 4:")
            debug_q = """
            WITH tr AS (
                SELECT trip_id, date, arg_min(stop_name, stop_sequence) as s, arg_max(stop_name, stop_sequence) as e
                FROM vbl_data_enriched WHERE line_name='4' GROUP BY trip_id, date
            ) SELECT s, e, count(*) as c FROM tr GROUP BY s, e LIMIT 5
            """
            print(con.execute(debug_q).df().to_string())
    except Exception as e:
        print(f"   -> SQL FEHLER: {e}")

    # 3. STOP-REIHENFOLGE CHECK (Y-Achse)
    print("\n3. Prüfe Stop-Reihenfolge für diese Route (Y-Achse)...")
    # Wir holen uns eine echte Trip-ID dieser Route
    stops_query = f"""
    WITH trip_routes AS (
        SELECT trip_id, date, arg_min(stop_name, stop_sequence) as s, arg_max(stop_name, stop_sequence) as e
        FROM vbl_data_enriched
        WHERE line_name = '4' GROUP BY trip_id, date
    ),
    target_trip AS (
        SELECT trip_id FROM trip_routes 
        WHERE s LIKE '%{start_filter}%' AND e LIKE '%{end_filter}%' 
        LIMIT 1
    )
    SELECT stop_sequence, stop_name, departure_planned 
    FROM vbl_data_enriched 
    WHERE trip_id IN (SELECT trip_id FROM target_trip)
    ORDER BY stop_sequence
    """
    
    try:
        df_stops = con.execute(stops_query).df()
        if df_stops.empty:
            print("   -> Keine Stops gefunden (wegen Punkt 2).")
        else:
            print("   -> Stops der Beispiel-Fahrt:")
            print(df_stops[['stop_sequence', 'stop_name']].to_string())
            
            # Check Sortierung
            is_sorted = df_stops['stop_sequence'].is_monotonic_increasing
            print(f"\n   -> Sortierung korrekt (1,2,3...)? {'JA' if is_sorted else 'NEIN'}")
            
            # Check Start/Ziel
            first = df_stops.iloc[0]['stop_name']
            last = df_stops.iloc[-1]['stop_name']
            print(f"   -> Erster Stop: {first} (Erwartet: {start_filter}...)")
            print(f"   -> Letzter Stop: {last} (Erwartet: {end_filter}...)")

    except Exception as e:
        print(f"   -> FEHLER: {e}")

if __name__ == "__main__":
    run_diagnosis()
