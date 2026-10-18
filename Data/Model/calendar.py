import sys
import os
_real_calendar = None
for _path in sys.path:
    if _path == os.path.dirname(os.path.abspath(__file__)) or _path == '':
        continue
    _candidate = os.path.join(_path, 'calendar.py')
    if os.path.exists(_candidate) and os.path.abspath(_candidate) != os.path.abspath(__file__):
        try:
            import importlib.util
            _spec = importlib.util.spec_from_file_location('_stdlib_cal', _candidate)
            _mod = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
            _real_calendar = _mod
            break
        except Exception:
            continue
if _real_calendar is None:
    _curr = os.path.dirname(os.path.abspath(__file__))
    _clean_path = [p for p in sys.path if p != _curr and p != '']
    _saved_path = sys.path
    sys.path = _clean_path
    try:
        import calendar as _std_cal
        _real_calendar = _std_cal
    except Exception:
        pass
    finally:
        sys.path = _saved_path
if _real_calendar:
    for _attr in dir(_real_calendar):
        if not _attr.startswith('_'):
            globals()[_attr] = getattr(_real_calendar, _attr)
from datetime import datetime
from typing import Optional
import pandas as pd
import pandas_market_calendars as mcal

class CalendarFeatures:

    def __init__(self, exchangeName: str='NYSE') -> None:
        self.exchangeName = exchangeName
        self.marketCalendar = mcal.get_calendar(exchangeName)

    def generateCalendarFeatures(self, startDate: str='2012-01-01', endDate: Optional[str]=None) -> pd.DataFrame:
        if endDate is None:
            endDate = datetime.now().strftime('%Y-%m-%d')
        schedule = self.marketCalendar.schedule(start_date=startDate, end_date=endDate)
        tradingDays = self.marketCalendar.valid_days(start_date=startDate, end_date=endDate)
        tradingDates = pd.to_datetime(tradingDays).tz_localize(None)
        calendarDf = pd.DataFrame(index=tradingDates)
        calendarDf.index.name = 'date'
        calendarDf['dayOfWeek'] = calendarDf.index.dayofweek
        calendarDf['dayOfMonth'] = calendarDf.index.day
        calendarDf['month'] = calendarDf.index.month
        calendarDf['quarter'] = calendarDf.index.quarter
        calendarDf['dayOfYear'] = calendarDf.index.dayofyear
        calendarDf['isHoliday'] = 0
        months = calendarDf['month']
        days = calendarDf['dayOfMonth']
        isQ1Earnings = months.isin([1, 2]) | (months == 3) & (days <= 15)
        isQ2Earnings = months.isin([4, 5]) | (months == 6) & (days <= 15)
        isQ3Earnings = months.isin([7, 8]) | (months == 9) & (days <= 15)
        isQ4Earnings = months.isin([10, 11]) | (months == 12) & (days <= 15)
        calendarDf['isEarningsWindow'] = (isQ1Earnings | isQ2Earnings | isQ3Earnings | isQ4Earnings).astype(int)
        return calendarDf
