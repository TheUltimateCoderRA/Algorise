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
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
import yfinance as yf

class Metadata:

    def __init__(self, tickersJsonPath: str='../../tickers.json') -> None:
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
                else:
                    raise ValueError('Invalid format in tickers.json')
        except Exception:
            return ['AAPL', 'MSFT', 'GOOGL', 'SPY']

    def fetchAssetMetadata(self) -> pd.DataFrame:
        metadataRecords: List[Dict[str, Any]] = []
        currentDate = datetime.now()
        for tickerSymbol in self.tickersList:
            normSymbol = tickerSymbol.replace('.', '-')
            record = {'ticker': tickerSymbol, 'gicsSector': 'Unknown', 'gicsIndustry': 'Unknown', 'listingAgeYears': 0.0}
            try:
                yfTicker = yf.Ticker(normSymbol)
                info = yfTicker.info
                record['gicsSector'] = info.get('sector', info.get('gicsSector', 'Unknown'))
                record['gicsIndustry'] = info.get('industry', info.get('gicsIndustry', 'Unknown'))
                hist = yfTicker.history(period='max')
                if not hist.empty:
                    firstTradeDate = hist.index[0]
                    if isinstance(firstTradeDate, pd.Timestamp):
                        ageDays = (currentDate - firstTradeDate.tz_localize(None)).days
                        record['listingAgeYears'] = round(ageDays / 365.25, 2)
                else:
                    firstEpoch = info.get('firstTradeDateEpochUtc')
                    if firstEpoch:
                        firstDate = datetime.fromtimestamp(firstEpoch)
                        ageDays = (currentDate - firstDate).days
                        record['listingAgeYears'] = round(ageDays / 365.25, 2)
            except Exception:
                pass
            metadataRecords.append(record)
        metadataDf = pd.DataFrame(metadataRecords)
        metadataDf.set_index('ticker', inplace=True)
        return metadataDf
