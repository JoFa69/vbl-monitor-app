
import sys
import os

# Add project root to path so we can import experiments package or app if needed
sys.path.append(os.getcwd())

from experiments.db_connector import get_connection

def test_aggregation():
    print("--- Experiment: Aggregation Analysis (Line 2) ---")
    
    conn = get_connection()
    
    # Parameters
    line_id = '2'
    date_from = '2025-10-01'
    date_to = '2025-11-30'
    time_start = '07:00:00'
    time_end = '09:00:00'
    
    try:
        query = f"""
        WITH trip_data AS (
            SELECT
                trip_id,
                date_dt,
                min(departure_planned) as trip_start,
                -- Construct Route Name: Start » End
                arg_min(stop_name, departure_planned) || ' » ' || arg_max(stop_name, arrival_planned) as route_name,
                
                -- Calculate delay for the whole trip (avg of stops or just arrival at end?)
                -- User asked for avg(arrival_delay). Usually meaning delay at stops? 
                -- Or delay of the trip? 
                -- Let's take the average delay of all stops in the trip for simplicity, 
                -- or if the user meant per-pattern stats, we aggregate across trips.
                -- Let's calculate delay per stop row first, then aggregate?
                -- Wait, the VIEW vbl_data is granular (one row per stop).
                -- So we first need to identify trips and their "pattern".
                
                -- Actually, to group by "Pattern", we need:
                -- 1. Identify Trip (User for that time)
                -- 2. Get its planned start time (HH:MM) -> This is the Pattern Key
                -- 3. Get its Route Name -> Pattern Key 2
                -- 4. Aggregate stats for that trip (avg delay across its stops? or end delay?)
                -- The prompt says: "Berechne... avg(arrival_delay)". 
                -- If we group by pattern, this is the average delay of ALL stops of ALL trips in that pattern?
                -- Or average END delay? "Ankunftsverspätung" usually refers to arrival at stop.
                
                avg(date_diff('second', arrival_planned, arrival_actual)) as trip_avg_delay
                
            FROM vbl_data
            WHERE line_name = '{line_id}'
              AND date_dt BETWEEN '{date_from}' AND '{date_to}'
            GROUP BY trip_id, date_dt
        )
        SELECT 
            strftime(trip_start, '%H:%M') as plan_time,
            route_name,
            count(*) as trip_count,
            round(avg(trip_avg_delay), 1) as avg_delay_sec,
            round(min(trip_avg_delay), 1) as min_delay_sec,
            round(max(trip_avg_delay), 1) as max_delay_sec
        FROM trip_data
        WHERE CAST(trip_start AS TIME) BETWEEN '{time_start}' AND '{time_end}'
        GROUP BY plan_time, route_name
        ORDER BY plan_time, route_name
        """
        
        results = conn.execute(query).fetchall()
        
        # Output Table
        print(f"\n{'Time':<8} | {'Route':<50} | {'Count':<5} | {'Avg (s)':<8} | {'Min':<6} | {'Max':<6}")
        print("-" * 100)
        
        for r in results:
            print(f"{r[0]:<8} | {r[1]:<50} | {r[2]:<5} | {r[3]:<8} | {r[4]:<6} | {r[5]:<6}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_aggregation()
