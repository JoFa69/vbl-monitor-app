# DATA_SCHEMA.md – Datenmodell & Mapping

Dieses Dokument definiert die Struktur der Rohdaten (Source) und das Ziel-Schema in DuckDB (Target).

## 1. Source-to-Target Mapping
Eingangsformat: CSV (OpenTransportData `ist-daten-v2`).
Zielformat: Parquet / DuckDB.

| Feldname (CSV Header) | Typ (Raw) | Import? | Ziel-Spalte (DuckDB) | Beschreibung / Nutzung |
| :--- | :--- | :--- | :--- | :--- |
| `_id` | int | Nein | - | Technischer Index DB, irrelevant. |
| `BETRIEBSTAG` | text | **JA** | `date` | **Partition Key.** Betriebstag (DD.MM.YYYY). Muss als Date geparst werden. |
| `FAHRT_BEZEICHNER` | text | **JA** | `trip_id` | Eindeutige ID der Fahrt. |
| `BETREIBER_ID` | text | Nein | - | Redundant zu ABK. |
| `BETREIBER_ABK` | text | **JA** | `agency_id` | **Filter.** Muss `'VBL'` sein. |
| `BETREIBER_NAME` | text | Nein | - | Redundant. |
| `PRODUKT_ID` | text | Nein | - | Meist 'Bus' oder 'Tram'. |
| `LINIEN_ID` | text | **JA** | `line_id` | Technischer Schlüssel der Linie. |
| `LINIEN_TEXT` | text | **JA** | `line_name` | Anzeige im Dashboard (z.B. "1", "6", "N12"). |
| `UMLAUF_ID` | text | **JA** | `block_id` | **Wendezeiten.** Verknüpft Fahrten (Ankunft A -> Abfahrt B). |
| `VERKEHRSMITTEL_TEXT` | text | **JA** | `transport_type` | Z.B. "Bus", "Trolleybus". |
| `ZUSATZFAHRT_TF` | text | **JA** | `is_additional` | Boolean Flag für Verstärkerfahrten. |
| `FAELLT_AUS_TF` | text | **JA** | `is_cancelled` | **KPI.** Wichtig für Ausfallquote. |
| `BPUIC` | text | **JA** | `stop_id_bpuic` | Klassische Haltestellen-ID. |
| `HALTESTELLEN_NAME` | text | **JA** | `stop_name` | Anzeige Name ("Luzern, Bahnhof"). |
| `SLOID` | text | **JA** | `stop_id_sloid` | **Zukunfts-ID.** Eindeutige CH-Haltestellenkante. |
| `ANKUNFTSZEIT` | text | **JA** | `arrival_planned` | HH:MM:SS. Soll-Ankunft. |
| `AN_PROGNOSE` | text | **JA** | `arrival_actual` | HH:MM:SS. Ist-Ankunft (Zeitpunkt des Haltes). |
| `AN_PROGNOSE_STATUS` | text | **JA** | `arrival_status` | Filter: Nur 'REAL' (gemessene Daten) verwenden. |
| `ABFAHRTSZEIT` | text | **JA** | `departure_planned` | HH:MM:SS. Soll-Abfahrt. |
| `AB_PROGNOSE` | text | **JA** | `departure_actual` | HH:MM:SS. Ist-Abfahrt. |
| `AB_PROGNOSE_STATUS` | text | **JA** | `departure_status` | Filter: Nur 'REAL' verwenden. |
| `DURCHFAHRT_TF` | text | Nein | - | Irrelevant für Halte-Analyse. |
| `SLOID` | text | **JA** | `sloid` | (siehe oben, doppelt in JSON, einmal reicht). |

---

## 2. Ingest-Regeln (für `ingest_data.py`)

Der ETL-Prozess muss beim Laden folgende Transformationen via DuckDB SQL durchführen:

1.  **Filterung:**
    ```sql
    WHERE BETREIBER_ABK = 'VBL'
    ```

2.  **Datums-Parsing:**
    Das Feld `BETRIEBSTAG` liegt oft als String vor (Format prüfen, meist `dd.mm.yyyy`).
    * Transformation: `strptime(BETRIEBSTAG, '%d.%m.%Y')::DATE AS date`

3.  **Zeit-Parsing:**
    Zeitstempel liegen als Strings vor.
    * Transformation (Beispiel): `strptime(AN_PROGNOSE, '%H:%M:%S')::TIME AS arrival_actual`
    * *Achtung:* Bei Fahrten über Mitternacht (z.B. 25:00:00) muss DuckDB dies korrekt behandeln oder als Intervall zum Betriebstag addiert werden.

4.  **Spalten-Selektion:**
    Es dürfen **nur** die oben mit "JA" markierten Spalten im finalen Parquet gespeichert werden, um die Dateigröße minimal zu halten.

## 3. Datenqualität
* **Status-Prüfung:** Zeilen, bei denen `AN_PROGNOSE_STATUS` oder `AB_PROGNOSE_STATUS` **nicht** 'REAL' sind, sollen entweder gefiltert oder (besser) mit einem Flag markiert werden, da sie keine echte Pünktlichkeitsmessung darstellen.