# Project Descrption

Autonomous AI Agent that can find, evaulate and trade stocks on its own (Algorise)

## Arcitecture

* Train a TFT Model on about 12 years worth of data on Ticker, GICS Sector, GICS Industry, Listing Age, Day of Week, Day of Month, Month, Quarter, Day of Year, Market Holiday Flag, FOMC Meeting Flag, Earnings Window Flag, Open Price, High Price, Low Price, Close Price, Adjusted Close Price, Volume, Volume Z-Score, Garman-Klass Volatility, Federal Funds Rate, 10-Year Treasury Yield, Consumer Price Index, Unemployment Rate, 10Y-2Y Treasury Spread, Money Supply M2, Consumer Sentiment Index, Industrial Production Index, High-Yield Credit Spread, Market Principal Component 1, Market Principal Component 2, Market Principal Component 3, Calculated EPS, EPS Year-over-Year Growth, Income Statement Data, Balance Sheet Data, Cash Flow Data, Earnings Report Event Date, Price Shock Flag
* Create and use an LLM research agent to look at news and other publicly available information to create a json report
* Use the model to predict expected prices across multiple time frames, and the results of the LLM agent and pass it to another LLM api along with the current portfolio data to make an informed desicion of if to buy and how much to buy.

## Filesystem

Algorise/
├── Data/
│   ├── Model/
│   │   ├── metadata.py      
│   │   ├── calendar.py   
│   │   ├── marketPrices.py      
│   │   ├── macro.py
│   │   └── fundamentals.py
│   └── Realtime/
│       ├── Research/
│       │   ├── agent.py
│       │   ├── parse.py
│       │   └── ...
│       └── Current Data/
│           ├── metadata.py      
│           ├── calendar.py   
│           ├── marketPrices.py      
│           ├── macro.py
│           ├── fundamentals.py
│           └── model.py
├── Database/
│   ├── createDB.py
│   ├── runAll.py
│   ├── checkDB.py
│   └── pushToCloud.py
├── Desicion/
│   └── desicion.py
├── Portfolio/
│   ├── getCurrentPortfolio.py
│   ├── buyStock.py
│   └── sellStock.py
├── .env
├── requirements.txt
├── README.md
└── tickers.json


## Coding Practices

* Use camelCase and for folders and such use capital letter for the first letter such as Algorise or Model
* Make everything modular and use OOPS programming
* Only use Python unless specifically said not to
* All data needs to be free, no paid subscriptions (Use yfinance, twelvedata (if needed), simfin, fred)