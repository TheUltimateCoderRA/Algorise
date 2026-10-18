import warnings
warnings.filterwarnings(action='ignore', message='X does not have valid feature names, but StandardScaler was fitted with feature names', category=UserWarning)
import os
import sqlite3
import logging
import pandas as pd
import numpy as np
import torch
import pytorch_forecasting
from pytorch_forecasting import TimeSeriesDataSet, TemporalFusionTransformer
from pytorch_forecasting.metrics import QuantileLoss
import lightning.pytorch as pl
from lightning.pytorch.callbacks import EarlyStopping, LearningRateMonitor
from lightning.pytorch.loggers import TensorBoardLogger
from pytorch_forecasting.data.encoders import EncoderNormalizer

class CleanEncoderNormalizer(EncoderNormalizer):

    def fit(self, values, *args, **kwargs):
        if isinstance(values, (pd.DataFrame, pd.Series)):
            values = values.values
        elif hasattr(values, 'detach'):
            values = values.detach().cpu().numpy()
        return super().fit(values, *args, **kwargs)
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from remoteLoader import ensure_algorise_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

class AlgoriseDataLoader:

    def __init__(self, db_path: str='Database/algorise.db') -> None:
        self.db_path = ensure_algorise_db(db_path)

    def _get_connection(self) -> sqlite3.Connection:
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f'Database file not found at {self.db_path}')
        return sqlite3.connect(self.db_path)

    def load_unified_dataset(self) -> pd.DataFrame:
        logger.info(f'Connecting to database at {self.db_path}...')
        conn = self._get_connection()
        try:
            logger.info('Loading market_prices table...')
            df_prices = pd.read_sql('SELECT * FROM market_prices', conn)
            logger.info('Loading market_pca table...')
            try:
                df_pca = pd.read_sql('SELECT * FROM market_pca', conn)
            except Exception:
                df_pca = pd.DataFrame(columns=['date', 'market_pc1', 'market_pc2', 'market_pc3'])
            logger.info('Loading macro table...')
            try:
                df_macro = pd.read_sql('SELECT * FROM macro', conn)
            except Exception:
                df_macro = pd.DataFrame(columns=['date'])
            logger.info('Loading metadata table...')
            try:
                df_meta = pd.read_sql('SELECT * FROM metadata', conn)
            except Exception:
                df_meta = pd.DataFrame(columns=['ticker', 'gics_sector', 'gics_industry'])
        finally:
            conn.close()
        if df_prices.empty:
            raise ValueError('market_prices table is empty. Please run feature engineering pipeline first.')
        df_prices['date'] = pd.to_datetime(df_prices['date'])
        df_prices = df_prices.sort_values(['ticker', 'date']).reset_index(drop=True)
        df_prices['close'] = df_prices['close_price']
        df_prices['returns'] = df_prices.groupby('ticker')['close'].pct_change().fillna(0.0)
        if 'garman_klass_volatility' in df_prices.columns:
            df_prices['garman_klass_vol'] = df_prices['garman_klass_volatility']
        else:
            df_prices['garman_klass_vol'] = 0.0
        if 'volume_z_score' in df_prices.columns:
            df_prices['volume_zscore'] = df_prices['volume_z_score']
        else:
            df_prices['volume_zscore'] = 0.0
        horizons = {'7d': 7, '15d': 15, '30d': 30, '3m': 63, '6m': 126, '1y': 252}
        for name, h in horizons.items():
            df_prices[f'return_{name}'] = df_prices.groupby('ticker')['close'].shift(-h) / df_prices['close'] - 1.0
            df_prices[f'vol_{name}'] = df_prices.groupby('ticker')['returns'].rolling(window=h, min_periods=1).std().reset_index(level=0, drop=True) * np.sqrt(252)
        target_cols = [f'return_{k}' for k in horizons] + [f'vol_{k}' for k in horizons]
        for col in target_cols:
            df_prices[col] = df_prices[col].fillna(0.0)
        if not df_pca.empty:
            df_pca['date'] = pd.to_datetime(df_pca['date'])
            df_prices = pd.merge(df_prices, df_pca, on='date', how='left')
        else:
            for col in ['market_pc1', 'market_pc2', 'market_pc3']:
                df_prices[col] = 0.0
        if not df_macro.empty:
            df_macro['date'] = pd.to_datetime(df_macro['date'])
            df_prices = pd.merge(df_prices, df_macro, on='date', how='left')
        if not df_meta.empty:
            df_prices['sector'] = df_meta.set_index('ticker').reindex(df_prices['ticker'])['gics_sector'].values if 'gics_sector' in df_meta.columns else 'Unknown'
            df_prices['industry'] = df_meta.set_index('ticker').reindex(df_prices['ticker'])['gics_industry'].values if 'gics_industry' in df_meta.columns else 'Unknown'
        else:
            df_prices['sector'] = 'Unknown'
            df_prices['industry'] = 'Unknown'
        df_prices['sector'] = df_prices['sector'].astype(str).fillna('Unknown')
        df_prices['industry'] = df_prices['industry'].astype(str).fillna('Unknown')
        macro_cols = [c for c in df_macro.columns if c != 'date']
        fill_cols = ['market_pc1', 'market_pc2', 'market_pc3', 'volume_zscore', 'garman_klass_vol'] + macro_cols
        for col in fill_cols:
            if col in df_prices.columns:
                df_prices[col] = df_prices[col].ffill().bfill().fillna(0.0)
        unique_dates = sorted(df_prices['date'].unique())
        date_to_idx = {date: idx for idx, date in enumerate(unique_dates)}
        df_prices['time_idx'] = df_prices['date'].map(date_to_idx)
        logger.info(f"Multi-horizon unified dataset loaded successfully. Shape: {df_prices.shape}, Tickers: {df_prices['ticker'].nunique()}")
        return df_prices

class TFTMultiHorizonPipeline:

    def __init__(self, max_encoder_length: int=60, max_prediction_length: int=252, batch_size: int=64, learning_rate: float=0.001, max_epochs: int=5, target_col: str='returns') -> None:
        self.max_encoder_length = max_encoder_length
        self.max_prediction_length = max_prediction_length
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.max_epochs = max_epochs
        self.target_col = target_col

    def build_datasets(self, df: pd.DataFrame) -> tuple[TimeSeriesDataSet, TimeSeriesDataSet]:
        logger.info(f"Configuring TimeSeriesDataSet with target '{self.target_col}' (horizon: {self.max_prediction_length} steps)...")
        max_time_idx = df['time_idx'].max()
        validation_cutoff = max_time_idx - self.max_prediction_length * 2
        training_data = df[df['time_idx'] <= validation_cutoff]
        validation_data = df[df['time_idx'] > validation_cutoff - self.max_encoder_length]
        macro_cols = [c for c in ['federal_funds_rate', 'treasury_yield_10y', 'cpi', 'unemployment_rate', 'treasury_spread_10y2y', 'money_supply_m2', 'consumer_sentiment', 'industrial_production', 'high_yield_credit_spread'] if c in df.columns]
        time_varying_known_reals = ['time_idx', 'market_pc1', 'market_pc2', 'market_pc3'] + macro_cols
        time_varying_unknown_reals = ['close', 'returns', 'volume', 'garman_klass_vol', 'volume_zscore'] + [f'return_{k}' for k in ['7d', '15d', '30d', '3m', '6m', '1y']] + [f'vol_{k}' for k in ['7d', '15d', '30d', '3m', '6m', '1y']]
        static_categoricals = ['sector', 'industry']
        training_dataset = TimeSeriesDataSet(training_data, time_idx='time_idx', target=self.target_col, group_ids=['ticker'], min_encoder_length=self.max_encoder_length // 2, max_encoder_length=self.max_encoder_length, min_prediction_length=1, max_prediction_length=self.max_prediction_length, static_categoricals=static_categoricals, time_varying_known_reals=time_varying_known_reals, time_varying_unknown_reals=time_varying_unknown_reals, target_normalizer=CleanEncoderNormalizer(method='standard'), add_relative_time_idx=True, add_target_scales=True, add_encoder_length=True, allow_missing_timesteps=True)
        validation_dataset = TimeSeriesDataSet.from_dataset(training_dataset, validation_data, predict=True, stop_randomization=True)
        return (training_dataset, validation_dataset)

    def create_dataloaders(self, training_dataset: TimeSeriesDataSet, validation_dataset: TimeSeriesDataSet) -> tuple[torch.utils.data.DataLoader, torch.utils.data.DataLoader]:
        train_dataloader = training_dataset.to_dataloader(batch_size=self.batch_size, shuffle=True, num_workers=0)
        val_dataloader = validation_dataset.to_dataloader(batch_size=self.batch_size * 2, shuffle=False, num_workers=0)
        return (train_dataloader, val_dataloader)

    def train_model(self, train_dataloader: torch.utils.data.DataLoader, val_dataloader: torch.utils.data.DataLoader, training_dataset: TimeSeriesDataSet) -> TemporalFusionTransformer:
        logger.info('Initializing TemporalFusionTransformer for multi-horizon returns & volatility...')
        tft = TemporalFusionTransformer.from_dataset(training_dataset, learning_rate=self.learning_rate, hidden_size=32, attention_head_size=4, dropout=0.2, hidden_continuous_size=16, output_size=7, loss=QuantileLoss(), reduce_on_plateau_patience=4)
        early_stop_callback = EarlyStopping(monitor='val_loss', min_delta=0.0001, patience=5, mode='min')
        lr_logger = LearningRateMonitor()
        logger_tb = TensorBoardLogger('lightning_logs', name='algorise_tft_multi_horizon')
        trainer = pl.Trainer(max_epochs=self.max_epochs, accelerator='cpu', enable_model_summary=True, gradient_clip_val=0.1, callbacks=[early_stop_callback, lr_logger], logger=logger_tb)
        logger.info('Starting training for multi-horizon return & volatility forecasts...')
        trainer.fit(tft, train_dataloaders=train_dataloader, val_dataloaders=val_dataloader)
        logger.info('Multi-horizon model training completed successfully.')
        return tft
if __name__ == '__main__':
    loader = AlgoriseDataLoader()
    df_unified = loader.load_unified_dataset()
    pipeline = TFTMultiHorizonPipeline(max_encoder_length=60, max_prediction_length=252, batch_size=64, learning_rate=0.001, max_epochs=3, target_col='returns')
    train_ds, val_ds = pipeline.build_datasets(df_unified)
    train_dl, val_dl = pipeline.create_dataloaders(train_ds, val_ds)
    model = pipeline.train_model(train_dl, val_dl, train_ds)
