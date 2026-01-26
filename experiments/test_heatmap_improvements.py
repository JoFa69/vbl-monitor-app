import sys
import os

# Init App Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_heatmap_stats, debug_check_route, get_connection

def test_robust_filtering():
    print("--- Testing Robust Filtering ---")
    
    # 1. Find a valid route first
    conn = get_connection()
    try:
        # Get a route that has data
        row = conn.execute("SELECT arg_min(stop_name, departure_planned) || ' » ' || arg_max(stop_name, arrival_planned) FROM vbl_data GROUP BY trip_id LIMIT 1").fetchone()
        if not row:
            print("No data found to test.")
            return
            
        valid_route = row[0]
        print(f"Testing with route: {valid_route}")
        
        # 2. Test get_heatmap_stats with this route
        stats = get_heatmap_stats(
            date_from='2020-01-01', 
            date_to='2030-01-01', # Wide range to ensure hit
            routes=[valid_route],
            granularity='60' # trigger standard view which uses new CTEs
        )
        
        if 'error' in stats:
            print(f"FAILED: {stats['error']}")
        elif len(stats.get('stops', [])) > 0:
            print("SUCCESS: Filtering returned data.")
        else:
            print("WARNING: Filtering returned 0 stops (but data exists). Check logic.")
            
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        conn.close()

def test_pattern_view_counts():
    print("\n--- Testing Pattern View Counts ---")
    try:
        stats = get_heatmap_stats(
            date_from='2020-01-01',
            date_to='2030-01-01',
            line_filter='1', # Use a line to get multiple patterns
            granularity='pattern'
        )
        
        if 'trips' in stats:
            trips = stats['trips']
            if len(trips) > 0:
                first_label = trips[0]['label']
                print(f"Sample Label: {first_label}")
                if "(n=" in first_label:
                    print("SUCCESS: Label contains trip count.")
                else:
                    print(f"FAILURE: Label missing count: {first_label}")
            else:
                print("WARNING: No patterns found for line 1.")
        else:
            print(f"FAILURE: No 'trips' key in pattern response. Keys: {stats.keys()}")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_robust_filtering()
    test_pattern_view_counts()
