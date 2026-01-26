# DESIGN.md – Technisches Architektur-Konzept

## 1. Tech-Stack ("Planer-Stack")
* **Backend:** Python (FastAPI)
* **Frontend:** HTML + Jinja2 + HTMX (CSS: Pico.css)
* **Datenbank:** DuckDB (In-Process OLAP)
* **Deployment:** Docker + Docker Compose

## 2. System-Architektur
* **Datenfluss:** Raw CSV (ZIP) -> ETL-Prozess -> Parquet Files -> DuckDB Abfrage -> API -> Frontend.
* **Performance:** Alle Aggregationen finden in DuckDB via SQL statt, nicht in Pandas.

## 3. System-Design (Ordnerstruktur)

So sollten Sie Ihr Projekt auf Ihrer Festplatte anlegen. Kopieren Sie dies, damit die KI weiß, wo welche Datei hingehört.

```text
/vbl-monitor-app
├── /app
│   ├── main.py              # Startpunkt der FastAPI App
│   ├── database.py          # Verbindung zu DuckDB
│   ├── /routes              # Die URLs der Webseite
│   │   ├── dashboard.py     # Logik für Startseite
│   │   └── analysis.py      # Logik für Wendezeiten
│   ├── /templates           # Jinja2 HTML-Dateien
│   │   ├── base.html        # Grundgerüst (Header/Footer)
│   │   ├── dashboard.html   # Inhalt Startseite
│   │   └── components/      # Wiederverwendbare Teile (z.B. Tabellenzeilen)
│   └── /static              # CSS (Pico.css), Bilder, Logos
├── /data
│   ├── raw/                 # Hier liegen die ZIPs/CSVs (werden nicht in Git committet!)
│   └── processed/           # Hier liegen die .parquet Dateien (die "Datenbank")
├── /etl_scripts
│   └── ingest_data.py       # Skript: Liest CSV, wendet Logik an, speichert Parquet
├── Dockerfile               # Bauplan für den App-Container
├── docker-compose.yml       # Startet die App
├── requirements.txt         # Liste der Python-Pakete (fastapi, duckdb, uvicorn...)
└── .env                     # Passwörter & Konfiguration

```

## 4. Fachliche Anforderungen
Die spezifischen Berechnungsregeln, Metriken und Logiken sind im Dokument `REQUIREMENTS.md` definiert und müssen strikt befolgt werden.
