# REQUIREMENTS.md – Fachliche Anforderungen (VBL Pünktlichkeits-Monitor)

Dieses Dokument definiert die Business Logic, Datenmodelle und Analysen für die Pünktlichkeits-Applikation. Es dient als "Single Source of Truth" für die Entwicklung.

---

## 1. Daten-Grundlage & Scope

### 1.1 Datenquelle
* **Portal:** OpenTransportData.swiss
* **Datensatz:** `ist-daten-v2` (Soll- und Ist-Zeiten).
* **Betreiber-Filter:** Nur Daten der `Agency_ID` bzw. `Betreiber_ABK = 'VBL'` (Verkehrsbetriebe Luzern).
* **Format:** CSV (Input), Parquet (Interne Speicherung).

### 1.2 Zeit-Definitionen
* **Betriebstag:** Ein Betriebstag beginnt um **04:00:00 Uhr** und endet um **03:59:59 Uhr** des Folgetages.
* **Mitternachts-Regel:** Fahrten, die nach 00:00 Uhr stattfinden, gehören logisch zum vorangegangenen Datum.
    * *Logik:* Wenn `Ist-Zeit` < `Soll-Zeit` (z.B. Ist 00:05, Soll 23:55) und der Betriebstag identisch ist, muss zur Ist-Zeit **86400 Sekunden** addiert werden, um die Differenz korrekt zu berechnen.

### 1.3 Daten-Qualität & Einschränkungen
* **Ist-Daten (Actual):** Liegen sekundengenau vor (`AN_IST`, `AB_IST`).
* **Soll-Daten (Planned):** Liegen im Export oft nur **minutengenau** vor (`SS:MM:00`).
    * *Konsequenz:* `AN_PROGNOSE` ist meist identisch mit `AB_PROGNOSE` (keine geplante Haltezeit).
    * *Berechnung:* Pünktlichkeit wird dennoch sekundengenau berechnet (`Ist - Soll`).

---

## 2. Modul A: Pünktlichkeits-Analyse (Kundensicht)

### 2.1 Basis-Metrik: Abweichung (Deviation)
Die Anwendung muss dem Nutzer erlauben, dynamisch zwischen zwei Sichtweisen zu wechseln:
1.  **[MUST] Ankunfts-Pünktlichkeit:** Basis `AN_IST - AN_PROGNOSE`.
    * *Use Case:* Anschlüsse, Fahrgast-Sicht am Ziel.
2.  **[MUST] Abfahrts-Pünktlichkeit:** Basis `AB_IST - AB_PROGNOSE`.
    * *Use Case:* Start-Pünktlichkeit, "Bus zu früh weg".

### 2.2 Klassifizierung (Buckets) [MUST]
Jede Fahrt/Haltestelle wird einer Kategorie zugeordnet. Die Schwellenwerte müssen konfigurierbar sein (Default):
* **Zu früh:** < -60 Sek.
* **Pünktlich:** -60 Sek. bis +120 Sek.
* **Leicht verspätet:** +121 Sek. bis +300 Sek.
* **Stark verspätet:** > +300 Sek.
* **Ausfall:** Fahrt im Soll vorhanden, aber keine Ist-Daten (`Status != REAL`).

### 2.3 Aggregations-Ebenen [MUST]
Die Datenbank muss Performanz für `GROUP BY` auf folgenden Ebenen bieten:
1.  **Netz / Teilnetz** (Gesamtübersicht).
2.  **Linie & Richtung** (Hin- vs. Rückweg getrennt).
3.  **Haltestelle** (Punktuelle Betrachtung).
4.  **Fahrt (Kurs)** (Drill-Down auf Einzel-Fahrt).
5.  **Zeit:** Datum, Tageszeit (Stunden-Slices), Wochentagstyp (Mo-Fr, Sa, So).

---

## 3. Modul B: Wendezeiten-Analyse (Betriebliche Sicht)

### 3.1 Verknüpfungs-Logik (Linkage) [MUST]
Identifikation von Wende-Vorgängen durch Verknüpfung von zwei Fahrten:
* **Join-Kriterium:** Identische `Umlauf_ID` (Block ID) + gleiches Fahrzeug/Datum.
* **Logik:** `Ankunft Fahrt A (Endstelle)` -> `Abfahrt Fahrt B (Startstelle)`.

### 3.2 Kennzahlen (KPIs)
* **Geplante Wendezeit:** `Abfahrt_Soll_B - Ankunft_Soll_A`.
* **Effektive Wendezeit:** `Abfahrt_Ist_B - Ankunft_Ist_A`.
* **Wendezeit-Verzehr (Consumption):** `Geplant - Effektiv`. (Positiver Wert = Pause wurde gekürzt).
* **Kritischer Wende-Alarm:** Flag setzen, wenn effektive Wendezeit < **X Minuten** (z.B. 2 Min).

---

## 4. Modul C: Fahr- & Haltezeiten (Strecken-Analyse)

### 4.1 Effektive Haltezeit (Dwell Time) [SHOULD]
* **Berechnung:** `AB_IST - AN_IST` an derselben Haltestelle.
* **Ziel:** Identifikation von Haltestellen mit Problemen beim Fahrgastwechsel (> 45s).

### 4.2 Effektive Fahrzeit (Run Time) [SHOULD]
* **Berechnung:** `AN_IST (Haltestelle N+1)` - `AB_IST (Haltestelle N)`.
* **Vergleich:** `Fahrzeit_Ist` vs. `Fahrzeit_Soll` (sofern Soll > 0).
* **Ziel:** Identifikation von Streckenabschnitten mit Stau/Baustellen (Fahrzeitverlust).

---

## 5. Filter & Eingangs-Parameter

### 5.1 Kalender-Kontext [MUST]
* Import einer CSV-Datei `calendar_special_days.csv`.
* Spalten: `date` (YYYY-MM-DD), `day_type` (z.B. "Ferien", "Feiertag", "Schule").
* Ermöglicht Filterung: "Zeige Pünktlichkeit nur an Schultagen".

### 5.2 UI-Filter [MUST]
* **Zeitraum:** Date-Picker (von/bis).
* **Uhrzeit:** Time-Range-Slider (z.B. 06:00 - 09:00 für HVZ).
* **Toleranz:** Slider zum Anpassen der "Pünktlich"-Definition (dynamische Neuberechnung der KPIs).

---

## 6. Visualisierung & Dashboard

### 6.1 Pflicht-Visualisierungen [MUST]
* **Carpet Plot (Heatmap):**
    * X-Achse: Tageszeit (Stunden).
    * Y-Achse: Datum oder Haltestellen-Reihenfolge.
    * Farbe: Verspätungsgrad (Grün -> Rot).
* **Linienprofil (Trajektorie):**
    * Liniendiagramm: Verspätungsaufbau von Start bis Ziel.
* **Zeitreihen-Diagramm:**
    * Trend der Pünktlichkeitsquote (OTP) über Wochen/Monate.

### 6.2 Optionale Visualisierungen [SHOULD/COULD]
* **Top/Flop Listen:** Ranking der schlechtesten 10 Haltestellen/Linien.
* **Boxplot:** Darstellung der Streuung (Min, Max, Median, 95%-Perzentil).

---

## 7. Daten-Ingest (ETL-Strategie)

Da die Quelle (opentransportdata) sehr große Dateien liefert:

1.  **API-Check:** Abfrage der CKAN-API für die URL des aktuellen CSVs.
2.  **Stream & Filter:** Download der CSV -> Sofortige Filterung via DuckDB (`WHERE Betreiber_ABK = 'VBL'`).
3.  **Speicherung:** Speichern als **Parquet** (`/data/processed/YYYY-MM-DD_vbl.parquet`).
4.  **Cleanup:** Sofortiges Löschen der Quell-CSV.
5.  **Automation:** Skript muss "Backfill"-fähig sein (Daten der letzten 180 Tage laden, falls nicht vorhanden).