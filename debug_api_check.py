
from fastapi.testclient import TestClient
from app.main import app
import urllib.parse

client = TestClient(app)

def debug_check():
    print("Debugging Route Filter via TestClient...")
    
    # 1. Start with the problematic route
    route = "Ebikon, Fildern » Obernau, Dorf"
    
    # 2. Call the Debug Endpoint
    # TestClient handles encoding of query params automatically
    print(f"\nScanning route: '{route}'")
    resp = client.get(f"/api/debug/check_route", params={"route": route})
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.json()}")
    
    # 3. Call the Stats Endpoint (simulating what the Frontend does)
    params = {
        "from": "2025-11-01",
        "to": "2025-11-02",
        "route": route 
    }
    print(f"\nRequesting Stats with params: {params}")
    resp_stats = client.get("/api/stats", params=params)
    print(f"Stats Status: {resp_stats.status_code}")
    # Partial HTML check
    if "Keine Daten gefunden" in resp_stats.text:
        print("FAIL: 'Keine Daten gefunden' returned (Basic Check).")
    elif "Gesamt:" in resp_stats.text:
        print("SUCCESS: Data found (Basic Check)!")
    
    # 4. Filter with EMPTY STOP
    params_empty_stop = {
        "from": "2025-11-01",
        "to": "2025-11-02",
        "route": route,
        "stop": "" # Simulating browser sending empty input
    }
    print(f"\nRequesting Stats with EMPTY STOP param: {params_empty_stop}")
    resp_empty = client.get("/api/stats", params=params_empty_stop)
    if "Keine Daten gefunden" in resp_empty.text:
        print("CONFIRMED: Empty stop param causes No Data!")
    else:
        print("SUCCESS: Empty stop param handled correctly.")

if __name__ == "__main__":
    debug_check()
