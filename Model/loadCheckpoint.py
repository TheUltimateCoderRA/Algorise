import sys
from pathlib import Path
import pandas as pd
import torch
from pytorch_forecasting import TemporalFusionTransformer
from pytorch_forecasting.data import EncoderNormalizer

class CleanEncoderNormalizer(EncoderNormalizer):

    def fit(self, values, *args, **kwargs):
        if isinstance(values, (pd.DataFrame, pd.Series)):
            values = values.values
        elif hasattr(values, 'detach'):
            values = values.detach().cpu().numpy()
        return super().fit(values, *args, **kwargs)
setattr(sys.modules['__main__'], 'CleanEncoderNormalizer', CleanEncoderNormalizer)
current_dir = Path(__file__).resolve().parent
checkpoint_path = current_dir.parent / 'lightning_logs' / 'algorise_tft_multi_horizon' / 'version_0' / 'checkpoints' / 'model.ckpt'
print(f'Loading model from: {checkpoint_path}')
model = TemporalFusionTransformer.load_from_checkpoint(checkpoint_path)
print('Model loaded successfully!')
output_path = current_dir / 'algorise_tft_weights.pth'
torch.save(model.state_dict(), output_path)
print(f'Clean state dict saved to: {output_path}')
