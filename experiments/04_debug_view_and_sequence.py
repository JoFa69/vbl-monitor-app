import duckdb
import pandas as pd
import os

# ANPASSEN: Pfad zu deiner Parquet-Datei
DATA_PATH = "data/processed/2025-11-17_vbl.parquet"

def debug_view_logic():
    # Check if file exists
    if not os.path.exists(DATA_PATH):
        print(f"FEHLER: Datei nicht gefunden: {DATA_PATH}")
        # Try to find any parquet file in data/processed
        processed_dir = "data/processed"
        if os.path.exists(processed_dir):
            files = [f for f in os.listdir(processed_dir) if f.endswith(".parquet")]
            if files:
                print(f"Versuche stattdessen: {files[0]}")
                backup_path = os.path.join(processed_dir, files[0])
                # We need to update the data path variable effectively for the query
                actual_path = backup_path.replace("\\", "/")
            else:
                return
        else:
            return
    else:
        actual_path = DATA_PATH

    con = duckdb.connect()
    print(f"--- 1. Lade Daten aus {actual_path} ---")
    
    # Wir simulieren exakt den View, den wir im Backend einbauen wollen
    create_view_sql = f"""
    CREATE OR REPLACE VIEW vbl_data_enriched AS
    SELECT 
        *,
        -- Hier passiert die Magie: Nummerierung basierend auf der Zeit
        ROW_NUMBER() OVER (
            PARTITION BY trip_id, date 
            ORDER BY departure_planned ASC
        ) as stop_sequence
    FROM '{actual_path}'
    WHERE departure_planned IS NOT NULL -- Sicherheitshalber
    """
    
    try:
        con.execute(create_view_sql)
        print("VIEW 'vbl_data_enriched' erfolgreich erstellt.\n")
    except Exception as e:
        print(f"Fehler beim Erstellen des Views: {e}")
        return

    # TEST 1: Sequenz-Check für EINE Fahrt
    print("--- 2. Detail-Check: Ist die stop_sequence logisch? ---")
    
    # DEBUG: Schema check
    print("Schema von vbl_data_enriched:")
    print(con.execute("DESCRIBE vbl_data_enriched").df().to_string())

    print("Suche eine Beispielfahrt...")
    
    try:
        # Get a trip that definitely exists
        # We need to handle departure_planned correctly based on schema. 
        # For now, let's just inspect schema and stop, or try a safer query first.
        
        # Determine column type dynamically or just fetch it raw to see
        # type_check = con.execute("SELECT typeof(departure_planned) FROM vbl_data_enriched LIMIT 1").fetchone()[0]
        # print(f"Type of departure_planned: {type_check}")

        sample_query = """
        SELECT 
            stop_name, 
            departure_planned,
            stop_sequence,
            line_name,
            trip_id
        FROM vbl_data_enriched
        WHERE trip_id = (SELECT trip_id FROM vbl_data_enriched LIMIT 1)
        ORDER BY stop_sequence ASC
        """
        
        df_sample = con.execute(sample_query).df()
        print(df_sample.to_string())
        
        # Validierung
        if df_sample.empty:
            print("\nWARNUNG: Keine Daten gefunden!")
        else:
            seq_list = df_sample['stop_sequence'].tolist()
            if seq_list == sorted(seq_list):
                print("\nERFOLG: Die stop_sequence ist korrekt aufsteigend sortiert!")
            else:
                print("\nFEHLER: Die stop_sequence ist durcheinander!")

        # TEST 2: Start/Ziel Ermittlung
        print("\n--- 3. Route-Check: Funktionieren arg_min/arg_max? ---")
        route_query = """
        SELECT 
            trip_id,
            arg_min(stop_name, stop_sequence) as start_stop,
            arg_max(stop_name, stop_sequence) as end_stop,
            COUNT(*) as stop_count
        FROM vbl_data_enriched
        GROUP BY trip_id
        LIMIT 5
        """
        
        df_route = con.execute(route_query).df()
        print(df_route[['start_stop', 'end_stop', 'stop_count']].to_string())
        
    except Exception as e:
        print(f"Fehler bei Tests: {e}")

if __name__ == "__main__":
    debug_view_logic()
