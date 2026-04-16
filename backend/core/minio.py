import boto3
from botocore.client import Config
from core.config import settings

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1' # Boto3 bắt buộc phải có region, dù MinIO không dùng tới
    )

s3_client = get_s3_client()

def ensure_bucket_exists():
    """Kiểm tra và tự động tạo Bucket nếu chưa có"""
    try:
        s3_client.head_bucket(Bucket=settings.bucket_name)
    except Exception:
        s3_client.create_bucket(Bucket=settings.bucket_name)
        print(f"🪣 Đã tạo mới bucket: {settings.bucket_name}")