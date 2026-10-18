import os
import re
import logging
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def get_release_url() -> str | None:
    # 1. Check environment variables
    for key, val in os.environ.items():
        if val and isinstance(val, str) and ('github.com' in val and 'release' in val):
            return val.strip()
            
    # 2. Directly inspect .env file in case it contains a raw URL line without a key
    env_path = Path(__file__).resolve().parent / '.env'
    if env_path.exists():
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    # If line has '=', take the value part
                    if '=' in line:
                        _, val = line.split('=', 1)
                        val = val.strip().strip('"\'')
                        if 'github.com' in val and 'release' in val:
                            return val
                    elif 'github.com' in line and 'release' in line:
                        return line.strip().strip('"\'')
        except Exception as e:
            logger.debug(f"Error reading .env directly: {e}")

    return None

def get_asset_url(filename: str) -> str | None:
    release_url = get_release_url()
    if not release_url:
        return None

    # Match github release url pattern: https://github.com/owner/repo/releases/tag/tag_name or similar
    match = re.search(r'github\.com/([^/]+)/([^/]+)/releases/(?:tag/)?([^/]+)', release_url)
    if match:
        owner, repo, tag = match.groups()
        return f"https://github.com/{owner}/{repo}/releases/download/{tag}/{filename}"
    
    base_url = release_url.rstrip('/')
    return f"{base_url}/download/{filename}"

def download_file_from_url(url: str, dest_path: str | Path) -> Path:
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Downloading from {url} to {dest_path}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    logger.info(f"Successfully downloaded file to {dest_path}")
    return dest_path

def ensure_algorise_db(db_path: str | Path = 'Database/algorise.db') -> Path:
    db_path = Path(db_path)
    if db_path.exists():
        return db_path
    
    url = get_asset_url('algorise.db')
    if url:
        try:
            return download_file_from_url(url, db_path)
        except Exception as e:
            logger.error(f"Failed to download algorise.db from {url}: {e}")
            return db_path
    else:
        logger.warning(f"Database file not found at {db_path} and no GitHub release URL found in .env.")
        return db_path

def ensure_algorise_weights(weights_path: str | Path = 'Model/algorise_tft_weights.pth') -> Path:
    weights_path = Path(weights_path)
    if weights_path.exists():
        return weights_path
    
    # Try downloading algorise_tft_weights.pth (and handle alforise_tft_weights.pth alias if needed)
    filename = weights_path.name
    url = get_asset_url(filename)
    if not url and filename == 'algorise_tft_weights.pth':
        url = get_asset_url('alforise_tft_weights.pth')

    if url:
        try:
            return download_file_from_url(url, weights_path)
        except Exception as e:
            logger.error(f"Failed to download weights from {url}: {e}")
            return weights_path
    else:
        logger.warning(f"Weights file not found at {weights_path} and no GitHub release URL found in .env.")
        return weights_path
