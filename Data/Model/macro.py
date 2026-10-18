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
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from dotenv import load_dotenv
from fredapi import Fred

class Macro:

    def __init__(self, envPath: Optional[str]=None) -> None:
        if envPath and os.path.exists(envPath):
            load_dotenv(envPath)
        else:
            load_dotenv()
        self.fredApiKey = os.getenv('fredKey')
        if not self.fredApiKey:
            self.fredApiKey = os.getenv('FRED_API_KEY')
        if self.fredApiKey and self.fredApiKey != 'YOUR_FRED_API_KEY':
            try:
                self.fredClient = Fred(api_key=self.fredApiKey)
            except Exception:
                self.fredClient = None
        else:
            self.fredClient = None
        self.indicatorSeries: List[str] = ['FEDFUNDS', 'GS10', 'CPIAUCSL', 'UNRATE', 'T10Y2Y', 'M2SL', 'UMCSENT', 'INDPRO', 'BAMLC0A0CM']

    def fetchMacroData(self, startDate: str='2012-01-01', endDate: Optional[str]=None) -> pd.DataFrame:
        if endDate is None:
            endDate = datetime.now().strftime('%Y-%m-%d')
        seriesData: Dict[str, pd.Series] = {}
        if self.fredClient is not None:
            for seriesId in self.indicatorSeries:
                try:
                    dataSeries = self.fredClient.get_series(seriesId, observation_start=startDate, observation_end=endDate)
                    seriesData[seriesId] = dataSeries
                except Exception:
                    pass
        if seriesData:
            macroDf = pd.DataFrame(seriesData)
        else:
            dateRange = pd.date_range(start=startDate, end=endDate, freq='B')
            macroDf = pd.DataFrame(index=dateRange, columns=self.indicatorSeries)
        macroDf.index = pd.to_datetime(macroDf.index)
        macroDf.index.name = 'date'
        macroDf = macroDf.resample('B').ffill()
        columnRenameMap = {'FEDFUNDS': 'federalFundsRate', 'GS10': 'treasuryYield10Y', 'CPIAUCSL': 'cpi', 'UNRATE': 'unemploymentRate', 'T10Y2Y': 'treasurySpread10Y2Y', 'M2SL': 'moneySupplyM2', 'UMCSENT': 'consumerSentiment', 'INDPRO': 'industrialProduction', 'BAMLC0A0CM': 'highYieldCreditSpread'}
        macroDf.rename(columns=columnRenameMap, inplace=True)
        return macroDf
