# PROJEKT REGELN & STYLEGUIDE

1. FORMATIERUNG (STRIKT EINHALTEN):
   - Zahlen und Einheiten IMMER mit Leerzeichen trennen.
     - Richtig: "120 Sek", "50 %"
     - Falsch: "120Sek", "50%"
   - Zeit-Einheiten:
     - Sekunden immer als "Sek." abkürzen (nicht "s", nicht "sec").
     - Minuten als "Min.".

2. TECHNOLOGIE:
   - Frontend: Tailwind CSS, HTMX.
   - Backend: FastAPI, DuckDB.

3. LAYOUT:
   - Sidebar-First Design.
   - Responsive: Nutze Tailwind Breakpoints (md:, lg:), damit es auf allen Screens passt.
   
   # DOMAIN LOGIC (NIEMALS ÄNDERN OHNE ANWEISUNG)

1. DATEN-DARSTELLUNG:
   - Haltestellen-Namen: Müssen IMMER im Format "Start » Ziel" angezeigt werden (SQL Konkatenierung), um die Fahrtrichtung eindeutig zu machen.
   - Einheiten: "Sek" (mit Leerzeichen), "Min" (mit Leerzeichen).

2. UI-VERHALTEN:
   - Layout: Full-Width (Fluid Layout). Keine fixen Container im Main-Content.
   - Filter: Lange Texte in Dropdowns müssen umbrechen (Wrap Text), nicht abgeschnitten werden.
   
   # TECHNISCHE STABILITÄT

1. JAVASCRIPT & HTMX:
   - Bei Nutzung von 3rd-Party Libs (Chart.js, MapLibre, TomSelect):
   - Initialisierung darf nicht nur bei `window.onload` passieren.
   - Muss AUCH bei `htmx:afterSwap` getriggert werden, damit Elemente nach Navigation neu gerendert werden.
   - Nutze idempotente Funktionen (prüfen, ob Instanz schon existiert, bevor neu erstellt wird).
   
   # REGIONALE KONVENTIONEN (LOCALE)
1. WOCHENTAGE:
   - Der Start der Woche ist IMMER Montag (ISO-8601).
   - Sortierung in Charts/Tabellen: Mo, Di, Mi, Do, Fr, Sa, So.
   - DuckDB Funktion: Nutze `dayofweek(...)` (0=So) nur mit Vorsicht, besser `isodow(...)` (1=Mo ... 7=So) für Sortierung.

2. FILTER-UX:
   - Breite Filter (z.B. Routen) dürfen die Sidebar nicht sprengen.
   - Lösung: Nutze "Flyout"-Menüs oder "Popovers", die sich bei Klick nach rechts über den Main-Content öffnen.
   
   # CRITICAL SYSTEM RULES (DO NOT TOUCH)

1. DATA LOADING:
   - Wir nutzen Hive Partitioning: `read_parquet('data/optimized/**/*.parquet', hive_partitioning=true)`.
   - Ändere NIEMALS diesen Pfad zurück auf `*.parquet` oder Flat-Files.
   - Ändere NIEMALS die `init_db` Logik ohne explizite Anweisung "RESET DB LOAD".

2. ARCHITEKTUR:
   - Frontend: HTMX + Chart.js.
   - Chart-Updates: Müssen IMMER `window.initDashboardCharts()` nach `htmx:afterSwap` feuern.
   - Änderungen an der Konfiguration dürfen die Performance der `get_stats` Queries nicht verschlechtern (keine Joins für Config-Werte).