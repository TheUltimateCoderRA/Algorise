import os
import sqlite3
import pandas as pd
import numpy as np
import json

class DatabaseManager:

    def __init__(self, dbPath: str='Database/algorise.db') -> None:
        self.dbPath = dbPath

    def getconnection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.dbPath)

class FeatureBuilder:

    def __init__(self, dbPath: str='Database/algorise.db') -> None:
        self.dbManager = DatabaseManager(dbPath=dbPath)

    def loadMarketPrices(self) -> pd.DataFrame:
        conn = self.dbManager.getconnection()
        dfPrices = pd.read_sql('SELECT * FROM market_prices', conn)
        conn.close()
        if not dfPrices.empty:
            dfPrices['date'] = pd.to_datetime(dfPrices['date'])
            dfPrices = dfPrices.drop_duplicates(subset=['date', 'ticker'], keep='last')
            dfPrices = dfPrices.sort_values(['ticker', 'date'])
        return dfPrices

    def computeGarmanKlassVolatility(self, dfPrices: pd.DataFrame) -> pd.DataFrame:
        highLowRatio = dfPrices['high_price'] / dfPrices['low_price'].replace(0, np.nan)
        closeOpenRatio = dfPrices['close_price'] / dfPrices['open_price'].replace(0, np.nan)
        gkVar = 0.5 * np.log(highLowRatio.clip(lower=1e-08)) ** 2 - (2 * np.log(2) - 1) * np.log(closeOpenRatio.clip(lower=1e-08)) ** 2
        dfPrices['garman_klass_volatility'] = np.sqrt(gkVar.clip(lower=0)).fillna(0)
        return dfPrices

    def computeVolumeZScore(self, dfPrices: pd.DataFrame) -> pd.DataFrame:

        def calc30dZScore(group):
            vol = group['volume']
            mean30 = vol.rolling(window=30, min_periods=1).mean()
            std30 = vol.rolling(window=30, min_periods=1).std().replace(0, 1.0)
            z = (vol - mean30) / std30
            return z.fillna(0)
        dfPrices['volume_z_score'] = dfPrices.groupby('ticker', group_keys=False).apply(calc30dZScore)
        return dfPrices

    def computePcaEmbeddings(self, dfPrices: pd.DataFrame) -> pd.DataFrame:
        dfPivot = dfPrices.pivot(index='date', columns='ticker', values='adjusted_close_price')
        dfReturns = dfPivot.pct_change().dropna(how='all').fillna(0)
        if dfReturns.empty or dfReturns.shape[1] < 3:
            return pd.DataFrame()
        X = dfReturns.values
        XMean = np.mean(X, axis=0)
        XCentered = X - XMean
        _, _, Vt = np.linalg.svd(XCentered, full_matrices=False)
        components = Vt[:3, :]
        pcaScores = XCentered @ components.T
        dfPca = pd.DataFrame(pcaScores, index=dfReturns.index, columns=['market_pc1', 'market_pc2', 'market_pc3']).reset_index()
        dfPca['date'] = dfPca['date'].dt.strftime('%Y-%m-%d')
        return dfPca

    def computeFundamentalsFeatures(self) -> pd.DataFrame:
        conn = self.dbManager.getconnection()
        dfIncome = pd.read_sql('SELECT * FROM fundamentals_income', conn)
        conn.close()
        if dfIncome.empty:
            return pd.DataFrame()
        parsedRecords = []
        for _, row in dfIncome.iterrows():
            ticker = row['ticker']
            reportDate = row['report_date']
            try:
                data = json.loads(row['data_json'])
                netIncome = data.get('Net Income') or data.get('Net Income (Common)') or 0.0
                sharesBasic = data.get('Shares (Basic)') or 0.0
                sharesDiluted = data.get('Shares (Diluted)') or sharesBasic
                eps = data.get('Basic EPS') or data.get('Diluted EPS')
                if eps is None or pd.isna(eps):
                    if sharesDiluted and sharesDiluted > 0:
                        eps = netIncome / sharesDiluted
                    elif sharesBasic and sharesBasic > 0:
                        eps = netIncome / sharesBasic
                    else:
                        eps = 0.0
                parsedRecords.append({'ticker': ticker, 'report_date': reportDate, 'net_income': float(netIncome or 0.0), 'shares_diluted': float(sharesDiluted or 0.0), 'eps': float(eps or 0.0)})
            except Exception:
                continue
        dfFund = pd.DataFrame(parsedRecords)
        if dfFund.empty:
            return dfFund
        dfFund['report_date'] = pd.to_datetime(dfFund['report_date'])
        dfFund = dfFund.drop_duplicates(subset=['ticker', 'report_date'], keep='last')
        dfFund = dfFund.sort_values(['ticker', 'report_date'])
        dfFund['yoy_eps_growth'] = dfFund.groupby('ticker')['eps'].pct_change(periods=4).fillna(0.0)
        dfFund['price_shock_flag'] = (dfFund['yoy_eps_growth'].abs() > 0.25).astype(int)
        dfFund['report_date'] = dfFund['report_date'].dt.strftime('%Y-%m-%d')
        return dfFund

    def runPipeline(self) -> None:
        print('=== Starting Feature Engineering & Feature Store Builder Pipeline ===')
        dfPrices = self.loadMarketPrices()
        if dfPrices.empty:
            print('Error: Market prices table is empty.')
            return
        dfPrices = self.computeGarmanKlassVolatility(dfPrices)
        dfPrices = self.computeVolumeZScore(dfPrices)
        conn = self.dbManager.getconnection()
        print('Updating market_prices table in database...')
        dfPrices.to_sql('market_prices', conn, if_exists='replace', index=False)
        dfGk = dfPrices[['ticker', 'date', 'garman_klass_volatility']].copy()
        dfGk['date'] = dfGk['date'].dt.strftime('%Y-%m-%d')
        dfGk.to_sql('garman_klass_vol', conn, if_exists='replace', index=False)
        print('Garman-Klass volatility and 30-day Volume Z-Score successfully stored.')
        print('Computing Cross-Market PCA Embeddings (PC1, PC2, PC3)...')
        dfPca = self.computePcaEmbeddings(dfPrices)
        if not dfPca.empty:
            dfPca.to_sql('market_pca', conn, if_exists='replace', index=False)
            print('Market PCA embeddings stored successfully in market_pca table.')
        print('Computing Calculated EPS, YoY Growth, and Price Shock Flag...')
        dfFund = self.computeFundamentalsFeatures()
        if not dfFund.empty:
            dfFund.to_sql('fundamentals_features', conn, if_exists='replace', index=False)
            print('Fundamentals features stored in fundamentals_features table.')
        print('\n=== Feature Store Inspection Summary ===')
        cursor = conn.cursor()
        tablesToCheck = ['market_prices', 'garman_klass_vol', 'market_pca', 'fundamentals_features']
        for t in tablesToCheck:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {t}')
                cnt = cursor.fetchone()[0]
                print(f"Table '{t}': {cnt} rows")
                dfSample = pd.read_sql(f'SELECT * FROM {t} LIMIT 3', conn)
                print(f'  Sample columns: {list(dfSample.columns)}')
            except Exception as e:
                print(f"Table '{t}' check failed: {e}")
        conn.close()
        print('\nFeature Engineering Pipeline successfully completed and validated!')
if __name__ == '__main__':
    builder = FeatureBuilder()
    builder.runPipeline()
