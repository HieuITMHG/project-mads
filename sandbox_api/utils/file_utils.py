from concurrent.futures import ThreadPoolExecutor
import os
from sandbox_api.core.minio import s3_client
from sandbox_api.core.config import settings

def download_one_file(s3_path: str, save_dir: str):
    file_name = s3_path.split("/")[-1]
    local_path = os.path.join(save_dir, file_name)
    
    try:
        s3_client.download_file(settings.upload_bucket, s3_path, local_path)
        return f"Đã download file {s3_path} vào {local_path}"
    except Exception as e:
        return f"Lỗi khi download file {s3_path}: {e}"
    
def download_all_files(s3_path_lst: list[str], save_dir: str):
    os.makedirs(save_dir, exist_ok=True)
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [
            executor.submit(download_one_file, s3_path, save_dir)
            for s3_path in s3_path_lst
        ]