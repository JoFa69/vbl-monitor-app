
from fastapi.testclient import TestClient
from app.main import app
import logging

# Mute logger for cleaner output
logging.getLogger("app.database").setLevel(logging.WARNING)

client = TestClient(app)

def test_endpoints():
    print("Verifying API Endpoints...")
    
    # 1. Main Dashboard
    print("- GET /")
    response = client.get("/")
    assert response.status_code == 200
    assert "Pünktlichkeits-Dashboard" in response.text
    print("  OK")

    params = {
        "from": "2025-11-01",
        "to": "2025-11-02"
    }
    
    # 2. Hourly Stats
    print("- GET /api/stats/hourly")
    response = client.get("/api/stats/hourly", params=params)
    assert response.status_code == 200
    # Check if canvas exists
    assert "hourlyChart" in response.text 
    print("  OK")

    # 3. Weekday Stats
    print("- GET /api/stats/weekday")
    response = client.get("/api/stats/weekday", params=params)
    assert response.status_code == 200
    assert "weekdayChart" in response.text
    print("  OK")

    # 4. Stops Table
    print("- GET /api/stats/stops")
    response = client.get("/api/stats/stops", params=params)
    assert response.status_code == 200
    assert "Problematische Haltestellen" in response.text
    print("  OK")

    # 5. Trips Table
    print("- GET /api/stats/trips")
    response = client.get("/api/stats/trips", params=params)
    assert response.status_code == 200
    assert "Größte Einzelverspätungen" in response.text
    print("  OK")
    
    # 6. Stop Filter Test
    # We need a stop name that exists.
    # We can rely on database content or just pass a dummy one and expect success (but empty results)
    print("- GET /api/stats with Stop Filter")
    response = client.get("/api/stats", params={**params, "stop": "Zürich, HB"}) # Unlikely to be in data but should not error
    assert response.status_code == 200
    print("  OK (Status 200 returned)")

if __name__ == "__main__":
    try:
        test_endpoints()
        print("\nAll endpoints verified successfully!")
    except AssertionError as e:
        print(f"\nVerification FAILED: {e}")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
