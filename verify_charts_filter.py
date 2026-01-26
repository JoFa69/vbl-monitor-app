import sys
import os
sys.path.append(os.getcwd())

from app.database import get_stats_by_hour, get_stats_by_weekday

def verify_charts():
    print("Testing Chart Filters...")
    d_from = '2025-11-01'
    d_to = '2025-11-30'
    
    print("\n--- Hourly Stats (No Filter) ---")
    h_all = get_stats_by_hour(d_from, d_to)
    total_all = sum(h['total'] for h in h_all)
    print(f"Total Trips: {total_all}")
    
    print("\n--- Hourly Stats (Filter: Samstag) ---")
    h_sat = get_stats_by_hour(d_from, d_to, day_class="Samstag")
    total_sat = sum(h['total'] for h in h_sat)
    print(f"Total Trips: {total_sat}")
    
    if total_sat > 0 and total_sat < total_all:
        print("SUCCESS: Hourly stats filtered properly.")
    else:
        print(f"FAILURE: Hourly stats filter issue (Sat: {total_sat}, All: {total_all})")

    print("\n--- Weekday Stats (No Filter) ---")
    w_all = get_stats_by_weekday(d_from, d_to)
    print(f"Days present: {[d['day_name'] for d in w_all]}")
    
    print("\n--- Weekday Stats (Filter: Samstag) ---")
    w_sat = get_stats_by_weekday(d_from, d_to, day_class="Samstag")
    days_present = [d['day_name'] for d in w_sat]
    print(f"Days present: {days_present}")
    
    if len(days_present) == 1 and days_present[0] == 'Sa':
         print("SUCCESS: Weekday stats filtered to Saturday only.")
    else:
         print(f"FAILURE: Weekday stats not filtered correctly. Found: {days_present}")

if __name__ == "__main__":
    verify_charts()
