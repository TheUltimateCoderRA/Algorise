import os
import sys
import shutil
import zipfile
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from remoteLoader import ensure_algorise_db

DB_PATH = os.path.join(os.path.dirname(__file__), 'algorise.db')
BACKUP_DIR = os.path.join(os.path.dirname(__file__), 'backups')

def push_to_cloud(db_path: str=DB_PATH) -> None:
    db_path = ensure_algorise_db(db_path)
    if not os.path.exists(db_path):
        print(f'Database not found at {db_path}. Nothing to push/backup.')
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_zip_path = os.path.join(BACKUP_DIR, f'algorise_db_backup_{timestamp}.zip')
    with zipfile.ZipFile(backup_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(db_path, arcname=os.path.basename(db_path))
    print(f'Database successfully compressed and archived at: {backup_zip_path}')
    print('Ready for cloud sync / push (integration point for S3, HuggingFace, or remote storage).')
if __name__ == '__main__':
    push_to_cloud()
