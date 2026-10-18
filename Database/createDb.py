import os
import sqlite3
DB_PATH = os.path.join(os.path.dirname(__file__), 'algorise.db')

def create_database(db_path: str=DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('\n        CREATE TABLE IF NOT EXISTS metadata (\n            ticker TEXT PRIMARY KEY,\n            gics_sector TEXT,\n            gics_industry TEXT,\n            listing_age_years REAL\n        )\n    ')
    cursor.execute('\n        CREATE TABLE IF NOT EXISTS calendar (\n            date TEXT PRIMARY KEY,\n            day_of_week INTEGER,\n            day_of_month INTEGER,\n            month INTEGER,\n            quarter INTEGER,\n            day_of_year INTEGER,\n            is_holiday INTEGER,\n            is_earnings_window INTEGER\n        )\n    ')
    cursor.execute('\n        CREATE TABLE IF NOT EXISTS market_prices (\n            ticker TEXT,\n            date TEXT,\n            open_price REAL,\n            high_price REAL,\n            low_price REAL,\n            close_price REAL,\n            adjusted_close_price REAL,\n            volume REAL,\n            volume_z_score REAL,\n            garman_klass_volatility REAL,\n            PRIMARY KEY (ticker, date)\n        )\n    ')
    cursor.execute('\n        CREATE TABLE IF NOT EXISTS macro (\n            date TEXT PRIMARY KEY,\n            federal_funds_rate REAL,\n            treasury_yield_10y REAL,\n            cpi REAL,\n            unemployment_rate REAL,\n            treasury_spread_10y2y REAL,\n            money_supply_m2 REAL,\n            consumer_sentiment REAL,\n            industrial_production REAL,\n            high_yield_credit_spread REAL\n        )\n    ')
    cursor.execute('\n        CREATE TABLE IF NOT EXISTS fundamentals_income (\n            ticker TEXT,\n            report_date TEXT,\n            data_json TEXT,\n            PRIMARY KEY (ticker, report_date)\n        )\n    ')
    cursor.execute('\n        CREATE TABLE IF NOT EXISTS fundamentals_balance (\n            ticker TEXT,\n            report_date TEXT,\n            data_json TEXT,\n            PRIMARY KEY (ticker, report_date)\n        )\n    ')
    cursor.execute('\n        CREATE TABLE IF NOT EXISTS fundamentals_cashflow (\n            ticker TEXT,\n            report_date TEXT,\n            data_json TEXT,\n            PRIMARY KEY (ticker, report_date)\n        )\n    ')
    conn.commit()
    conn.close()
    print(f'Database created successfully at {db_path}')
if __name__ == '__main__':
    create_database()
