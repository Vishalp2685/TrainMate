import sqlite3
from datetime import datetime

def get_trains_between_stations(src_code: str, dest_code: str, current_time: str):

    try:
        conn = sqlite3.connect('TrainSchedule.db')
        cursor = conn.cursor()
    
        query = """
                SELECT DISTINCT 
                t1.[Train No.], 
                t1.[train Name], 
                t1.[Departure time], 
                t2.[Arrival time], 
                t1.[Station Name], 
                t2.[Station Name]

            FROM data t1
            JOIN data t2 
            ON t1.[Train No.] = t2.[Train No.]

            WHERE TRIM(t1.[station Code]) = TRIM(?) 
            AND TRIM(t2.[station Code]) = TRIM(?)

            AND CAST(t1.[islno] AS INTEGER) < CAST(t2.[islno] AS INTEGER)

            AND time(t1.[Departure time]) >= time(?)

            ORDER BY time(t1.[Departure time]) ASC
        """
        rows = cursor.execute(query, (src_code, dest_code, current_time)).fetchall()
        trains = []
        print(rows)
        for row in rows:
            trains.append({
                "train_no": str(row[0]).strip("'"),
                "train_name": str(row[1]).strip(),
                "departure_time": str(row[2]),
                "arrival_time": str(row[3]),
                "source_station": str(row[4]).strip(),
                "dest_station": str(row[5]).strip()
            })
        return trains
    except Exception as e:
        print(f"Error fetching trains: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()