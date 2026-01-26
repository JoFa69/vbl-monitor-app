
import duckdb
from app.database import get_connection

def verify_macro():
    print("Connecting to DB...")
    try:
        conn = get_connection()
        
        # Verify Table Content
        print("Checking special_dates table...")
        dates = conn.execute("SELECT * FROM special_dates LIMIT 5").fetchall()
        print("Sample data:", dates)
        
        # Test Cases
        test_cases = [
            ('2024-12-25', 'Sonn-/Feiertag'), # Feiertag
            ('2024-12-23', 'Mo-Fr (Ferien)'), # Ferien Mon
            ('2025-01-01', 'Sonn-/Feiertag'), # Feiertag
            ('2024-12-02', 'Mo-Fr (Schule)'), # Normal Mon (assuming no holiday)
            ('2024-12-07', 'Samstag'),        # Normal Sat
             ('2024-12-08', 'Sonn-/Feiertag') # Normal Sun
        ]
        
        print("\nTesting get_day_class macro:")
        for date_str, expected in test_cases:
            try:
                # We cast the string literal to DATE in SQL
                query = f"SELECT get_day_class('{date_str}'::DATE)"
                result = conn.execute(query).fetchone()[0]
                status = "PASS" if result == expected else f"FAIL (Expected {expected})"
                print(f"Date {date_str}: {result} -> {status}")
            except Exception as e:
                print(f"Date {date_str}: ERROR ({e})")
                
    except Exception as e:
        print(f"Verification Failed: {e}")

if __name__ == "__main__":
    verify_macro()
