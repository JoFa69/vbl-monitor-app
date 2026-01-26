# VBL Monitor - Projekt Status & Anker (v2.0 React)

**Letztes Update:** 15.01.2026
**Aktueller Fokus:** Wiederherstellung Feature-Parity (Frontend) & Lastteppich-Analyse

## 1. Architektur (Truth Source)
* **Architektur:** Headless (Getrenntes Backend & Frontend).
* **Backend:** Python 3.11 (FastAPI) auf Port **8000**. Liefert reine JSON-Responses.
* **Datenbank:** DuckDB (In-Memory) liest Parquet-Dateien aus `data/optimized/`.
* **Frontend:** **React (Vite)** auf Port **5173**. Styling mit **Tailwind CSS**.
* **Visualisierung:** `react-chartjs-2` (Chart.js).

## 2. Design & Corporate Identity (VBL)
Wir folgen strikt dem VBL Styleguide:
* **Farben UI:**
    * Primary Blue: `#0064a3` (Header, Buttons)
    * Sidebar Dark: `#1A3A4E` (Hintergrund Navigation)
* **Farben Status (Charts):**
    * Zu früh: `#38a8e0` (Hellblau)
    * Pünktlich: `#86bd28` (Grün)
    * Verspätet: `#f8ac36` (Orange)
    * Stark Verspätet: `#e62d2a` (Rot)
* **Formatierung:** Schweizer Zahlenformat (`219'356`), Zeit `HH:MM`.

## 3. Fertige Features (Backend Stable)
* [x] **Daten-Engine:** Parquet Ingest, Hive Partitioning, DuckDB SQL-Optimierung.
* [x] **Business-Logik:** Betriebstag (04:00-03:59), Pünktlichkeits-Schwellenwerte.
* [x] **API Endpoints:** `/stats`, `/hourly`, `/weekday`, `/settings` (GET/POST).
* [x] **Deployment:** Docker-Image enthält nur Code (Stateless). Daten werden per Volume (`-v`) vom Host gemountet (Rancher Desktop kompatibel).

## 4. Aktuelle Baustellen (Frontend React)
Das React-Frontend wurde frisch aufgesetzt, muss aber funktional an die alte Version angeglichen werden ("Gap Analysis"):

* [x] **Layout-Reparatur:**
    * Wiederherstellung der **linken Sidebar** (fixiert, `#1A3A4E`).
    * Alle Filter (Datum, Zeit, Linie, Route, Haltestelle) müssen in die Sidebar.
    * Hinzufügen des **"Basis"-Switch** (Ankunft vs. Abfahrt).
* [x] **Charts korrigieren:**
    * Y-Achse muss **Prozentwerte (0-100%)** zeigen (Stacked 100%).
    * **Tabs** über Charts einfügen: `[Übersicht]` vs. `[Einzel-Kategorien]`.
* [x] **Settings Page:**
    * Formular muss `/api/v1/settings` ansprechen (JSON Body), um HVZ-Zeiten zu speichern.
* [ ] **NEU: Lastteppich (Heatmap):**
    * Matrix-Visualisierung: Haltestellen (Y) vs. Uhrzeit (X).
    * Metrik: Durchschnittliche Verspätung.

## 5. Ordnerstruktur
* `/backend`: FastAPI App (`main.py`, `database.py`).
* `/frontend`: React App (`src/`, `components/`, `package.json`).
* `/data`: (Nicht im Container/Repo) Lokale Parquet-Dateien & `config.json`.