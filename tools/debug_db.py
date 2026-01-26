
from app.database import get_punctuality_stats, get_stats_by_hour
from datetime import date

print("Testing get_punctuality_stats...")
try:
    stats = get_punctuality_stats(date(2024, 1, 1), date(2024, 1, 31))
    print("Stats:", stats)
except Exception as e:
    print("Error in get_punctuality_stats:", e)

print("\nTesting get_stats_by_hour...")
try:
    stats = get_stats_by_hour(date(2024, 1, 1), date(2024, 1, 31))
    print("Hourly Stats:", len(stats), "entries")
except Exception as e:
    print("Error in get_stats_by_hour:", e)
