import os
import sys
import sqlite3

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from remoteLoader import ensure_algorise_db

DB_PATH = os.path.join(os.path.dirname(__file__), 'algorise.db')

def check_database(db_path: str=DB_PATH) -> None:
    db_path = ensure_algorise_db(db_path)
    if not os.path.exists(db_path):
        print(f'Database file not found at {db_path}. Please ensure ALGORISE_DB_URL is set in .env or run createDb.py.')
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f'=== Database Inspection: {db_path} ===\n')
    for table_tuple in tables:
        table_name = table_tuple[0]
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = cursor.fetchone()[0]
        print(f'Table: {table_name} | Row Count: {count}')
        cursor.execute(f'SELECT * FROM {table_name} LIMIT 3')
        rows = cursor.fetchall()
        if rows:
            print('  Sample rows:')
            for row in rows:
                print(f'    {row}')
        print('-' * 40)
    conn.close()
if __name__ == '__main__':
    check_database()
