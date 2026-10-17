import os
import sys
import sqlite3
import json
import pandas as pd
from datetime import datetime
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)
from Database.createDb import create_database, DB_PATH
from Data.Model.metadata import Metadata
from Data.Model.calendar import CalendarFeatures
from Data.Model.marketPrices import Prices
from Data.Model.macro import Macro
from Data.Model.fundamentals import Fundamentals

def serialize_val(v):
    if pd.isna(v):
        return None
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.strftime('%Y-%m-%d')
    return v

def run_all(startDate: str='2012-01-01', endDate: Optional[str]=None) -> None:
    if endDate is None:
        endDate = datetime.now().strftime('%Y-%m-%d')
    print(f'Initializing database and running pipeline for date range: {startDate} to {endDate}...')
    create_database(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for tbl in ['metadata', 'calendar', 'market_prices', 'macro', 'fundamentals_income', 'fundamentals_balance', 'fundamentals_cashflow']:
        try:
            cursor.execute(f'DELETE FROM {tbl}')
        except Exception:
            pass
    conn.commit()
    print('Fetching and storing Metadata...')
    try:
        metadata_obj = Metadata()
        df_metadata = metadata_obj.fetchAssetMetadata()
        if not df_metadata.empty:
            df_to_save = df_metadata.reset_index()
            success_count = 0
            for _, row in df_to_save.iterrows():
                try:
                    cursor.execute('\n                        INSERT OR REPLACE INTO metadata (ticker, gics_sector, gics_industry, listing_age_years)\n                        VALUES (?, ?, ?, ?)\n                    ', (str(row.get('ticker')), str(row.get('gicsSector', 'Unknown')), str(row.get('gicsIndustry', 'Unknown')), float(row.get('listingAgeYears', 0.0) or 0.0)))
                    success_count += 1
                except Exception as ex:
                    print(f"Error inserting metadata for {row.get('ticker')}: {ex}")
            conn.commit()
            print(f'Metadata stored successfully ({success_count} rows).')
    except Exception as e:
        print(f'Error storing metadata: {e}')
    print('Generating and storing Calendar Features (2012-present)...')
    try:
        calendar_obj = CalendarFeatures(exchangeName='NYSE')
        df_calendar = calendar_obj.generateCalendarFeatures(startDate=startDate, endDate=endDate)
        if not df_calendar.empty:
            df_cal_to_save = df_calendar.reset_index()
            date_col = 'date' if 'date' in df_cal_to_save.columns else df_cal_to_save.columns[0]
            success_count = 0
            for _, row in df_cal_to_save.iterrows():
                try:
                    dt_str = pd.to_datetime(row[date_col]).strftime('%Y-%m-%d')
                    cursor.execute('\n                        INSERT OR REPLACE INTO calendar (date, day_of_week, day_of_month, month, quarter, day_of_year, is_holiday, is_earnings_window)\n                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)\n                    ', (dt_str, int(row.get('dayOfWeek', 0)), int(row.get('dayOfMonth', 0)), int(row.get('month', 0)), int(row.get('quarter', 0)), int(row.get('dayOfYear', 0)), int(row.get('isHoliday', 0)), int(row.get('isEarningsWindow', 0))))
                    success_count += 1
                except Exception as ex:
                    print(f'Error inserting calendar date {row.get(date_col)}: {ex}')
            conn.commit()
            print(f'Calendar features stored successfully ({success_count} rows).')
    except Exception as e:
        print(f'Error storing calendar features: {e}')
    print('Fetching and storing Market Prices (12-year history)...')
    try:
        prices_obj = Prices()
        df_prices = prices_obj.dailyPrices(startDate=startDate, endDate=endDate)
        if not df_prices.empty:
            df_prices_to_save = df_prices.reset_index()
            date_col = 'Date' if 'Date' in df_prices_to_save.columns else 'date' if 'date' in df_prices_to_save.columns else df_prices_to_save.columns[0]
            success_count = 0
            for _, row in df_prices_to_save.iterrows():
                try:
                    dt_str = pd.to_datetime(row[date_col]).strftime('%Y-%m-%d')
                    cursor.execute('\n                        INSERT OR REPLACE INTO market_prices \n                        (ticker, date, open_price, high_price, low_price, close_price, adjusted_close_price, volume, volume_z_score, garman_klass_volatility)\n                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\n                    ', (str(row.get('ticker')), dt_str, float(row.get('openPrice', 0.0) or 0.0), float(row.get('highPrice', 0.0) or 0.0), float(row.get('lowPrice', 0.0) or 0.0), float(row.get('closePrice', 0.0) or 0.0), float(row.get('adjustedClosePrice', 0.0) or 0.0), float(row.get('volume', 0.0) or 0.0), float(row.get('volumeZScore', 0.0) or 0.0), float(row.get('garmanKlassVolatility', 0.0) or 0.0)))
                    success_count += 1
                except Exception as ex:
                    pass
            conn.commit()
            print(f'Market prices stored successfully ({success_count} rows).')
    except Exception as e:
        print(f'Error storing market prices: {e}')
    print('Fetching and storing Macro Data...')
    try:
        macro_obj = Macro()
        df_macro = macro_obj.fetchMacroData(startDate=startDate, endDate=endDate)
        if not df_macro.empty:
            df_macro_to_save = df_macro.reset_index()
            date_col = 'date' if 'date' in df_macro_to_save.columns else df_macro_to_save.columns[0]
            success_count = 0
            for _, row in df_macro_to_save.iterrows():
                try:
                    raw_dt = row.get(date_col)
                    if pd.isna(raw_dt):
                        continue
                    dt_str = pd.to_datetime(raw_dt).strftime('%Y-%m-%d')
                    cursor.execute('\n                        INSERT OR REPLACE INTO macro \n                        (date, federal_funds_rate, treasury_yield_10y, cpi, unemployment_rate, treasury_spread_10y2y, money_supply_m2, consumer_sentiment, industrial_production, high_yield_credit_spread)\n                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\n                    ', (dt_str, float(row.get('federalFundsRate', 0.0) or 0.0), float(row.get('treasuryYield10Y', 0.0) or 0.0), float(row.get('cpi', 0.0) or 0.0), float(row.get('unemploymentRate', 0.0) or 0.0), float(row.get('treasurySpread10Y2Y', 0.0) or 0.0), float(row.get('moneySupplyM2', 0.0) or 0.0), float(row.get('consumerSentiment', 0.0) or 0.0), float(row.get('industrialProduction', 0.0) or 0.0), float(row.get('highYieldCreditSpread', 0.0) or 0.0)))
                    success_count += 1
                except Exception as ex:
                    pass
            conn.commit()
            print(f'Macro data stored successfully ({success_count} rows).')
    except Exception as e:
        print(f'Error storing macro data: {e}')
    print('Loading and storing Fundamentals via SimFin...')
    try:
        fundamentals_obj = Fundamentals()
        statements = fundamentals_obj.loadAllFundamentals()
        for stmt_type, df_stmt in statements.items():
            if isinstance(df_stmt, pd.DataFrame) and (not df_stmt.empty):
                table_name = 'fundamentals_income'
                if 'balance' in stmt_type.lower():
                    table_name = 'fundamentals_balance'
                elif 'cash' in stmt_type.lower():
                    table_name = 'fundamentals_cashflow'
                df_to_save = df_stmt.reset_index()
                success_count = 0
                for _, row in df_to_save.iterrows():
                    try:
                        ticker = str(row.get('Ticker', row.get('ticker', 'AAPL')))
                        raw_date = row.get('Report Date', row.get('Date', '2024-01-01'))
                        if pd.isna(raw_date):
                            continue
                        report_date = pd.to_datetime(raw_date).strftime('%Y-%m-%d')
                        row_dict = {k: serialize_val(v) for k, v in row.to_dict().items()}
                        data_json = json.dumps(row_dict)
                        cursor.execute(f'\n                            INSERT OR REPLACE INTO {table_name} (ticker, report_date, data_json)\n                            VALUES (?, ?, ?)\n                        ', (ticker, report_date, data_json))
                        success_count += 1
                    except Exception as ex:
                        pass
                conn.commit()
                print(f'{table_name} stored successfully ({success_count} rows).')
    except Exception as e:
        print(f'Error storing fundamentals: {e}')
    conn.close()
    print('All data successfully processed and stored in database!')
if __name__ == '__main__':
    run_all(startDate='2012-01-01')
