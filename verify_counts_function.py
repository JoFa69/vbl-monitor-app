import sys
import os
sys.path.append(os.getcwd())

from app.database import get_day_class_counts

def verify():
    print("Testing get_day_class_counts...")
    # November 2025
    d_from = '2025-11-01'
    d_to = '2025-11-30'
    
    counts = get_day_class_counts(d_from, d_to)
    print(f"Counts for {d_from} to {d_to}:")
    for k, v in counts.items():
        print(f"  {k}: {v}")
        
    if counts.get('Samstag') == 4 and counts.get('Sonn-/Feiertag') == 6:
        print("SUCCESS: Counts match expectation.")
    else:
        print("FAILURE: Counts do not match expectation.")

if __name__ == "__main__":
    verify()
