import os
import zipfile
import pandas as pd
from pathlib import Path
from sqlalchemy import text, create_engine # Bổ sung create_engine
from kaggle.api.kaggle_api_extended import KaggleApi

# Bỏ import engine cũ đi
# from core.postgres import engine 
from core.minio import s3_client, ensure_bucket_exists
from core.config import settings
from api.models.base import Base

DATASET_NAME = "olistbr/brazilian-ecommerce"
TEMP_DIR = Path("/tmp/olist_data")

FILE_TABLE_MAP = [
    ("olist_customers_dataset.csv", "olist_customers"),
    ("olist_sellers_dataset.csv", "olist_sellers"),
    ("olist_geolocation_dataset.csv", "olist_geolocation"),
    ("olist_products_dataset.csv", "olist_products"),
    ("olist_orders_dataset.csv", "olist_orders"),
    ("olist_order_items_dataset.csv", "olist_order_items"),
    ("olist_order_payments_dataset.csv", "olist_order_payments")
]

# TẠO MỘT SYNC ENGINE RIÊNG CHO PANDAS
# Lưu ý: Không có '+asyncpg' ở đây
SYNC_DATABASE_URL = f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
sync_engine = create_engine(SYNC_DATABASE_URL, echo=False)

def check_data_exists() -> bool:
    try:
        # Thay engine -> sync_engine
        with sync_engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM olist_orders"))
            return result.scalar() > 0
    except Exception:
        return False

def download_from_kaggle():
    print("Đang kết nối Kaggle và tải Dataset ...")
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    api = KaggleApi()
    api.authenticate()
    
    api.dataset_download_files(DATASET_NAME, path=str(TEMP_DIR), unzip=True)
    print("Tải và giải nén thành công!")

def upload_raw_to_minio():
    print("☁️ Đang đẩy file CSV gốc lên Data Lake (MinIO)...")
    ensure_bucket_exists(settings.olist_data)
    
    for file_name, _ in FILE_TABLE_MAP:
        file_path = TEMP_DIR / file_name
        if file_path.exists():
            s3_client.upload_file(
                Filename=str(file_path),
                Bucket=settings.olist_data,
                Key=f"raw/olist/{file_name}"
            )
            print(f"  -> Đã upload {file_name}")

def ingest_to_postgres():
    print("🚀 Bắt đầu tạo cấu trúc bảng (Schema)...")
    # Thay engine -> sync_engine
    Base.metadata.create_all(bind=sync_engine)

    print("🚀 Bắt đầu đọc CSV và đẩy vào PostgreSQL...")
    for file_name, table_name in FILE_TABLE_MAP:
        file_path = TEMP_DIR / file_name
        
        if not file_path.exists():
            continue

        print(f"⏳ Đang import {file_name} vào bảng {table_name}...")
        chunk_iter = pd.read_csv(file_path, chunksize=10000)
        
        for chunk in chunk_iter:
            # Thay engine -> sync_engine
            chunk.to_sql(name=table_name, con=sync_engine, if_exists="append", index=False)
            
        print(f"✅ Import thành công bảng {table_name}!")

def main_pipeline():
    print("🔍 Kiểm tra trạng thái hệ thống...")
    if check_data_exists():
        print("⏭️ Dữ liệu đã tồn tại trong PostgreSQL. Bỏ qua Pipeline!")
        return

    print("⏬ Bắt đầu luồng Data Engineering...")
    download_from_kaggle()
    upload_raw_to_minio()
    ingest_to_postgres()
    print("🎉 TOÀN BỘ PIPELINE ĐÃ HOÀN TẤT!")

if __name__ == "__main__":
    main_pipeline()