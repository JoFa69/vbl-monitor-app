
import subprocess
import time
import requests
import sys
import os
import signal

def run_test():
    # Start Server in Background
    print("Starting temporary server on port 8082...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8082"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd(),
        text=True
    )
    
    try:
        time.sleep(5) # Wait for server startup
        
        # Define the problematic route
        # "Emmenbrücke Sprengi » Luzern, Bahnhof"
        route_name = "Emmenbrücke Sprengi » Luzern, Bahnhof"
        
        print(f"Sending request for route: {route_name}")
        
        params = {
            "from": "2025-11-01",
            "to": "2025-11-01",
            "route": [route_name],
            "granularity": "trip"
        }
        
        url = "http://localhost:8082/api/stats/heatmap"
        
        try:
            resp = requests.get(url, params=params)
            print(f"Status Code: {resp.status_code}")
            data = resp.json()
            grid_info = "Grid Found" if 'grid' in data and data['grid'] else "Grid Empty/Missing"
            print(f"Response Analysis: {grid_info}")
            if 'trip_infos' in data:
                print(f"Trips Found: {len(data['trip_infos'])}")
            
        except Exception as e:
            print(f"Request failed: {e}")

        # Kill server to flush buffers
        server_process.Terminate()
        # On Windows terminate might not suffice for immediate buffer flush, but text=True helps.
        
    except Exception as e:
        print(f"Test Loop Error: {e}")
    finally:
        print("Stopping server...")
        server_process.kill()
        out, err = server_process.communicate()
        
        print("\n=== SERVER LOGS (SPY OUTPUT) ===")
        print(out)
        print(err)
        print("================================")

if __name__ == "__main__":
    run_test()
