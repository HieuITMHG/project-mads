from core.minio import s3_client
from core.config import settings

def upload_to_minio():
    s3_client.u