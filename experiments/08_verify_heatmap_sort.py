import sys
import os

# Add parent dir to path (Must be before imports from app)
sys.path.append(os.getcwd())

from app.database import get_heatmap_stats


def main():
    start_date = "2025-10-01" 
    end_date = "2025-10-01"
    line = "4"
    
    print("Fetching heatmap stats for Line 4...")
    try:
        stats = get_heatmap_stats(
            date_from=start_date, 
            date_to=end_date, 
            line_filter=line,
            granularity='trip'
        )
        
        stops = stats.get('stops', [])
        print(f"Found {len(stops)} ordered stops:")
        for i, s in enumerate(stops):
            print(f"{i+1}. {s}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
