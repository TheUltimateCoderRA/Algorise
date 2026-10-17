import sys
import os
if 'calendar' not in sys.modules or sys.modules['calendar'] is sys:
    _curr = os.path.dirname(os.path.abspath(__file__))
    _clean_path = [p for p in sys.path if p != _curr and p != '']
    _saved_path = sys.path
    sys.path = _clean_path
    try:
        import calendar as _std_cal
        sys.modules['calendar'] = _std_cal
    except Exception:
        pass
    finally:
        sys.path = _saved_path
import json
from typing import Dict, List, Optional
import pandas as pd
from dotenv import load_dotenv
import simfin as sf

class Fundamentals:

    def __init__(self, tickersJsonPath: str='../../tickers.json', envPath: Optional[str]=None) -> None:
        if envPath and os.path.exists(envPath):
            load_dotenv(envPath)
        else:
            load_dotenv()
        self.simfinApiKey = os.getenv('simfinKey') or os.getenv('SIMFIN_API_KEY')
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
        simfin_dir = os.path.join(project_root, 'simfin_data')
        os.makedirs(simfin_dir, exist_ok=True)
        sf.set_data_dir(simfin_dir)
        if self.simfinApiKey and self.simfinApiKey != 'YOUR_SIMFIN_API_KEY':
            try:
                sf.set_api_key(self.simfinApiKey)
            except Exception as e:
                print(f'Warning: Could not set SimFin API key: {e}')
        if not os.path.exists(tickersJsonPath):
            altPath = os.path.join(os.path.dirname(__file__), '../../../tickers.json')
            if os.path.exists(altPath):
                tickersJsonPath = altPath
            else:
                altPathRoot = 'tickers.json'
                if os.path.exists(altPathRoot):
                    tickersJsonPath = altPathRoot
        self.tickersJsonPath = tickersJsonPath
        self.tickersList = self._loadTickers()

    def _loadTickers(self) -> List[str]:
        try:
            with open(self.tickersJsonPath, 'r', encoding='utf-8') as file:
                data = json.load(file)
                if isinstance(data, dict) and 'tickers' in data:
                    return data['tickers']
                elif isinstance(data, list):
                    return data
        except Exception:
            pass
        return ['AAPL', 'MSFT', 'GOOGL', 'SPY']

    def _filterByTickers(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        if 'Ticker' in df.index.names:
            df = df.reset_index()
        elif 'ticker' in df.index.names:
            df = df.reset_index()
        ticker_col = 'Ticker' if 'Ticker' in df.columns else 'ticker' if 'ticker' in df.columns else None
        if ticker_col:
            return df[df[ticker_col].isin(self.tickersList)].copy()
        return df

    def loadIncomeStatements(self, variant: str='quarterly', market: str='us') -> pd.DataFrame:
        try:
            dfIncome = sf.load_income(variant=variant, market=market)
            return self._filterByTickers(dfIncome)
        except Exception as e:
            print(f'Error loading income statements via simfin: {e}')
            return pd.DataFrame()

    def loadBalanceSheets(self, variant: str='quarterly', market: str='us') -> pd.DataFrame:
        try:
            dfBalance = sf.load_balance(variant=variant, market=market)
            return self._filterByTickers(dfBalance)
        except Exception as e:
            print(f'Error loading balance sheets via simfin: {e}')
            return pd.DataFrame()

    def loadCashFlowStatements(self, variant: str='quarterly', market: str='us') -> pd.DataFrame:
        try:
            dfCashFlow = sf.load_cashflow(variant=variant, market=market)
            return self._filterByTickers(dfCashFlow)
        except Exception as e:
            print(f'Error loading cash flow statements via simfin: {e}')
            return pd.DataFrame()

    def loadAllFundamentals(self) -> Dict[str, pd.DataFrame]:
        return {'incomeStatements': self.loadIncomeStatements(), 'balanceSheets': self.loadBalanceSheets(), 'cashFlowStatements': self.loadCashFlowStatements()}
