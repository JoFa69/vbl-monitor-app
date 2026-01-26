import sys
import os

sys.path.append(os.getcwd())

from app.database import get_connection

def check_real_data():
    print("--- DEBUG REAL DATA START ---")
    target_route = "Emmenbrücke Sprengi » Luzern, Bahnhof"
    
    # Use wide date range
    date_from = "2025-10-01"
    date_to = "2025-11-30" # Data mostly here
    
    try:
        conn = get_connection()
        
        # 1. Check Total Count for this route (Any Status)
        q_total = """
        SELECT COUNT(*) 
        FROM vbl_data v
        JOIN (
             SELECT trip_id, arg_min(stop_name, departure_planned) || ' » ' || arg_max(stop_name, arrival_planned) as route_name
             FROM vbl_data 
             WHERE date >= ? AND date <= ?
             GROUP BY trip_id
        ) tr ON v.trip_id = tr.trip_id
        WHERE tr.route_name = ?
        """
        c_total = conn.execute(q_total, [date_from, date_to, target_route]).fetchone()[0]
        print(f"Total Rows for Route '{target_route}': {c_total}")
        
        # 2. Check REAL Status Count
        q_real = q_total + " AND v.arrival_status = 'REAL'"
        c_real = conn.execute(q_real, [date_from, date_to, target_route]).fetchone()[0]
        print(f"REAL Status Rows for Route: {c_real}")
        
        if c_total > 0 and c_real == 0:
            print("CONCLUSION: Data exists but is NOT 'REAL' (only Planned). This explains empty heatmap.")
        elif c_total == 0:
            print("CONCLUSION: No data found for this route in date range.")
        else:
            print(f"CONCLUSION: Data exists and has REAL status ({c_real} rows). Should be visible if Date is correct.")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_real_data()
