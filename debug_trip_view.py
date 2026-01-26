
import sys
import os
import requests
import json
from datetime import datetime

# URL of the backend API
BASE_URL = "http://localhost:8081/api"

def check_trip_view():
    print("Checking Trip View API...")
    
    # Needs a valid route. Let's find one first via line/route lists?
    # Or just use date range scan.
    
    # 1. Get Date Range
    try:
        r = requests.get(f"{BASE_URL}/dashboard-metadata")
        meta = r.json()
        min_date = meta['date_range']['min']
        max_date = meta['date_range']['max']
        print(f"Date Range: {min_date} to {max_date}")
        
        # Use a known date slice or the min date
        # Assuming we have data in 2025-11-01
        test_date = "2025-11-01" 
        
        # 2. Find a route
        lines = meta.get('lines', {})
        route = None
        for line_id, routes_list in lines.items():
            if len(routes_list) > 0:
                route = routes_list[0]['name']
                print(f"Using Test Route: {route}")
                break
        
        if not route:
            print("ERROR: No routes found in metadata.")
            return

        # 3. Call Heatmap API with granularity=trip
        params = {
            "from": test_date,
            "to": test_date, # Single day for trip view usually
            "route": [route], # List
            "granularity": "trip"
        }
        
        url = f"{BASE_URL}/stats/heatmap"
        print(f"Requesting: {url} with {params}")
        
        res = requests.get(url, params=params)
        
        if res.status_code != 200:
            print(f"ERROR: API returned {res.status_code}")
            print(res.text)
            return
            
        data = res.json()
        print("Response Keys:", data.keys())
        
        if 'grid' in data:
            grid = data['grid']
            print(f"Grid found. Rows: {len(grid)}")
            if len(grid) > 0:
                print(f"Cols: {len(grid[0])}")
                # Check for non-null values
                non_null = 0
                for row in grid:
                    for cell in row:
                        if cell is not None:
                            non_null += 1
                print(f"Non-null cells: {non_null}")
            else:
                print("Grid is empty list.")
        else:
            print("ERROR: 'grid' key missing in response!")
            print("Full Response (truncated):", str(data)[:500])

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    check_trip_view()
