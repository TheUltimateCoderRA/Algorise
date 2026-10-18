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
from datetime import datetime, timedelta
from typing import List, Optional
import numpy as np
import pandas as pd
import yfinance as yf

class Prices:

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
        except Exception:
            pass
        return ['AAPL', 'MSFT', 'GOOGL', 'SPY']

    def _normalizeTicker(self, ticker: str) -> str:
        return ticker.strip().upper().replace('.', '-')

    def fetchMarketPrices(self, startDate: str='2012-01-01', endDate: Optional[str]=None) -> pd.DataFrame:
        if endDate is None:
            endDate = datetime.now().strftime('%Y-%m-%d')
        normalizedTickers = [self._normalizeTicker(t) for t in self.tickersList]
        rawDf = yf.download(normalizedTickers, start=startDate, end=endDate, auto_adjust=False, group_by='ticker', threads=True, progress=False)
        processedFrames = []
        if len(normalizedTickers) == 1:
            ticker = self.tickersList[0]
            df = rawDf.copy()
            df['ticker'] = ticker
            processedFrames.append(self._computeFeatures(df, ticker))
        else:
            for ticker, normTicker in zip(self.tickersList, normalizedTickers):
                try:
                    if normTicker in rawDf.columns.levels[0]:
                        df = rawDf[normTicker].copy()
                        df['ticker'] = ticker
                        processedFrames.append(self._computeFeatures(df, ticker))
                except Exception:
                    pass
        if not processedFrames:
            raise ValueError('No price data successfully retrieved for any ticker.')
        combinedPricesDf = pd.concat(processedFrames)
        return combinedPricesDf

    def dailyPrices(self, startDate: str='2012-01-01', endDate: Optional[str]=None) -> pd.DataFrame:
        return self.fetchMarketPrices(startDate=startDate, endDate=endDate)

    def _computeFeatures(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        df = df.dropna(subset=['Close'])
        volMean = df['Volume'].rolling(window=20, min_periods=1).mean()
        volStd = df['Volume'].rolling(window=20, min_periods=1).std().replace(0, 1)
        df['volumeZScore'] = (df['Volume'] - volMean) / volStd
        highLowLog = np.log(df['High'] / df['Low'].replace(0, np.nan)) ** 2
        closeOpenLog = np.log(df['Close'] / df['Open'].replace(0, np.nan)) ** 2
        gkVar = 0.5 * highLowLog - (2 * np.log(2) - 1) * closeOpenLog
        df['garmanKlassVolatility'] = np.sqrt(gkVar.clip(lower=0))
        renameMap = {'Open': 'openPrice', 'High': 'highPrice', 'Low': 'lowPrice', 'Close': 'closePrice', 'Adj Close': 'adjustedClosePrice', 'Volume': 'volume'}
        df.rename(columns=renameMap, inplace=True)
        df['ticker'] = ticker
        columnsToKeep = ['ticker', 'openPrice', 'highPrice', 'lowPrice', 'closePrice', 'adjustedClosePrice', 'volume', 'volumeZScore', 'garmanKlassVolatility']
        existingCols = [c for c in columnsToKeep if c in df.columns]
        return df[existingCols]
