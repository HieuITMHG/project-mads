import boto3
from botocore.client import Config
from sandbox_api.core.config import settings

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1' 
    )

s3_client = get_s3_client()

def ensure_bucket_exists(bucket_name: str):
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except Exception:
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"Đã tạo mới bucket: {bucket_name}")