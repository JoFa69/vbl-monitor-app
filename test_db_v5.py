
import logging
from app.database import (
    get_connection, 
    get_punctuality_stats, 
    get_stats_by_hour, 
    get_stats_by_weekday, 
    get_problematic_stops, 
    get_worst_trips
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_analytics():
    print("Testing Analytics Functions...")
    
    # Range with known data
    start = "2025-11-01"
    end = "2025-11-02"
    
    print(f"\n--- Stats by Hour ({start} to {end}) ---")
    hourly = get_stats_by_hour(start, end)
    print(f"Returned {len(hourly)} rows")
    if hourly:
        print(f"Sample: {hourly[0]}")
        
    print(f"\n--- Stats by Weekday ({start} to {end}) ---")
    daily = get_stats_by_weekday(start, end)
    print(f"Returned {len(daily)} rows")
    if daily:
        print(f"Sample: {daily[0]}")

    print(f"\n--- Problematic Stops ({start} to {end}) ---")
    stops = get_problematic_stops(start, end)
    print(f"Returned {len(stops)} stops")
    for s in stops[:3]:
        print(s)

    print(f"\n--- Worst Trips ({start} to {end}) ---")
    trips = get_worst_trips(start, end)
    print(f"Returned {len(trips)} trips")
    for t in trips[:3]:
        print(t)
        
    print(f"\n--- Testing Stop Filter ---")
    if stops:
        test_stop = stops[0]['name']
        print(f"Filtering by stop: {test_stop}")
        stats = get_punctuality_stats(start, end, stop_filter=[test_stop])
        print(f"Stats for {test_stop}: {stats}")
        
    print(f"\n--- REGRESSION TEST: Route Filter ---")
    # This route was reported as failing
    problem_route = "Ebikon, Fildern » Obernau, Dorf"
    print(f"Testing route: '{problem_route}'")
    stats_prob = get_punctuality_stats(start, end, route_filter=[problem_route])
    print(f"Stats for problem route: {stats_prob}")

if __name__ == "__main__":
    test_analytics()
