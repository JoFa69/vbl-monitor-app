import duckdb
import os
import sys  # <--- DAS HAT GEFEHLT! Wichtig für sys.version
import logging

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Globale Variablen
conn = None
TABLE_NAME = None

def get_merged_config():
    """Lädt die Config sicher aus der DB oder nutzt Defaults."""
    default_config = {
        "outlier_min": "120", 
        "outlier_max": "7200",
        "ignore_outliers": "false"
    }
    
    # Schutz gegen "DB ist nicht da"
    if conn is None:
        logger.warning("ACHTUNG: Datenbank-Verbindung ist nicht aktiv! Nutze Default-Config.")
        return default_config

    try:
        # Versuche Config aus der DB zu laden
        return get_app_config()
    except Exception as e:
        logger.error(f"Fehler beim Laden der Config: {e}")
        return default_config

def _init_db():
    global conn, TABLE_NAME
    
    # Render braucht ein Home-Verzeichnis für DuckDB
    os.environ.setdefault("HOME", "/tmp")

    logger.info(f"DEBUG: Python Version: {sys.version}")

    # 1. Token aus Environment holen (jetzt wieder sauber!)
    token = os.environ.get("MOTHERDUCK_TOKEN")
    
    # Sicherheits-Check
    if not token:
        logger.error("FATAL: Kein MOTHERDUCK_TOKEN gefunden!")
        raise ValueError("MOTHERDUCK_TOKEN fehlt in den Environment Variables.")

    token = token.strip() # Wichtig: Leerzeichen entfernen

    try:
        logger.info("DEBUG: Versuche Verbindung via URL-Parameter (Python 3.11 Fix)...")
        
        # 2. Verbindung aufbauen (Robuste URL-Methode)
        # Wir nutzen f-String, das ist stabiler als config={} Dictionary
        connection_string = f"md:?motherduck_token={token}"
        
        conn = duckdb.connect(connection_string)
        logger.info("DEBUG: Verbindung zur Lobby erfolgreich!")

        # 3. Datenbank auswählen
        # Wir prüfen erst, ob wir Zugriff haben
        dbs_df = conn.sql("SHOW DATABASES").df()
        available_dbs = dbs_df['name'].tolist()
        logger.info(f"DEBUG: Verfügbare Datenbanken: {available_dbs}")

        if "my_db" in available_dbs:
            conn.sql("USE my_db")
            logger.info("DEBUG: 'my_db' ausgewählt.")
            TABLE_NAME = "my_db.main.data_nov25"
        else:
            logger.warning(f"WARNUNG: 'my_db' nicht gefunden! Nutze erste verfügbare: {available_dbs[0]}")
            conn.sql(f"USE {available_dbs[0]}")
            TABLE_NAME = f"{available_dbs[0]}.main.data_nov25"

    except Exception as e:
        logger.error(f"DEBUG FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise e

# --- Hilfsfunktionen für Config (unverändert, aber sicher importiert) ---

def get_app_config():
    if conn is None: return {}
    try:
        # Tabelle erstellen falls nicht existiert
        conn.execute("CREATE TABLE IF NOT EXISTS app_config (key VARCHAR PRIMARY KEY, value VARCHAR)")
        results = conn.execute("SELECT key, value FROM app_config").fetchall()
        return {row[0]: row[1] for row in results}
    except Exception as e:
        logger.error(f"SQL Fehler in get_app_config: {e}")
        return {}

def set_app_config(new_config: dict):
    if conn is None: return
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS app_config (key VARCHAR PRIMARY KEY, value VARCHAR)")
        for k, v in new_config.items():
            # Upsert (Insert or Replace)
            conn.execute("INSERT OR REPLACE INTO app_config VALUES (?, ?)", [str(k), str(v)])
    except Exception as e:
        logger.error(f"SQL Fehler in set_app_config: {e}")

# Dummy für load_calendar_data, falls benötigt
def load_calendar_data(connection):
    pass
