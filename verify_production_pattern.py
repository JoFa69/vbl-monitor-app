
import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

try:
    from app.database import get_pattern_stats, get_connection
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def verify():
    print("--- Verifying Production Pattern View ---")
    
    # Parameters known to have data (from lab experiment)
    date_from = '2025-11-01'
    date_to = '2025-11-30'
    line = '2'
    
    # 1. Test get_pattern_stats
    print(f"Fetching pattern stats for Line {line} ({date_from} to {date_to})...")
    
    try:
        # We need to simulate the filter logic. 
        # get_pattern_stats takes 'line_filter'? No, it takes 'routes', 'stops', 'line_filter' (maybe).
        # Let's check signatures or just pass what we can.
        # Signature: date_from, date_to, routes=None, stops=None, day_class=None, line_filter=None...
        
        # We can pass line_filter='2' if supported, or verify if we need to resolve routes first.
        # app/database.py logic usually requires line_filter to be passed to _build_filter_clause.
        
        stats = get_pattern_stats(
            date_from=date_from,
            date_to=date_to,
            line_filter=line,
            metric_type='arrival'
        )
        
        if 'error' in stats:
            print(f"ERROR (No Filter): {stats['error']}")
        else:
            print(f"SUCCESS (No Filter): Got {len(stats.get('trips', []))} patterns.")

        # 2. Test with Route Filter (Triggering the Binder Error scenario)
        test_route = "Emmenbrücke Sprengi » Luzern, Bahnhof"
        print(f"\nFetching pattern stats with Route Filter: '{test_route}'...")
        stats_filtered = get_pattern_stats(
            date_from=date_from,
            date_to=date_to,
            line_filter=line,
            routes=[test_route],
            metric_type='arrival'
        )
        
        if 'error' in stats_filtered:
             print(f"ERROR (With Route Filter): {stats_filtered['error']}")
        else:
             print(f"SUCCESS (With Route Filter): Got {len(stats_filtered.get('trips', []))} patterns.")
             # Check if all returned patterns match the route
             mismatches = [p for p in stats_filtered.get('trips', []) if p['vehicle'] != test_route]
             if mismatches:
                 print(f"WARNING: Found {len(mismatches)} patterns processing wrong route!")
             else:
                 print("Validation: All patterns match the requested route.")

        # 3. Test Wrapper: get_heatmap_stats (simulate API call)
        print(f"\nTesting Wrapper 'get_heatmap_stats' with granularity='pattern'...")
        from app.database import get_heatmap_stats
        
        wrapper_stats = get_heatmap_stats(
            date_from=date_from,
            date_to=date_to,
            line_filter=line,
            metric_type='arrival',
            granularity='pattern'
        )
        
        if 'error' in wrapper_stats:
             print(f"ERROR (Wrapper): {wrapper_stats['error']}")
        else:
             print(f"SUCCESS (Wrapper): Got {len(wrapper_stats.get('trips', []))} patterns.")
             
             x_labels = wrapper_stats.get('x_labels', [])
             print(f"DEBUG: x_labels Sample (first 5): {x_labels[:5]}")
             
             # Check for "cryptic numbers"
             if x_labels and isinstance(x_labels[0], (int, float)):
                 print("FAILURE: x_labels are numbers! Implementation bug confirmed.")
             elif x_labels and ":" not in str(x_labels[0]):
                  print(f"WARNING: x_labels might be malformed (expected HH:MM): {x_labels[0]}")
             else:
                  print("SUCCESS: x_labels look like time strings.")

    except Exception as e:
        print(f"Execution Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify()
