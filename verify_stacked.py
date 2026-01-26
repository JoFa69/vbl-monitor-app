
import sys
import os
import asyncio
from unittest.mock import MagicMock

# Configure path
sys.path.append(os.getcwd())

from app.database import get_stats_by_hour, get_stats_by_weekday, get_date_range

def verify_backend_structure():
    print("Verifying backend data structure for Stacked Charts...")
    
    dr = get_date_range()
    date_from = dr['min']
    date_to = dr['max']
    
    print(f"Date Range: {date_from} to {date_to}")

    # 1. Hourly Stats
    print("\n--- Hourly Stats ---")
    hourly = get_stats_by_hour(date_from, date_to)
    if hourly:
        first = hourly[0]
        print(f"First row: {first}")
        required_keys = ['hour', 'total', 'early', 'on_time', 'late_slight', 'late_severe']
        missing = [k for k in required_keys if k not in first]
        if missing:
            print(f"FAILURE: Hourly stats missing keys: {missing}")
        else:
            print("SUCCESS: Hourly stats have all required keys.")
            # Check sum
            calculated_total = first['early'] + first['on_time'] + first['late_slight'] + first['late_severe']
            print(f"Total Check: DB Total={first['total']}, Sum Attributes={calculated_total}")
            if first['total'] == calculated_total:
                print("SUCCESS: Sum matches total.")
            else:
                print("WARNING: Sum does not match total (could be unknown/nulls or logic error).")
    else:
        print("WARNING: No hourly data found.")

    # 2. Weekday Stats
    print("\n--- Weekday Stats ---")
    weekday = get_stats_by_weekday(date_from, date_to)
    if weekday:
        first = weekday[0]
        print(f"First row: {first}")
        required_keys = ['dow', 'total', 'early', 'on_time', 'late_slight', 'late_severe']
        missing = [k for k in required_keys if k not in first]
        if missing:
            print(f"FAILURE: Weekday stats missing keys: {missing}")
        else:
            print("SUCCESS: Weekday stats have all required keys.")
    else:
        print("WARNING: No weekday data found.")

if __name__ == "__main__":
    verify_backend_structure()
