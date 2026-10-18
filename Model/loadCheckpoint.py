import sys
from pathlib import Path
import pandas as pd
import torch
from pytorch_forecasting import TemporalFusionTransformer
from pytorch_forecasting.data import EncoderNormalizer

sys.path.append(str(Path(__file__).resolve().parent.parent))
from remoteLoader import ensure_algorise_weights

class CleanEncoderNormalizer(EncoderNormalizer):

    def fit(self, values, *args, **kwargs):
        if isinstance(values, (pd.DataFrame, pd.Series)):
            values = values.values
        elif hasattr(values, 'detach'):
            values = values.detach().cpu().numpy()
        return super().fit(values, *args, **kwargs)
setattr(sys.modules['__main__'], 'CleanEncoderNormalizer', CleanEncoderNormalizer)
current_dir = Path(__file__).resolve().parent
output_path = current_dir / 'algorise_tft_weights.pth'

# Ensure weights file is available (downloads from GitHub release specified in .env if not present locally)
ensure_algorise_weights(output_path)

if output_path.exists():
    print(f'Loading weights from: {output_path}')
    state_dict = torch.load(output_path, map_location='cpu')
    print('Weights loaded successfully from release / local cache!')
else:
    checkpoint_path = current_dir.parent / 'lightning_logs' / 'algorise_tft_multi_horizon' / 'version_0' / 'checkpoints' / 'model.ckpt'
    if checkpoint_path.exists():
        print(f'Loading model from checkpoint: {checkpoint_path}')
        model = TemporalFusionTransformer.load_from_checkpoint(checkpoint_path)
        print('Model loaded successfully!')
        torch.save(model.state_dict(), output_path)
        print(f'Clean state dict saved to: {output_path}')
    else:
        print(f'Neither weights file nor local checkpoint found. Please set ALGORISE_WEIGHTS_URL in .env or train the model.')
