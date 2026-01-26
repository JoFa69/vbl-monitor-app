
from app.database import get_punctuality_stats
import json

def test_filters():
    print("Testing Filter Logic...")
    start_date = "2025-10-01"
    end_date = "2025-12-17"
    
    # 1. Baseline (All Data)
    print("\n--- Baseline (No Filter) ---")
    stats_base = get_punctuality_stats(start_date, end_date)
    print(f"Total: {stats_base.get('total', 0)}")
    
    # 2. Stop Filter "Luzern, Bahnhof" (Likely not a last stop for many lines, or is it? It's a hub.)
    # Let's pick a stop that is likely intermediate. 
    # "Luzern, Pilatusplatz" is often intermediate.
    print("\n--- Stop Filter: 'Luzern, Pilatusplatz' ---")
    stop_name = "Luzern, Pilatusplatz"
    stats_stop = get_punctuality_stats(start_date, end_date, stop_filter=[stop_name])
    print(f"Stats for {stop_name}: {stats_stop}")
    
    if stats_stop.get('total', 0) == 0:
        print("FAILURE: Stop filter returned 0 results. (Likely effectively filtered out by 'last stop' logic)")
    else:
        print(f"SUCCESS: Stop filter returned {stats_stop.get('total')} results.")

if __name__ == "__main__":
    test_filters()
