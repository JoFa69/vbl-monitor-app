
from app.database import get_punctuality_stats, get_connection
import duckdb

def verify_filter():
    print("Testing Day Class Filter...")
    
    # Ensure data exists for testing (Data avaliable from 2025-10-01 to 2025-12-17)
    start_date = "2025-10-01"
    end_date = "2025-12-17" 
    
    # 1. Test "Sonn-/Feiertag" (Should catch 01.11.25 and Sundays)
    print("\n--- Testing 'Sonn-/Feiertag' ---")
    stats_holiday = get_punctuality_stats(start_date, end_date, day_class="Sonn-/Feiertag")
    print(f"Stats (Sonn-/Feiertag): {stats_holiday}")
    
    # 2. Test "Mo-Fr (Schule)" (Should catch Nov 2025 weekdays)
    print("\n--- Testing 'Mo-Fr (Schule)' ---")
    stats_school = get_punctuality_stats(start_date, end_date, day_class="Mo-Fr (Schule)")
    print(f"Stats (Mo-Fr (Schule)): {stats_school}")
    
    # 3. Test "Mo-Fr (Ferien)" (Should catch Oct 1-10 2025)
    print("\n--- Testing 'Mo-Fr (Ferien)' ---")
    stats_vacation = get_punctuality_stats(start_date, end_date, day_class="Mo-Fr (Ferien)")
    print(f"Stats (Mo-Fr (Ferien)): {stats_vacation}")
    
    if stats_holiday.get('total', 0) > 0 and stats_school.get('total', 0) > 0 and stats_vacation.get('total', 0) > 0:
         print("\nSUCCESS: Filter returned results for all categories.")
    else:
         print(f"Holiday: {stats_holiday.get('total', 0)}")
         print(f"School: {stats_school.get('total', 0)}")
         print(f"Vacation: {stats_vacation.get('total', 0)}")
         if stats_school.get('total', 0) > 0:
             print("\nPARTIAL SUCCESS: Some categories found data.")
         else: 
             print("\nFAILURE: No data found.")

if __name__ == "__main__":
    verify_filter()
