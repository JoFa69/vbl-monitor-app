vbl-monitor/
├── .env                       # Passwörter & Konfiguration (z.B. Pfad zu Daten)
├── .gitignore                 # WICHTIG: Verhindert, dass Daten-Dateien in Git landen
├── DESIGN.md                  # Ihr technisches Konzept
├── REQUIREMENTS.md            # Ihre fachlichen Anforderungen
├── docker-compose.yml         # Startet App & Services
├── Dockerfile                 # Bauplan für den App-Container
├── requirements.txt           # Liste der Python-Pakete (fastapi, duckdb, pandas...)
│
├── app/                       # Der gesamte Quellcode der Web-App
│   ├── main.py                # Einstiegspunkt (FastAPI App Definition)
│   ├── database.py            # DuckDB Verbindung & SQL-Abfragen
│   ├── config.py              # Lädt Einstellungen aus .env
│   │
│   ├── routes/                # Die "Steuerung" (URLs)
│   │   ├── __init__.py
│   │   ├── dashboard.py       # Logik für die HTML-Seiten
│   │   └── api.py             # Logik für JSON-Daten (für Charts/HTMX)
│   │
│   ├── templates/             # HTML-Dateien (Jinja2)
│   │   ├── base.html          # Grundgerüst (Header, Footer, CSS-Links)
│   │   ├── dashboard.html     # Die Hauptseite
│   │   └── components/        # Kleine Bausteine für HTMX (z.B. "table_rows.html")
│   │
│   └── static/                # Statische Dateien
│       ├── css/
│       │   └── pico.min.css   # Das Design-Framework
│       └── img/
│
├── data/                      # Hier liegen die Daten (lokal)
│   ├── raw/                   # Temporärer Download-Ordner für ZIP/CSV (wird gelöscht)
│   ├── processed/             # Hier liegen die fertigen .parquet Dateien (Ihre DB)
│   └── references/            # Hier liegt calendar_special_days.csv
│
└── etl_scripts/               # Skripte für Datenbeschaffung
    └── ingest_data.py         # Lädt CSV von OpenData, filtert & speichert als Parquet