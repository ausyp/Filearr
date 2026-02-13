import sqlite3
import os

def get_key():
    db_path = "data/filearr.db"
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT value FROM system_settings WHERE key='TMDB_API_KEY';")
        row = cursor.fetchone()
        if row:
            print(row[0])
        else:
            print("Key not found in DB")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    get_key()
